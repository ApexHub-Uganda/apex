"""Hostel RBAC, scoping, and allocation workflow tests."""
from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class, Term
from apps.core.constants import UserRole
from apps.hostel.constants import ALLOCATION_ACTIVE, ALLOCATION_CHECKED_IN, ALLOCATION_VACATED
from apps.hostel.models import Allocation, Hostel, Room
from apps.staff.services import onboard_staff
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features
from apps.tenants.role_feature_defaults import get_default_feature_permission
from apps.tenants.role_permissions import get_user_feature_permissions


@pytest.fixture
def hostel_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Hostel RBAC Plan", slug="hostel-rbac", max_students=500)
    assign_plan_features(plan, [
        "hostel_manager_workspace",
        "hostel_management",
        "rooms",
        "room_allocation",
        "hostel_maintenance",
        "hostel_visitors",
        "hostel_discipline",
        "hostel_inventory",
        "hostel_fees",
        "hostel_reports",
        "student_management",
        "dashboard_analytics",
    ])
    return plan


@pytest.fixture
def hostel_tenant(db, hostel_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Hostel RBAC School",
        code="HSTR",
        email="hstr@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=hostel_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def hostel_manager(db, hostel_tenant):
    return onboard_staff(
        hostel_tenant,
        data={
            "first_name": "Mary",
            "last_name": "Warden",
            "email": "mary.warden@test.edu",
            "phone": "+254700000601",
            "portal_role": UserRole.HOSTEL_MANAGER,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def other_hostel_manager(db, hostel_tenant):
    return onboard_staff(
        hostel_tenant,
        data={
            "first_name": "John",
            "last_name": "Warden",
            "email": "john.warden@test.edu",
            "phone": "+254700000602",
            "portal_role": UserRole.HOSTEL_MANAGER,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def hostel_setup(db, hostel_tenant, hostel_manager, other_hostel_manager):
    year = AcademicYear.objects.create(
        tenant=hostel_tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    school_class = Class.objects.create(
        tenant=hostel_tenant, name="Grade 7", code="G7", academic_year=year,
    )
    student = Student.objects.create(
        tenant=hostel_tenant,
        admission_number="HST-001",
        first_name="Grace",
        last_name="Nambi",
        date_of_birth=date(2013, 4, 4),
        gender="female",
        school_class=school_class,
        enrollment_date=date(2026, 1, 10),
        status="active",
    )
    hostel_a = Hostel.objects.create(
        tenant=hostel_tenant,
        name="Girls Hostel A",
        gender="female",
        warden=hostel_manager,
        capacity=40,
    )
    hostel_b = Hostel.objects.create(
        tenant=hostel_tenant,
        name="Boys Hostel B",
        gender="male",
        warden=other_hostel_manager,
        capacity=40,
    )
    room_a = Room.objects.create(
        tenant=hostel_tenant,
        hostel=hostel_a,
        room_number="A-101",
        capacity=4,
    )
    room_b = Room.objects.create(
        tenant=hostel_tenant,
        hostel=hostel_b,
        room_number="B-101",
        capacity=4,
    )
    return {
        "student": student,
        "hostel_a": hostel_a,
        "hostel_b": hostel_b,
        "room_a": room_a,
        "room_b": room_b,
        "year": year,
    }


@pytest.mark.django_db
class TestHostelRoleDefaults:
    def test_hostel_manager_has_workspace_and_reports_read(self):
        assert get_default_feature_permission(UserRole.HOSTEL_MANAGER, "hostel_manager_workspace") == {
            "can_read": True, "can_write": True,
        }
        assert get_default_feature_permission(UserRole.HOSTEL_MANAGER, "hostel_reports") == {
            "can_read": True, "can_write": False,
        }
        assert get_default_feature_permission(UserRole.HOSTEL_MANAGER, "dashboard_analytics") == {
            "can_read": True, "can_write": False,
        }

    def test_hostel_manager_effective_permissions(self, hostel_tenant, hostel_manager):
        perms = get_user_feature_permissions(hostel_tenant, hostel_manager.user)
        assert perms["room_allocation"]["can_write"] is True
        assert perms["hostel_maintenance"]["can_write"] is True
        assert perms["hostel_reports"]["can_read"] is True
        assert perms.get("hostel_reports", {}).get("can_write") in (None, False)


@pytest.mark.django_db
class TestHostelScopingAPI:
    def test_warden_sees_only_assigned_hostel(self, hostel_setup, hostel_manager, other_hostel_manager):
        client = APIClient()
        client.force_authenticate(user=hostel_manager.user)
        response = client.get("/api/v1/hostel/")
        assert response.status_code == 200
        hostel_ids = {item["id"] for item in response.data["results"]}
        assert str(hostel_setup["hostel_a"].id) in hostel_ids
        assert str(hostel_setup["hostel_b"].id) not in hostel_ids

        other_client = APIClient()
        other_client.force_authenticate(user=other_hostel_manager.user)
        other_response = other_client.get("/api/v1/hostel/")
        other_ids = {item["id"] for item in other_response.data["results"]}
        assert str(hostel_setup["hostel_b"].id) in other_ids
        assert str(hostel_setup["hostel_a"].id) not in other_ids

    def test_school_admin_sees_all_hostels(self, hostel_setup, hostel_tenant):
        from django.contrib.auth import get_user_model

        admin = get_user_model().objects.create_user(
            email="hostel-admin@test.edu",
            password="TestPass@2026",
            first_name="Hostel",
            last_name="Admin",
            role=UserRole.SCHOOL_ADMIN,
            tenant=hostel_tenant,
            is_email_verified=True,
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get("/api/v1/hostel/")
        assert response.status_code == 200
        assert response.data["count"] == 2


@pytest.mark.django_db
class TestHostelWorkflowAPI:
    def test_allocate_check_in_vacate_syncs_room_occupied(self, hostel_setup, hostel_manager):
        client = APIClient()
        client.force_authenticate(user=hostel_manager.user)
        allocate = client.post(
            "/api/v1/hostel/allocations/allocate/",
            {
                "student": str(hostel_setup["student"].id),
                "room": str(hostel_setup["room_a"].id),
                "start_date": "2026-03-01",
                "bed_number": "B1",
            },
            format="json",
        )
        assert allocate.status_code in (200, 201)
        allocation = Allocation.objects.get(pk=allocate.data["data"]["id"])
        assert allocation.status == ALLOCATION_ACTIVE

        hostel_setup["room_a"].refresh_from_db()
        assert hostel_setup["room_a"].occupied == 1

        check_in = client.post(f"/api/v1/hostel/allocations/{allocation.id}/check-in/")
        assert check_in.status_code == 200
        allocation.refresh_from_db()
        assert allocation.status == ALLOCATION_CHECKED_IN

        vacate = client.post(f"/api/v1/hostel/allocations/{allocation.id}/vacate/")
        assert vacate.status_code == 200
        allocation.refresh_from_db()
        assert allocation.status == ALLOCATION_VACATED
        hostel_setup["room_a"].refresh_from_db()
        assert hostel_setup["room_a"].occupied == 0

    def test_warden_cannot_allocate_outside_assigned_hostel(self, hostel_setup, hostel_manager):
        client = APIClient()
        client.force_authenticate(user=hostel_manager.user)
        response = client.post(
            "/api/v1/hostel/allocations/allocate/",
            {
                "student": str(hostel_setup["student"].id),
                "room": str(hostel_setup["room_b"].id),
                "start_date": "2026-03-01",
            },
            format="json",
        )
        assert response.status_code == 404

    def test_hostel_workspace_api(self, hostel_tenant, hostel_manager):
        client = APIClient()
        client.force_authenticate(user=hostel_manager.user)
        response = client.get("/api/v1/hostel/workspace/")
        assert response.status_code == 200
        assert response.data["data"]["role"] == UserRole.HOSTEL_MANAGER
        assert response.data["data"]["is_school_wide"] is False

    def test_hostel_reports_api(self, hostel_setup, hostel_manager):
        client = APIClient()
        client.force_authenticate(user=hostel_manager.user)
        response = client.get("/api/v1/hostel/reports/")
        assert response.status_code == 200
        assert len(response.data["data"]["rows"]) == 1
        assert response.data["data"]["summary"]["hostels"] == 1

    def test_permission_matrix_includes_hostel_manager(self, hostel_tenant, hostel_manager):
        from django.contrib.auth import get_user_model

        admin = get_user_model().objects.create_user(
            email="hostel-matrix-admin@test.edu",
            password="TestPass@2026",
            first_name="Matrix",
            last_name="Admin",
            role=UserRole.SCHOOL_ADMIN,
            tenant=hostel_tenant,
            is_email_verified=True,
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get("/api/v1/tenants/role-permissions/")
        role_keys = {r["key"] for r in response.data["data"]["roles"]}
        assert UserRole.HOSTEL_MANAGER in role_keys