"""Subscription lifecycle notification tests."""
from __future__ import annotations

import pytest
from rest_framework import status

from apps.communication.models import Notification
from apps.subscriptions.models import Plan, Subscription


@pytest.mark.django_db
class TestSubscriptionNotifications:
    def test_activate_notifies_school_admin(self, api_client, super_admin, tenant, plan, school_admin):
        sub = Subscription.objects.create(tenant=tenant, plan=plan, status="trial")
        Notification.objects.filter(recipient=school_admin).delete()

        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            f"/api/v1/subscriptions/{sub.id}/activate/",
            {"period_days": 45},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        notice = Notification.objects.filter(recipient=school_admin, is_deleted=False).latest("created_at")
        assert notice.title == "Subscription activated"
        assert notice.metadata["event"] == "subscription_activated"

    def test_suspend_notifies_school_admin(self, api_client, super_admin, tenant, plan, school_admin):
        sub = tenant.active_subscription
        Notification.objects.filter(recipient=school_admin).delete()

        api_client.force_authenticate(user=super_admin)
        response = api_client.post(f"/api/v1/subscriptions/{sub.id}/suspend/")
        assert response.status_code == status.HTTP_200_OK

        notice = Notification.objects.filter(recipient=school_admin, is_deleted=False).latest("created_at")
        assert notice.title == "Subscription suspended"
        assert notice.metadata["event"] == "subscription_suspended"

    def test_create_subscription_notifies_school_admin(self, api_client, super_admin, tenant, plan, school_admin):
        extra_plan = Plan.objects.create(name="Extra Plan", slug="extra_plan_notify", is_active=True)
        Notification.objects.filter(recipient=school_admin).delete()

        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            "/api/v1/subscriptions/",
            {"tenant": str(tenant.id), "plan": str(extra_plan.id), "billing_cycle": "monthly"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

        notice = Notification.objects.filter(recipient=school_admin, is_deleted=False).latest("created_at")
        assert notice.title == "New subscription assigned"
        assert notice.metadata["event"] == "subscription_created"
        assert notice.metadata["plan_slug"] == extra_plan.slug