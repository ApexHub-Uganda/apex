"""Canonical subscription tiers and helpers to keep the plan catalog fixed."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.core.constants import PlanSlug
from apps.subscriptions.models import Plan, Subscription
from apps.subscriptions.plan_tiers import PLAN_TIER_ORDER, normalize_plan_slug
from apps.tenants.services import ACTIVE_SUBSCRIPTION_STATUSES

CANONICAL_PLAN_SLUGS = frozenset(PLAN_TIER_ORDER)

CANONICAL_PLAN_DEFAULTS: list[dict[str, Any]] = [
    {
        "name": "Free Trial",
        "slug": PlanSlug.FREE_TRIAL,
        "price_monthly": Decimal("0"),
        "price_yearly": Decimal("0"),
        "max_students": 50,
        "max_staff": 10,
        "max_parents": 100,
        "max_branches": 1,
        "max_sms_monthly": 0,
        "max_emails_monthly": 200,
        "trial_days": 14,
        "grace_period_days": 7,
        "sort_order": 0,
    },
    {
        "name": "Basic",
        "slug": PlanSlug.BASIC,
        "price_monthly": Decimal("49.00"),
        "price_yearly": Decimal("490.00"),
        "max_students": 200,
        "max_staff": 30,
        "max_parents": 400,
        "max_branches": 1,
        "max_sms_monthly": 100,
        "max_emails_monthly": 500,
        "trial_days": 14,
        "grace_period_days": 7,
        "sort_order": 1,
    },
    {
        "name": "Premium",
        "slug": PlanSlug.PREMIUM,
        "price_monthly": Decimal("99.00"),
        "price_yearly": Decimal("990.00"),
        "max_students": 500,
        "max_staff": 75,
        "max_parents": 1000,
        "max_branches": 3,
        "max_sms_monthly": 500,
        "max_emails_monthly": 2000,
        "trial_days": 14,
        "grace_period_days": 10,
        "sort_order": 2,
    },
    {
        "name": "Premium Plus",
        "slug": PlanSlug.PREMIUM_PLUS,
        "price_monthly": Decimal("199.00"),
        "price_yearly": Decimal("1990.00"),
        "max_students": 2000,
        "max_staff": 200,
        "max_parents": 5000,
        "max_branches": 10,
        "max_sms_monthly": 2000,
        "max_emails_monthly": 10000,
        "trial_days": 14,
        "grace_period_days": 14,
        "sort_order": 3,
    },
]


class NonCanonicalPlanError(ValueError):
    """Raised when an operation targets a plan outside the fixed tier catalog."""


def is_canonical_plan_slug(slug: str | None) -> bool:
    normalized = normalize_plan_slug(slug)
    return normalized in CANONICAL_PLAN_SLUGS if normalized else False


def assert_canonical_plan_slug(slug: str | None) -> str:
    normalized = normalize_plan_slug(slug)
    if not normalized or normalized not in CANONICAL_PLAN_SLUGS:
        allowed = ", ".join(PLAN_TIER_ORDER)
        raise NonCanonicalPlanError(
            f"Only the platform tier plans are allowed ({allowed}). "
            f"Received slug: {slug!r}.",
        )
    return normalized


@transaction.atomic
def ensure_canonical_plans(*, seed_features: bool = True) -> list[Plan]:
    """Upsert the four fixed platform tiers without touching non-canonical rows."""
    from apps.subscriptions.seed_features import seed_feature_catalog, seed_plan_defaults

    if seed_features:
        seed_feature_catalog()

    plans: list[Plan] = []
    for data in CANONICAL_PLAN_DEFAULTS:
        plan, _ = Plan.objects.update_or_create(
            slug=data["slug"],
            defaults={
                **data,
                "description": f"{data['name']} plan for schools",
                "is_active": True,
                "is_public": True,
            },
        )
        plans.append(plan)

    if seed_features:
        seed_plan_defaults()

    return plans


def get_orphan_plans() -> list[Plan]:
    return list(
        Plan.objects.exclude(slug__in=CANONICAL_PLAN_SLUGS).order_by("name", "slug"),
    )


def prune_orphan_plans(
    *,
    dry_run: bool = False,
    reassign_orphans_to: str | None = None,
) -> dict[str, Any]:
    """Remove plans outside the fixed tier catalog.

    Orphans with subscriptions are skipped unless ``reassign_orphans_to`` is a
    canonical plan slug; in that case subscriptions are moved first.
    """
    from apps.subscriptions.plan_deletion import delete_plan_safely

    replacement: Plan | None = None
    if reassign_orphans_to:
        replacement_slug = assert_canonical_plan_slug(reassign_orphans_to)
        replacement = Plan.objects.filter(slug=replacement_slug, is_active=True).first()
        if replacement is None:
            raise NonCanonicalPlanError(
                f'Canonical replacement plan "{replacement_slug}" was not found.',
            )

    orphans = get_orphan_plans()
    deleted: list[dict[str, str]] = []
    skipped: list[dict[str, Any]] = []
    reassigned: list[dict[str, Any]] = []

    for plan in orphans:
        subscription_count = plan.subscriptions.count()
        active_count = plan.subscriptions.filter(
            status__in=ACTIVE_SUBSCRIPTION_STATUSES,
        ).count()

        if subscription_count:
            if replacement is None:
                skipped.append({
                    "id": str(plan.id),
                    "name": plan.name,
                    "slug": plan.slug,
                    "subscription_count": subscription_count,
                    "active_subscription_count": active_count,
                })
                continue

            reassigned.append({
                "id": str(plan.id),
                "name": plan.name,
                "slug": plan.slug,
                "subscription_count": subscription_count,
                "reassigned_to": replacement.slug,
            })
            if dry_run:
                continue

            delete_plan_safely(plan, reassign_to=replacement)
            deleted.append({
                "id": str(plan.id),
                "name": plan.name,
                "slug": plan.slug,
                "subscriptions_reassigned": subscription_count,
            })
            continue

        deleted.append({
            "id": str(plan.id),
            "name": plan.name,
            "slug": plan.slug,
        })
        if not dry_run:
            plan.delete()

    return {
        "deleted": deleted,
        "skipped": skipped,
        "reassigned": reassigned,
        "dry_run": dry_run,
    }