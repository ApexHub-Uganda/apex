"""Subscription tests."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from apps.core.constants import PlanSlug
from apps.subscriptions.models import FeatureFlag, Plan, Subscription
from apps.subscriptions.seed_features import seed_feature_catalog, seed_plan_defaults


@pytest.mark.django_db
class TestSubscriptions:
    def test_list_public_plans(self, api_client, plan):
        response = api_client.get("/api/v1/subscriptions/plans/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_tenant_has_feature_from_plan(self, tenant, plan):
        from apps.subscriptions.services import assign_plan_features, invalidate_tenant_cache
        seed_feature_catalog()
        assign_plan_features(plan, ["library_management"])
        invalidate_tenant_cache(str(tenant.id))
        assert tenant.has_feature("library_management") is True
        assert tenant.has_feature("hostel_management") is False

    def test_subscription_expiry(self, tenant, plan):
        sub = Subscription.objects.get(tenant=tenant)
        sub.status = "active"
        sub.current_period_end = timezone.now() - timedelta(days=1)
        sub.grace_period_ends_at = timezone.now() - timedelta(days=1)
        sub.save()
        assert sub.is_expired is True
        assert sub.in_grace_period is False

    def test_subscription_grace_period(self, tenant, plan):
        sub = Subscription.objects.get(tenant=tenant)
        sub.status = "grace_period"
        sub.current_period_end = timezone.now() - timedelta(days=1)
        sub.grace_period_ends_at = timezone.now() + timedelta(days=5)
        sub.save()
        assert sub.is_expired is True
        assert sub.in_grace_period is True

    def test_current_subscription_endpoint(self, api_client, school_admin, tenant, plan):
        api_client.force_authenticate(user=school_admin)
        response = api_client.get("/api/v1/subscriptions/current/")
        assert response.status_code == status.HTTP_200_OK
        assert str(response.data["tenant"]) == str(tenant.id)

    def test_plan_feature_catalog_assignment(self, plan):
        seed_feature_catalog()
        from apps.subscriptions.services import assign_plan_features
        assign_plan_features(plan, ["library_management", "dashboard_analytics"])
        assert plan.feature_flags.get("library_management") is True
        assert plan.feature_flags.get("dashboard_analytics") is True
        assert FeatureFlag.objects.filter(feature_key="student_management").exists()

    def test_feature_catalog_api(self, api_client, super_admin):
        from apps.subscriptions.module_registry import all_module_feature_keys

        seed_feature_catalog()
        api_client.force_authenticate(user=super_admin)
        response = api_client.get("/api/v1/subscriptions/features/catalog/")
        assert response.status_code == status.HTTP_200_OK
        expected = len(all_module_feature_keys())
        assert response.data["data"]["total_features"] == expected
        assert expected >= 75