"""Canonical subscription tier enforcement."""
from __future__ import annotations

import pytest
from django.core.management import call_command
from rest_framework import status

from apps.core.constants import PlanSlug
from apps.subscriptions.canonical_plans import ensure_canonical_plans, prune_orphan_plans
from apps.subscriptions.models import Plan


@pytest.mark.django_db
class TestCanonicalPlans:
    def test_api_blocks_plan_creation(self, api_client, super_admin):
        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            "/api/v1/subscriptions/plans/manage/",
            {
                "name": "Mystery Plan",
                "slug": "mystery-plan",
                "price_monthly": "10.00",
                "price_yearly": "100.00",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data["error"]["code"] == "plan_creation_disabled"
        assert not Plan.objects.filter(slug="mystery-plan").exists()

    def test_ensure_canonical_plans_upserts_only_four_tiers(self, db):
        ensure_canonical_plans(seed_features=False)

        slugs = set(Plan.objects.filter(slug__in=[
            PlanSlug.FREE_TRIAL,
            PlanSlug.BASIC,
            PlanSlug.PREMIUM,
            PlanSlug.PREMIUM_PLUS,
        ]).values_list("slug", flat=True))

        assert slugs == {
            PlanSlug.FREE_TRIAL,
            PlanSlug.BASIC,
            PlanSlug.PREMIUM,
            PlanSlug.PREMIUM_PLUS,
        }

    def test_prune_orphan_plans_removes_test_artifacts(self, db):
        Plan.objects.create(name="Scoping Plan", slug="scoping-plan", is_active=True)
        ensure_canonical_plans(seed_features=False)

        result = prune_orphan_plans(dry_run=False)

        assert any(row["slug"] == "scoping-plan" for row in result["deleted"])
        assert not Plan.objects.filter(slug="scoping-plan").exists()
        assert Plan.objects.filter(slug=PlanSlug.BASIC).exists()

    def test_management_command_prunes_orphans(self, db):
        Plan.objects.create(name="HR RBAC Plan", slug="hr-rbac", is_active=True)
        ensure_canonical_plans(seed_features=False)

        call_command("ensure_canonical_plans", "--prune")

        assert not Plan.objects.filter(slug="hr-rbac").exists()
        assert Plan.objects.count() == 4