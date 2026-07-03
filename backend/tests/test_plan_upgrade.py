"""School-admin plan upgrade flow tests."""
from __future__ import annotations

import pytest
from rest_framework import status

from apps.communication.models import Notification
from apps.core.constants import PlanSlug
from apps.subscriptions.models import PaymentTransaction, Plan, Subscription


@pytest.mark.django_db
class TestPlanUpgrade:
    def test_premium_catalog_offers_premium_plus(self, api_client, school_admin, tenant, plan):
        premium, _ = Plan.objects.update_or_create(
            slug=PlanSlug.PREMIUM,
            defaults={
                "name": "Premium",
                "is_active": True,
                "is_public": False,
                "price_monthly": 99,
                "price_yearly": 990,
            },
        )
        premium_plus, _ = Plan.objects.update_or_create(
            slug=PlanSlug.PREMIUM_PLUS,
            defaults={
                "name": "Premium Plus",
                "is_active": True,
                "is_public": False,
                "price_monthly": 199,
                "price_yearly": 1990,
            },
        )
        Subscription.objects.filter(tenant=tenant).update(plan=premium)

        api_client.force_authenticate(user=school_admin)
        response = api_client.get("/api/v1/subscriptions/upgrade/catalog/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert data["is_top_tier"] is False
        assert data["current_plan_slug"] == PlanSlug.PREMIUM
        assert data["current_plan"]["slug"] == PlanSlug.PREMIUM
        upgrade_slugs = [p["slug"] for p in data["upgrade_plans"]]
        assert upgrade_slugs == [PlanSlug.PREMIUM_PLUS]

    def test_premium_plus_catalog_is_top_tier(self, api_client, school_admin, tenant, plan):
        premium_plus, _ = Plan.objects.update_or_create(
            slug=PlanSlug.PREMIUM_PLUS,
            defaults={
                "name": "Premium Plus",
                "is_active": True,
                "is_public": True,
                "price_monthly": 199,
                "price_yearly": 1990,
            },
        )
        Subscription.objects.filter(tenant=tenant).update(plan=premium_plus)

        api_client.force_authenticate(user=school_admin)
        response = api_client.get("/api/v1/subscriptions/upgrade/catalog/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert data["is_top_tier"] is True
        assert data["upgrade_plans"] == []

    def test_catalog_lists_upgrade_plans(self, api_client, school_admin, tenant, plan):
        Plan.objects.get_or_create(
            slug=PlanSlug.PREMIUM,
            defaults={"name": "Premium", "is_active": True, "is_public": True, "price_monthly": 49},
        )
        api_client.force_authenticate(user=school_admin)
        response = api_client.get("/api/v1/subscriptions/upgrade/catalog/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert data["current_plan"]["slug"] == plan.slug
        assert len(data["upgrade_plans"]) >= 1
        assert len(data["payment_methods"]) >= 2
        method_types = {m["type"] for m in data["payment_methods"]}
        assert "card" in method_types
        assert "mobile_money" in method_types

    def test_checkout_fails_with_dummy_gateway(self, api_client, school_admin, tenant, plan):
        premium, _ = Plan.objects.get_or_create(
            slug=PlanSlug.PREMIUM,
            defaults={
                "name": "Premium Upgrade",
                "is_active": True,
                "is_public": True,
                "price_monthly": 99,
                "price_yearly": 999,
            },
        )
        if premium.price_monthly <= 0:
            premium.price_monthly = 99
            premium.price_yearly = 999
            premium.is_public = True
            premium.save()
        Notification.objects.filter(recipient=school_admin).delete()

        api_client.force_authenticate(user=school_admin)
        response = api_client.post(
            "/api/v1/subscriptions/upgrade/checkout/",
            {
                "plan_slug": premium.slug,
                "billing_cycle": "monthly",
                "payment_method": "card",
                "provider_slug": "stripe",
                "payer_name": "School Admin",
                "card_last_four": "4242",
                "card_brand": "visa",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert response.data["success"] is False
        assert "failed" in response.data["message"].lower() or "not connected" in response.data["message"].lower()

        txn = PaymentTransaction.objects.filter(tenant=tenant).order_by("-created_at").first()
        assert txn is not None
        assert txn.status == "failed"

        notice = Notification.objects.filter(recipient=school_admin, is_deleted=False).latest("created_at")
        assert notice.metadata["event"] == "upgrade_payment_failed"
        assert txn.payment_method == "card"

    def test_mobile_money_checkout_fails(self, api_client, school_admin, tenant, plan):
        premium, _ = Plan.objects.get_or_create(
            slug=PlanSlug.PREMIUM,
            defaults={
                "name": "Premium Upgrade",
                "is_active": True,
                "is_public": True,
                "price_monthly": 99,
                "price_yearly": 999,
            },
        )
        if premium.price_monthly <= 0:
            premium.price_monthly = 99
            premium.price_yearly = 999
            premium.is_public = True
            premium.save()

        api_client.force_authenticate(user=school_admin)
        response = api_client.post(
            "/api/v1/subscriptions/upgrade/checkout/",
            {
                "plan_slug": premium.slug,
                "billing_cycle": "monthly",
                "payment_method": "mobile_money",
                "provider_slug": "mpesa",
                "phone_number": "+256700123456",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert "mobile money" in response.data["message"].lower()

        txn = PaymentTransaction.objects.filter(tenant=tenant).order_by("-created_at").first()
        assert txn.payment_method == "mobile_money"
        assert txn.payer_phone.endswith("3456")