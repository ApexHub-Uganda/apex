"""School geofence + staff GPS attendance + class attendance enforcement."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.attendance.geofence import evaluate_location, point_in_polygon, save_geofence
from apps.attendance.models import AttendanceRecord, SchoolGeofence
from apps.attendance.staff_geo_attendance import staff_check_in
from apps.core.constants import UserRole
from apps.staff.services import onboard_staff
from apps.subscriptions.models import Plan, Subscription
from apps.subscriptions.seed_features import seed_feature_catalog
from apps.subscriptions.services import assign_plan_features
from apps.tenants.models import Tenant


# Simple square around (0.35, 32.58) — Kampala-ish
SQUARE = [
    {"lat": 0.3480, "lng": 32.5800},
    {"lat": 0.3480, "lng": 32.5850},
    {"lat": 0.3450, "lng": 32.5850},
    {"lat": 0.3450, "lng": 32.5800},
]
INSIDE = (0.3465, 32.5825)
OUTSIDE = (0.3600, 32.6000)


@pytest.fixture
def geo_tenant(db):
    seed_feature_catalog()
    plan = Plan.objects.create(name="Geo Plan", slug="geo-plan", max_students=500)
    assign_plan_features(plan, [
        "student_attendance", "staff_attendance", "staff_management",
        "classes", "dashboard_analytics",
    ])
    tenant = Tenant.objects.create(
        name="Geo School",
        code="GEO1",
        email="geo@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def school_admin(db, geo_tenant):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        email="admin.geo@test.edu",
        password="TestPass@2026",
        first_name="Geo",
        last_name="Admin",
        role=UserRole.SCHOOL_ADMIN,
        tenant=geo_tenant,
        is_email_verified=True,
    )


@pytest.fixture
def staff_user(db, geo_tenant):
    staff = onboard_staff(
        geo_tenant,
        data={
            "first_name": "Geo",
            "last_name": "Teacher",
            "email": "geo.teacher@test.edu",
            "phone": "+256700000111",
            "portal_role": UserRole.TEACHER,
            "date_joined": "2025-01-01",
        },
    )
    return staff.user


@pytest.mark.django_db
class TestGeofenceMath:
    def test_point_in_polygon_inside(self):
        assert point_in_polygon(INSIDE[0], INSIDE[1], SQUARE) is True

    def test_point_in_polygon_outside(self):
        assert point_in_polygon(OUTSIDE[0], OUTSIDE[1], SQUARE) is False

    def test_evaluate_not_enforced_without_fence(self, geo_tenant):
        result = evaluate_location(tenant=geo_tenant, lat=OUTSIDE[0], lng=OUTSIDE[1])
        assert result["allowed"] is True
        assert result["enforced"] is False

    def test_evaluate_outside_when_enabled(self, geo_tenant, school_admin):
        save_geofence(
            tenant=geo_tenant,
            user=school_admin,
            vertices=SQUARE,
            buffer_meters=5,
            is_enabled=True,
        )
        result = evaluate_location(tenant=geo_tenant, lat=OUTSIDE[0], lng=OUTSIDE[1])
        assert result["allowed"] is False
        assert result["code"] == "outside"

    def test_evaluate_inside_when_enabled(self, geo_tenant, school_admin):
        save_geofence(
            tenant=geo_tenant,
            user=school_admin,
            vertices=SQUARE,
            buffer_meters=5,
            is_enabled=True,
        )
        result = evaluate_location(tenant=geo_tenant, lat=INSIDE[0], lng=INSIDE[1])
        assert result["allowed"] is True
        assert result["code"] == "inside"

    def test_poor_accuracy_rejected(self, geo_tenant, school_admin):
        save_geofence(
            tenant=geo_tenant,
            user=school_admin,
            vertices=SQUARE,
            buffer_meters=5,
            is_enabled=True,
        )
        result = evaluate_location(
            tenant=geo_tenant,
            lat=INSIDE[0],
            lng=INSIDE[1],
            accuracy_m=2000,
        )
        assert result["allowed"] is False
        assert result["code"] == "poor_accuracy"

    def test_moderate_accuracy_accepted_inside(self, geo_tenant, school_admin):
        save_geofence(
            tenant=geo_tenant,
            user=school_admin,
            vertices=SQUARE,
            buffer_meters=25,
            is_enabled=True,
        )
        result = evaluate_location(
            tenant=geo_tenant,
            lat=INSIDE[0],
            lng=INSIDE[1],
            accuracy_m=120,
        )
        assert result["allowed"] is True


@pytest.mark.django_db
class TestStaffGeoApi:
    def test_admin_can_save_geofence(self, geo_tenant, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        response = client.put("/api/v1/attendance/geofence/", {
            "vertices": SQUARE,
            "buffer_meters": 20,
            "is_enabled": True,
            "name": "Main campus",
        }, format="json")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["configured"] is True
        assert data["is_enabled"] is True
        assert data["vertex_count"] == 4
        assert SchoolGeofence.objects.filter(tenant=geo_tenant).exists()

    def test_save_rejects_fewer_than_four_points(self, geo_tenant, school_admin):
        client = APIClient()
        client.force_authenticate(user=school_admin)
        response = client.put("/api/v1/attendance/geofence/", {
            "vertices": SQUARE[:3],
            "is_enabled": True,
        }, format="json")
        assert response.status_code == 400

    def test_staff_check_in_inside(self, geo_tenant, school_admin, staff_user):
        save_geofence(
            tenant=geo_tenant,
            user=school_admin,
            vertices=SQUARE,
            buffer_meters=10,
            is_enabled=True,
        )
        client = APIClient()
        client.force_authenticate(user=staff_user)
        response = client.post("/api/v1/attendance/staff/check-in/", {
            "lat": INSIDE[0],
            "lng": INSIDE[1],
            "accuracy_m": 12,
        }, format="json")
        assert response.status_code == 200
        assert response.json()["data"]["checked_in"] is True
        assert AttendanceRecord.objects.filter(
            tenant=geo_tenant, attendee_type="staff", staff__user=staff_user,
        ).exists()

    def test_staff_check_in_outside_denied(self, geo_tenant, school_admin, staff_user):
        save_geofence(
            tenant=geo_tenant,
            user=school_admin,
            vertices=SQUARE,
            buffer_meters=5,
            is_enabled=True,
        )
        client = APIClient()
        client.force_authenticate(user=staff_user)
        response = client.post("/api/v1/attendance/staff/check-in/", {
            "lat": OUTSIDE[0],
            "lng": OUTSIDE[1],
            "accuracy_m": 10,
        }, format="json")
        assert response.status_code == 400
        assert response.json().get("code") == "outside"

    def test_staff_check_in_requires_location_when_enforced(self, geo_tenant, school_admin, staff_user):
        save_geofence(
            tenant=geo_tenant,
            user=school_admin,
            vertices=SQUARE,
            is_enabled=True,
        )
        with pytest.raises(Exception):
            staff_check_in(tenant=geo_tenant, user=staff_user, lat=None, lng=None)


@pytest.mark.django_db
class TestClassAttendanceGeofence:
    def test_class_bulk_denied_outside(self, geo_tenant, school_admin, staff_user):
        save_geofence(
            tenant=geo_tenant,
            user=school_admin,
            vertices=SQUARE,
            buffer_meters=5,
            is_enabled=True,
        )
        from apps.academics.models import AcademicYear, Class
        from apps.students.models import Student
        from datetime import date

        year = AcademicYear.objects.create(
            tenant=geo_tenant,
            name="2025-2026",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            is_current=True,
        )
        school_class = Class.objects.create(
            tenant=geo_tenant,
            name="P.1",
            code="P1",
            academic_year=year,
        )
        student = Student.objects.create(
            tenant=geo_tenant,
            admission_number="GEO-001",
            first_name="Kid",
            last_name="One",
            date_of_birth=date(2015, 1, 1),
            enrollment_date=date(2025, 1, 15),
            gender="male",
            school_class=school_class,
            status="active",
        )
        # Grant teacher access via school-wide: school_admin path is simpler for forbidden check
        client = APIClient()
        client.force_authenticate(user=school_admin)
        response = client.post("/api/v1/attendance/class-marking/bulk/", {
            "school_class": str(school_class.id),
            "date": date.today().isoformat(),
            "lat": OUTSIDE[0],
            "lng": OUTSIDE[1],
            "accuracy_m": 8,
            "entries": [{"student": str(student.id), "present": True}],
        }, format="json")
        assert response.status_code == 400
        body = response.json()
        assert body.get("code") in ("outside", "outside_geofence") or "outside" in (body.get("message") or "").lower()

    def test_class_bulk_allowed_inside(self, geo_tenant, school_admin):
        save_geofence(
            tenant=geo_tenant,
            user=school_admin,
            vertices=SQUARE,
            buffer_meters=5,
            is_enabled=True,
        )
        from apps.academics.models import AcademicYear, Class
        from apps.students.models import Student
        from datetime import date

        year = AcademicYear.objects.create(
            tenant=geo_tenant,
            name="2025-2026B",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            is_current=True,
        )
        school_class = Class.objects.create(
            tenant=geo_tenant,
            name="P.2",
            code="P2",
            academic_year=year,
        )
        student = Student.objects.create(
            tenant=geo_tenant,
            admission_number="GEO-002",
            first_name="Kid",
            last_name="Two",
            date_of_birth=date(2015, 1, 1),
            enrollment_date=date(2025, 1, 15),
            gender="female",
            school_class=school_class,
            status="active",
        )
        client = APIClient()
        client.force_authenticate(user=school_admin)
        response = client.post("/api/v1/attendance/class-marking/bulk/", {
            "school_class": str(school_class.id),
            "date": date.today().isoformat(),
            "lat": INSIDE[0],
            "lng": INSIDE[1],
            "accuracy_m": 8,
            "entries": [{"student": str(student.id), "present": True}],
        }, format="json")
        assert response.status_code == 200
        assert response.json()["data"]["saved"] >= 1
