import pytest
from django.utils import timezone

from apps.core.constants import PlanSlug, UserRole
from apps.platform.models import PlanAdvertisement
from apps.platform.services.plan_advertisements import (
    build_default_advertisement_payload,
    get_active_plan_advertisements_for_tenant,
    get_upgrade_options,
)


@pytest.mark.django_db
class TestPlanAdvertisements:
    def test_upgrade_options_exclude_same_or_lower_tiers(self):
        assert PlanSlug.BASIC in get_upgrade_options(PlanSlug.FREE_TRIAL)
        assert PlanSlug.PREMIUM_PLUS in get_upgrade_options(PlanSlug.BASIC)
        assert get_upgrade_options(PlanSlug.PREMIUM_PLUS) == []

    def test_default_payload_suggests_next_plan(self):
        payload = build_default_advertisement_payload(PlanSlug.FREE_TRIAL)
        assert payload["target_plan_slug"] == PlanSlug.FREE_TRIAL
        assert payload["suggested_plan_slug"] == PlanSlug.BASIC
        assert payload["highlights"]

    def test_active_ad_shown_for_matching_tenant_plan(self, tenant):
        PlanAdvertisement.objects.create(
            target_plan_slug=tenant.active_subscription.plan.slug,
            suggested_plan_slug=PlanSlug.PREMIUM,
            title="Upgrade to Premium",
            headline="Grow with Premium",
            message="Unlock more modules for your school.",
            highlights=["Library", "Transport"],
            status="active",
            broadcast_at=timezone.now(),
        )

        items = get_active_plan_advertisements_for_tenant(tenant)
        assert len(items) == 1
        assert items[0]["metadata"]["advertisement"] is True
        assert items[0]["metadata"]["suggested_plan_slug"] == PlanSlug.PREMIUM

    def test_super_admin_can_create_ad_via_api(self, api_client, super_admin, plan):
        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            "/api/v1/platform/plan-advertisements/",
            {
                "target_plan_slug": plan.slug,
                "suggested_plan_slug": PlanSlug.PREMIUM,
                "title": "Move to Basic",
                "headline": "Scale your school",
                "message": "Basic unlocks more for your team.",
                "highlights": ["More modules"],
                "cta_label": "See Basic",
                "cta_url": "/school-admin/notifications",
                "status": "draft",
            },
            format="json",
        )
        assert response.status_code == 201
        payload = response.data.get("data", response.data)
        assert payload["target_plan_slug"] == plan.slug