"""Plan tier ordering, feature inheritance, and comparison helpers."""
from __future__ import annotations

from typing import Any

from apps.core.constants import PlanSlug
from apps.subscriptions.models import FeatureFlag, Plan

PLAN_TIER_ORDER = [
    PlanSlug.FREE_TRIAL,
    PlanSlug.BASIC,
    PlanSlug.PREMIUM,
    PlanSlug.PREMIUM_PLUS,
]

PLAN_TIER_LABELS = {
    PlanSlug.FREE_TRIAL: "Free Trial",
    PlanSlug.BASIC: "Basic",
    PlanSlug.PREMIUM: "Premium",
    PlanSlug.PREMIUM_PLUS: "Premium Plus",
}


class PlanInheritanceError(ValueError):
    """Raised when a plan is missing mandatory lower-tier features."""


def normalize_plan_slug(slug: str | None) -> str | None:
    if not slug:
        return None
    return str(slug).strip().lower().replace(" ", "_")


def get_parent_tier_slug(plan_slug: str | None) -> str | None:
    normalized = normalize_plan_slug(plan_slug)
    if not normalized or normalized not in PLAN_TIER_ORDER:
        return None
    idx = PLAN_TIER_ORDER.index(normalized)
    if idx == 0:
        return None
    return PLAN_TIER_ORDER[idx - 1]


def get_lower_tier_slugs(plan_slug: str | None) -> list[str]:
    normalized = normalize_plan_slug(plan_slug)
    if not normalized or normalized not in PLAN_TIER_ORDER:
        return []
    idx = PLAN_TIER_ORDER.index(normalized)
    return PLAN_TIER_ORDER[:idx]


def get_plan_tier_label(plan_slug: str | None) -> str:
    normalized = normalize_plan_slug(plan_slug)
    if not normalized:
        return "Plan"
    return PLAN_TIER_LABELS.get(normalized, normalized.replace("_", " ").title())


def get_plan_feature_keys(plan: Plan | None) -> set[str]:
    if not plan:
        return set()
    return set(
        plan.features.filter(is_active=True).values_list("feature_key", flat=True),
    )


def get_inherited_feature_keys(plan_slug: str | None) -> set[str]:
    """Union of all feature keys assigned to lower-tier plans."""
    inherited: set[str] = set()
    for lower_slug in get_lower_tier_slugs(plan_slug):
        lower_plan = Plan.objects.filter(slug=lower_slug, is_active=True).first()
        inherited.update(get_plan_feature_keys(lower_plan))
    return inherited


def merge_plan_feature_keys(plan_slug: str | None, feature_keys: list[str]) -> list[str]:
    """Ensure all inherited lower-tier features are included."""
    merged = set(feature_keys or [])
    merged.update(get_inherited_feature_keys(plan_slug))
    return sorted(merged)


def validate_plan_feature_inheritance(plan_slug: str | None, feature_keys: list[str]) -> None:
    """Raise if explicit selection omits mandatory inherited features."""
    missing = get_inherited_feature_keys(plan_slug) - set(feature_keys or [])
    if missing:
        parent = get_parent_tier_slug(plan_slug)
        parent_label = get_plan_tier_label(parent)
        raise PlanInheritanceError(
            f"All {parent_label} plan features are required on "
            f"{get_plan_tier_label(plan_slug)}. Missing: {', '.join(sorted(missing))}",
        )


def _serialize_feature_rows(keys: set[str]) -> list[dict[str, str]]:
    if not keys:
        return []
    features = FeatureFlag.objects.filter(
        feature_key__in=keys,
        is_active=True,
    ).select_related("category").order_by("category__sort_order", "sort_order")
    return [
        {
            "feature_key": feature.feature_key,
            "name": feature.feature_name,
            "description": feature.description or "",
            "category": feature.category.name if feature.category else "General",
        }
        for feature in features
    ]


def get_plan_feature_breakdown(plan: Plan) -> dict[str, Any]:
    """Split a plan's features into inherited vs exclusive buckets."""
    all_keys = get_plan_feature_keys(plan)
    parent_slug = get_parent_tier_slug(plan.slug)
    inherited_keys = get_inherited_feature_keys(plan.slug) & all_keys
    exclusive_keys = all_keys - inherited_keys

    inherited_rows = _serialize_feature_rows(inherited_keys)
    exclusive_rows = _serialize_feature_rows(exclusive_keys)

    exclusive_by_category: dict[str, list[dict[str, str]]] = {}
    for row in exclusive_rows:
        exclusive_by_category.setdefault(row["category"], []).append(row)

    parent_label = get_plan_tier_label(parent_slug) if parent_slug else None
    summary = None
    if parent_slug and parent_label:
        summary = f"Everything in {parent_label}, plus {len(exclusive_keys)} additional feature"
        if len(exclusive_keys) != 1:
            summary += "s"

    return {
        "inherits_from_slug": parent_slug,
        "inherits_from_label": parent_label,
        "inherited_feature_count": len(inherited_keys),
        "exclusive_feature_count": len(exclusive_keys),
        "inherited_summary": summary,
        "inherited_features": inherited_rows,
        "exclusive_features": exclusive_rows,
        "exclusive_feature_categories": [
            {"name": name, "features": items}
            for name, items in exclusive_by_category.items()
        ],
    }