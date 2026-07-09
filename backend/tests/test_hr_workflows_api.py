"""Phase 3–5 HR workflow API tests."""
from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.core.constants import UserRole
from apps.hr.constants import LEAVE_PENDING, REVIEW_DRAFT
from apps.hr.models import Leave, PerformanceReview
from apps.staff.services import onboard_staff
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def hr_workflow_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="HR Workflow Plan", slug="hr-workflow", max_students=500)
    assign_plan_features(plan, [
        "hr_manager_workspace", "staff_management", "leave_requests",
        "performance_reviews", "hr_reports", "hr_analytics",
    ])
    return plan


@pytest.fixture
def hr_workflow_tenant(db, hr_workflow_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="HR Workflow School",
        code="HRWF",
        email="hrwf@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=hr_workflow_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def hr_mgr(db, hr_workflow_tenant):
    return onboard_staff(
        hr_workflow_tenant,
        data={
            "first_name": "HR",
            "last_name": "Manager",
            "email": "hr.mgr@test.edu",
            "phone": "+254700000701",
            "portal_role": UserRole.HR_MANAGER,
            "date_joined": "2026-01-01",
        },
    )


@pytest.mark.django_db
class TestHRWorkflowAPI:
    def test_workspace_has_pending_leave_counts(self, hr_workflow_tenant, hr_mgr):
        Leave.objects.create(
            tenant=hr_workflow_tenant,
            staff=hr_mgr,
            leave_type="annual",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 3),
            days=3,
            reason="Test",
            status=LEAVE_PENDING,
        )
        client = APIClient()
        client.force_authenticate(user=hr_mgr.user)
        response = client.get("/api/v1/hr/workspace/")
        assert response.status_code == 200
        counts = response.data["data"]["counts"]
        assert counts["pending_leaves"] >= 1
        assert counts["pending_leave"] >= 1

    def test_approval_queue_lists_pending_leaves(self, hr_workflow_tenant, hr_mgr):
        leave = Leave.objects.create(
            tenant=hr_workflow_tenant,
            staff=hr_mgr,
            leave_type="sick",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 2),
            days=2,
            reason="Medical",
            status=LEAVE_PENDING,
        )
        client = APIClient()
        client.force_authenticate(user=hr_mgr.user)
        response = client.get("/api/v1/hr/approval-queue/")
        assert response.status_code == 200
        assert response.data["data"]["count"] >= 1
        assert any(item["id"] == str(leave.id) for item in response.data["data"]["leaves"])

    def test_bulk_approve_leaves(self, hr_workflow_tenant, hr_mgr):
        leave = Leave.objects.create(
            tenant=hr_workflow_tenant,
            staff=hr_mgr,
            leave_type="annual",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 5),
            days=5,
            reason="Holiday",
            status=LEAVE_PENDING,
        )
        client = APIClient()
        client.force_authenticate(user=hr_mgr.user)
        response = client.post(
            "/api/v1/hr/workflow/bulk/",
            {"action": "approve", "leave_ids": [str(leave.id)]},
            format="json",
        )
        assert response.status_code == 200
        leave.refresh_from_db()
        assert leave.status == "approved"

    def test_reject_leave(self, hr_workflow_tenant, hr_mgr):
        leave = Leave.objects.create(
            tenant=hr_workflow_tenant,
            staff=hr_mgr,
            leave_type="unpaid",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 2),
            days=2,
            reason="Personal",
            status=LEAVE_PENDING,
        )
        client = APIClient()
        client.force_authenticate(user=hr_mgr.user)
        response = client.post(
            f"/api/v1/hr/leaves/{leave.id}/reject/",
            {"reason": "Insufficient coverage"},
            format="json",
        )
        assert response.status_code == 200
        leave.refresh_from_db()
        assert leave.status == "rejected"

    def test_hr_reports_api(self, hr_workflow_tenant, hr_mgr):
        client = APIClient()
        client.force_authenticate(user=hr_mgr.user)
        response = client.get("/api/v1/hr/reports/?type=summary")
        assert response.status_code == 200
        assert "summary" in response.data["data"]

    def test_hr_analytics_api(self, hr_workflow_tenant, hr_mgr):
        client = APIClient()
        client.force_authenticate(user=hr_mgr.user)
        response = client.get("/api/v1/hr/analytics/")
        assert response.status_code == 200
        assert "summary" in response.data["data"]

    def test_submit_performance_review(self, hr_workflow_tenant, hr_mgr):
        review = PerformanceReview.objects.create(
            tenant=hr_workflow_tenant,
            staff=hr_mgr,
            reviewer=hr_mgr.user,
            review_period_start=date(2026, 1, 1),
            review_period_end=date(2026, 6, 30),
            overall_rating=4,
            status=REVIEW_DRAFT,
        )
        client = APIClient()
        client.force_authenticate(user=hr_mgr.user)
        response = client.post(f"/api/v1/hr/performance-reviews/{review.id}/submit/")
        assert response.status_code == 200
        review.refresh_from_db()
        assert review.status == "submitted"