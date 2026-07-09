"""Phase 3–5 hostel workflow API tests."""
from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class
from apps.core.constants import UserRole
from apps.hostel.constants import MAINTENANCE_REPORTED, VISITOR_CHECKED_IN
from apps.hostel.models import Hostel, HostelMaintenance, HostelVisitor, Room
from apps.staff.services import onboard_staff
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def hostel_workflow_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Hostel Workflow Plan", slug="hst-workflow", max_students=500)
    assign_plan_features(plan, [
        "hostel_manager_workspace", "hostel_management", "rooms", "room_allocation",
        "hostel_maintenance", "hostel_visitors", "hostel_reports", "student_management",
    ])
    return plan


@pytest.fixture
def hostel_workflow_tenant(db, hostel_workflow_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Hostel Workflow School",
        code="HSTW",
        email="hstw@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=hostel_workflow_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def hostel_mgr(db, hostel_workflow_tenant):
    return onboard_staff(
        hostel_workflow_tenant,
        data={
            "first_name": "Hostel",
            "last_name": "Manager",
            "email": "hostel.mgr@test.edu",
            "phone": "+254700000901",
            "portal_role": UserRole.HOSTEL_MANAGER,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def hostel_wf_setup(db, hostel_workflow_tenant, hostel_mgr):
    year = AcademicYear.objects.create(
        tenant=hostel_workflow_tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    school_class = Class.objects.create(
        tenant=hostel_workflow_tenant, name="Grade 8", code="G8", academic_year=year,
    )
    student = Student.objects.create(
        tenant=hostel_workflow_tenant,
        admission_number="HSTW-001",
        first_name="Peter",
        last_name="Okello",
        date_of_birth=date(2012, 3, 3),
        gender="male",
        school_class=school_class,
        enrollment_date=date(2026, 1, 10),
        status="active",
    )
    hostel = Hostel.objects.create(
        tenant=hostel_workflow_tenant,
        name="Boys Hostel",
        gender="male",
        warden=hostel_mgr,
        capacity=50,
    )
    room = Room.objects.create(
        tenant=hostel_workflow_tenant,
        hostel=hostel,
        room_number="101",
        capacity=4,
    )
    return {"student": student, "hostel": hostel, "room": room}


@pytest.mark.django_db
class TestHostelWorkflowAPI:
    def test_visitor_check_out(self, hostel_wf_setup, hostel_mgr):
        visitor = HostelVisitor.objects.create(
            tenant=hostel_wf_setup["hostel"].tenant,
            hostel=hostel_wf_setup["hostel"],
            student=hostel_wf_setup["student"],
            visitor_name="John Parent",
            purpose="Visit",
            status=VISITOR_CHECKED_IN,
        )
        client = APIClient()
        client.force_authenticate(user=hostel_mgr.user)
        response = client.post(f"/api/v1/hostel/visitors/{visitor.id}/check-out/")
        assert response.status_code == 200
        visitor.refresh_from_db()
        assert visitor.status == "checked_out"

    def test_resolve_maintenance(self, hostel_wf_setup, hostel_mgr):
        maintenance = HostelMaintenance.objects.create(
            tenant=hostel_wf_setup["hostel"].tenant,
            hostel=hostel_wf_setup["hostel"],
            room=hostel_wf_setup["room"],
            title="Broken window",
            description="Window pane cracked",
            status=MAINTENANCE_REPORTED,
            reported_by=hostel_mgr.user,
        )
        client = APIClient()
        client.force_authenticate(user=hostel_mgr.user)
        response = client.post(f"/api/v1/hostel/maintenance/{maintenance.id}/resolve/")
        assert response.status_code == 200
        maintenance.refresh_from_db()
        assert maintenance.status == "completed"

    def test_hostel_reports_typed(self, hostel_wf_setup, hostel_mgr):
        client = APIClient()
        client.force_authenticate(user=hostel_mgr.user)
        response = client.get("/api/v1/hostel/reports/?type=occupancy")
        assert response.status_code == 200
        assert len(response.data["data"]["rows"]) >= 1

    def test_workspace_hostel_key_aliases(self, hostel_wf_setup, hostel_mgr):
        client = APIClient()
        client.force_authenticate(user=hostel_mgr.user)
        response = client.get("/api/v1/hostel/workspace/")
        assert response.status_code == 200
        counts = response.data["data"]["counts"]
        assert counts["hostels"] == counts["total_hostels"]
        assert counts["rooms"] == counts["total_rooms"]
        assert counts["available_beds"] == counts["vacant_beds"]