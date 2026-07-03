"""Super-admin tenant administration tests."""
from __future__ import annotations

import pytest
from rest_framework import status

from apps.communication.models import Notification
from apps.subscriptions.models import Plan, Subscription
from apps.tenants.models import Tenant


@pytest.mark.django_db
class TestTenantAdministration:
    def test_deletion_preview(self, api_client, super_admin, tenant):
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(f"/api/v1/tenants/{tenant.id}/deletion-preview/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert data["school"]["id"] == str(tenant.id)
        assert "summary" in data
        assert data["confirmation_required"] == tenant.name

    def test_change_plan(self, api_client, super_admin, tenant, plan, school_admin):
        premium = Plan.objects.create(name="Premium Test", slug="premium_test_admin", is_active=True)
        from apps.subscriptions.services import assign_plan_features
        assign_plan_features(premium, ["library_management", "dashboard_analytics"])

        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            f"/api/v1/tenants/{tenant.id}/change-plan/",
            {
                "plan_slug": premium.slug,
                "billing_cycle": "yearly",
                "subscription_status": "active",
                "period_days": 60,
                "notes": "Upgraded by super admin",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        sub = tenant.active_subscription
        assert sub.plan.slug == premium.slug
        assert sub.billing_cycle == "yearly"
        assert sub.status == "active"

        notifications = Notification.objects.filter(recipient=school_admin, is_deleted=False)
        assert notifications.count() == 1
        notice = notifications.first()
        assert notice.title == "Subscription plan updated"
        assert "Premium Test" in notice.message
        assert notice.metadata["event"] == "plan_changed"
        assert notice.metadata["payment_pending"] is True
        assert notice.action_url.endswith("/school-admin/notifications")

    def test_change_plan_notifies_without_completed_payment(self, api_client, super_admin, tenant, plan, school_admin):
        trial_plan = Plan.objects.create(name="Trial Plan", slug="trial_plan_notify", is_active=True, trial_days=14)

        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            f"/api/v1/tenants/{tenant.id}/change-plan/",
            {
                "plan_slug": trial_plan.slug,
                "billing_cycle": "monthly",
                "subscription_status": "trial",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        notice = Notification.objects.filter(recipient=school_admin, is_deleted=False).latest("created_at")
        assert notice.metadata["subscription_status"] == "trial"
        assert notice.metadata["payment_pending"] is True
        assert "Payment has not been completed yet" in notice.message

    def test_permanent_delete_requires_confirmation(self, api_client, super_admin, tenant):
        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            f"/api/v1/tenants/{tenant.id}/permanent-delete/",
            {"confirmation_name": "Wrong Name", "acknowledge_permanent": True},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Tenant.objects.filter(id=tenant.id).exists()

    def test_permanent_delete_success(self, api_client, super_admin, tenant):
        tenant_id = tenant.id
        school_name = tenant.name
        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            f"/api/v1/tenants/{tenant_id}/permanent-delete/",
            {"confirmation_name": school_name, "acknowledge_permanent": True},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert not Tenant.objects.filter(id=tenant_id).exists()
        assert Subscription.objects.filter(tenant_id=tenant_id).count() == 0

    def test_destroy_disabled(self, api_client, super_admin, tenant):
        api_client.force_authenticate(user=super_admin)
        response = api_client.delete(f"/api/v1/tenants/{tenant.id}/")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED