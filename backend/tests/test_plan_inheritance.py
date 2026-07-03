"""Plan tier feature inheritance tests."""
from __future__ import annotations

import pytest
from rest_framework import status

from apps.core.constants import PlanSlug
from apps.subscriptions.models import Plan
from apps.subscriptions.plan_tiers import get_plan_feature_breakdown, merge_plan_feature_keys
from apps.subscriptions.services import assign_plan_features
from apps.subscriptions.seed_features import seed_feature_catalog


@pytest.mark.django_db
class TestPlanInheritance:
    @pytest.fixture(autouse=True)
    def setup_catalog(self, db):
        seed_feature_catalog()

    def test_merge_adds_lower_tier_features(self):
        basic = Plan.objects.create(name="Basic", slug=PlanSlug.BASIC, is_active=True)
        premium = Plan.objects.create(name="Premium", slug=PlanSlug.PREMIUM, is_active=True)
        assign_plan_features(basic, ["student_management", "classes"])
        merged = merge_plan_feature_keys(premium.slug, ["library_management"])
        assert "student_management" in merged
        assert "classes" in merged
        assert "library_management" in merged

    def test_assign_plan_features_auto_inherits(self):
        basic = Plan.objects.create(name="Basic", slug=PlanSlug.BASIC, is_active=True)
        premium = Plan.objects.create(name="Premium", slug=PlanSlug.PREMIUM, is_active=True)
        assign_plan_features(basic, ["student_management", "classes"])
        assign_plan_features(premium, ["library_management"])
        premium_keys = set(premium.features.values_list("feature_key", flat=True))
        assert {"student_management", "classes", "library_management"}.issubset(premium_keys)

    def test_feature_breakdown_for_premium(self):
        basic = Plan.objects.create(name="Basic", slug=PlanSlug.BASIC, is_active=True)
        premium = Plan.objects.create(name="Premium", slug=PlanSlug.PREMIUM, is_active=True)
        assign_plan_features(basic, ["student_management", "classes"])
        assign_plan_features(premium, ["student_management", "classes", "library_management"])
        breakdown = get_plan_feature_breakdown(premium)
        assert breakdown["inherits_from_slug"] == PlanSlug.BASIC
        assert breakdown["inherited_feature_count"] == 2
        assert breakdown["exclusive_feature_count"] == 1
        assert "Everything in Basic" in breakdown["inherited_summary"]

    def test_super_admin_cannot_remove_inherited_features(self, api_client, super_admin):
        basic = Plan.objects.create(name="Basic", slug=PlanSlug.BASIC, is_active=True)
        premium = Plan.objects.create(name="Premium", slug=PlanSlug.PREMIUM, is_active=True)
        assign_plan_features(basic, ["student_management", "classes"])
        assign_plan_features(premium, ["student_management", "classes", "library_management"])

        api_client.force_authenticate(user=super_admin)
        response = api_client.patch(
            f"/api/v1/subscriptions/plans/manage/{premium.id}/",
            {"enabled_feature_keys": ["library_management"]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        premium.refresh_from_db()
        assert premium.features.filter(feature_key="student_management").exists()