"""HR RBAC and leave workflow tests."""
from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.core.constants import UserRole
from apps.hr.constants import LEAVE_PENDING
from apps.hr.models import Leave
from apps.staff.services import onboard_staff
from apps.subscriptions.services import assign_plan_features
from apps.tenants.role_feature_defaults import get_default_feature_permission
from apps.tenants.role_permissions import get_user_feature_permissions, user_can_access_feature


@pytest.fixture
def hr_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="HR RBAC Plan", slug="hr-rbac", max_students=500)
    assign_plan_features(plan, [
        "hr_manager_workspace", "staff_management", "hr_departments", "positions",
        "leave_types", "leave_requests", "performance_reviews", "staff_contracts",
        "staff_discipline", "staff_qualifications", "staff_documents", "work_schedules",
        "hr_reports", "hr_analytics", "staff_attendance",
    ])
    return plan


@pytest.fixture
def hr_tenant(db, hr_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="HR RBAC School",
        code="HRRB",
        email="hrrb@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=hr_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def hr_manager(db, hr_tenant):
    return onboard_staff(
        hr_tenant,
        data={
            "first_name": "Human",
            "last_name": "Resources",
            "email": "hr.manager@test.edu",
            "phone": "+254700000601",
            "portal_role": UserRole.HR_MANAGER,
            "date_joined": "2026-01-01",
        },
    )


@pytest.mark.django_db
class TestHRRbac:
    def test_hr_manager_default_permissions(self):
        assert get_default_feature_permission(UserRole.HR_MANAGER, "hr_manager_workspace") == {
            "can_read": True, "can_write": True,
        }
        assert get_default_feature_permission(UserRole.HR_MANAGER, "salary_structures") == {
            "can_read": True, "can_write": False,
        }

    def test_hr_manager_workspace_api(self, hr_tenant, hr_manager):
        client = APIClient()
        client.force_authenticate(user=hr_manager.user)
        response = client.get("/api/v1/hr/workspace/")
        assert response.status_code == 200
        data = response.data.get("data", response.data)
        assert data["role"] == UserRole.HR_MANAGER
        assert "features" in data

    def test_leave_approval_workflow(self, hr_tenant, hr_manager):
        leave = Leave.objects.create(
            tenant=hr_tenant,
            staff=hr_manager,
            leave_type="annual",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 5),
            days=5,
            reason="Family event",
            status=LEAVE_PENDING,
        )
        client = APIClient()
        client.force_authenticate(user=hr_manager.user)
        response = client.post(f"/api/v1/hr/leaves/{leave.id}/approve/")
        assert response.status_code == 200
        leave.refresh_from_db()
        assert leave.status == "approved"

    def test_leave_write_denied_when_revoked(self, hr_tenant, hr_manager):
        from apps.tenants.models import SchoolRoleFeaturePermission

        SchoolRoleFeaturePermission.objects.create(
            tenant=hr_tenant,
            role=UserRole.HR_MANAGER,
            feature_key="leave_requests",
            can_read=True,
            can_write=False,
        )
        assert not user_can_access_feature(
            hr_tenant, hr_manager.user, "leave_requests", require_write=True,
        )
        perms = get_user_feature_permissions(hr_tenant, hr_manager.user)
        assert perms["leave_requests"]["can_write"] is False

        leave = Leave.objects.create(
            tenant=hr_tenant,
            staff=hr_manager,
            leave_type="sick",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 2),
            days=2,
            reason="Medical",
            status=LEAVE_PENDING,
        )
        client = APIClient()
        client.force_authenticate(user=hr_manager.user)
        response = client.post(f"/api/v1/hr/leaves/{leave.id}/approve/")
        assert response.status_code == 403