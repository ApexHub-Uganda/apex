"""Subscription feature resolution with caching."""
from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.db import transaction

from apps.subscriptions.models import FeatureCategory, FeatureFlag, Plan, PlanFeature

TENANT_FLAGS_CACHE = "sub:tenant_flags:{tenant_id}"
TENANT_NAV_CACHE = "sub:tenant_nav:{tenant_id}"
TENANT_WIDGETS_CACHE = "sub:tenant_widgets:{tenant_id}"
PLAN_FLAGS_CACHE = "sub:plan_flags:{plan_id}"
CATALOG_CACHE = "sub:feature_catalog"
CACHE_TTL = 300


def invalidate_plan_cache(plan_id: str) -> None:
    cache.delete(PLAN_FLAGS_CACHE.format(plan_id=plan_id))


def invalidate_tenant_cache(tenant_id: str) -> None:
    cache.delete(TENANT_FLAGS_CACHE.format(tenant_id=tenant_id))
    cache.delete(TENANT_NAV_CACHE.format(tenant_id=tenant_id))
    cache.delete(TENANT_WIDGETS_CACHE.format(tenant_id=tenant_id))


def invalidate_catalog_cache() -> None:
    cache.delete(CATALOG_CACHE)


def invalidate_all_subscription_caches() -> None:
    cache.delete_pattern("sub:*") if hasattr(cache, "delete_pattern") else None
    invalidate_catalog_cache()


def build_plan_feature_flags(plan: Plan) -> dict[str, bool]:
    """Build denormalized flags from plan-feature assignments."""
    enabled_keys = set(
        PlanFeature.objects.filter(plan=plan, feature__is_active=True)
        .values_list("feature__feature_key", flat=True)
    )
    flags: dict[str, bool] = {}
    for feature in FeatureFlag.objects.filter(is_active=True).only(
        "feature_key", "nav_key",
    ):
        enabled = feature.feature_key in enabled_keys
        flags[feature.feature_key] = enabled
        if enabled and feature.nav_key:
            flags[feature.nav_key] = True
    return flags


def get_plan_feature_flags(plan: Plan) -> dict[str, bool]:
    key = PLAN_FLAGS_CACHE.format(plan_id=plan.id)
    cached = cache.get(key)
    if cached is not None:
        return cached
    flags = plan.feature_flags or build_plan_feature_flags(plan)
    cache.set(key, flags, CACHE_TTL)
    return flags


def get_tenant_feature_flags(tenant) -> dict[str, bool]:
    key = TENANT_FLAGS_CACHE.format(tenant_id=tenant.id)
    cached = cache.get(key)
    if cached is not None:
        return cached
    sub = tenant.active_subscription
    if not sub or not sub.plan:
        cache.set(key, {}, CACHE_TTL)
        return {}
    flags = get_plan_feature_flags(sub.plan)
    cache.set(key, flags, CACHE_TTL)
    return flags


def tenant_has_feature(tenant, feature_key: str) -> bool:
    if not feature_key:
        return True
    return bool(get_tenant_feature_flags(tenant).get(feature_key))


def get_subscription_summary(tenant) -> dict[str, Any] | None:
    """Compact subscription payload for tenant API and dashboards."""
    sub = tenant.active_subscription
    if not sub or not sub.plan:
        return None
    plan = sub.plan
    return {
        "plan_name": plan.name,
        "plan_slug": plan.slug,
        "status": sub.status,
        "billing_cycle": sub.billing_cycle,
        "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "max_students": plan.max_students,
        "max_staff": plan.max_staff,
        "max_parents": plan.max_parents,
        "max_branches": plan.max_branches,
        "feature_count": plan.features.filter(is_active=True).count(),
    }


def get_enabled_feature_keys(tenant) -> list[str]:
    sub = tenant.active_subscription
    if not sub or not sub.plan:
        return []
    return list(
        sub.plan.features.filter(is_active=True)
        .order_by("category__sort_order", "sort_order")
        .values_list("feature_key", flat=True)
    )


def get_tenant_navigation(tenant) -> list[dict[str, Any]]:
    key = TENANT_NAV_CACHE.format(tenant_id=tenant.id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    sub = tenant.active_subscription
    if not sub or not sub.plan:
        cache.set(key, [], CACHE_TTL)
        return []

    enabled_keys = set(
        PlanFeature.objects.filter(plan=sub.plan, feature__is_active=True, feature__show_in_nav=True)
        .values_list("feature__nav_key", flat=True)
    )
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for feature in FeatureFlag.objects.filter(
        is_active=True, show_in_nav=True, nav_key__in=enabled_keys,
    ).order_by("sort_order", "feature_name"):
        if not feature.nav_key or feature.nav_key in seen:
            continue
        if not tenant_has_feature(tenant, feature.feature_key):
            continue
        seen.add(feature.nav_key)
        items.append({
            "key": feature.nav_key,
            "label": feature.feature_name.split(" - ")[0] if " - " in feature.feature_name else _nav_label(feature.nav_key),
            "path": feature.route_path or f"/school-admin/{feature.nav_key}",
            "icon": feature.icon or "FiGrid",
            "feature_key": feature.feature_key,
        })

    cache.set(key, items, CACHE_TTL)
    return items


def get_tenant_dashboard_widgets(tenant) -> list[dict[str, Any]]:
    key = TENANT_WIDGETS_CACHE.format(tenant_id=tenant.id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    sub = tenant.active_subscription
    if not sub or not sub.plan:
        cache.set(key, [], CACHE_TTL)
        return []

    widgets = []
    for feature in FeatureFlag.objects.filter(
        is_active=True, show_on_dashboard=True,
    ).order_by("sort_order"):
        if tenant_has_feature(tenant, feature.feature_key):
            widgets.append({
                "key": feature.widget_key or feature.feature_key,
                "label": feature.dashboard_label or feature.feature_name,
                "icon": feature.icon or "FiGrid",
                "feature_key": feature.feature_key,
            })

    cache.set(key, widgets, CACHE_TTL)
    return widgets


def _nav_label(nav_key: str) -> str:
    return nav_key.replace("_", " ").title()


@transaction.atomic
def assign_plan_features(plan: Plan, feature_keys: list[str]) -> Plan:
    """Replace plan feature assignments atomically."""
    features = list(FeatureFlag.objects.filter(feature_key__in=feature_keys, is_active=True))
    unknown = set(feature_keys) - {f.feature_key for f in features}
    if unknown:
        raise ValueError(f"Unknown or inactive features: {', '.join(sorted(unknown))}")

    PlanFeature.objects.filter(plan=plan).delete()
    PlanFeature.objects.bulk_create([
        PlanFeature(plan=plan, feature=feature) for feature in features
    ])
    plan.feature_flags = build_plan_feature_flags(plan)
    plan.save(update_fields=["feature_flags", "updated_at"])
    invalidate_plan_cache(str(plan.id))

    for sub in plan.subscriptions.select_related("tenant").filter(
        status__in=["trial", "active", "grace_period"],
    ):
        invalidate_tenant_cache(str(sub.tenant_id))

    return plan


def get_feature_catalog() -> list[dict[str, Any]]:
    cached = cache.get(CATALOG_CACHE)
    if cached is not None:
        return cached

    categories = []
    for category in FeatureCategory.objects.filter(is_active=True).prefetch_related("features").order_by("sort_order"):
        features = [
            {
                "id": str(f.id),
                "feature_key": f.feature_key,
                "feature_name": f.feature_name,
                "description": f.description,
                "nav_key": f.nav_key,
                "route_path": f.route_path,
                "icon": f.icon,
                "show_in_nav": f.show_in_nav,
                "show_on_dashboard": f.show_on_dashboard,
                "widget_key": f.widget_key,
                "sort_order": f.sort_order,
            }
            for f in category.features.filter(is_active=True).order_by("sort_order", "feature_name")
        ]
        if features:
            categories.append({
                "id": str(category.id),
                "slug": category.slug,
                "name": category.name,
                "description": category.description,
                "sort_order": category.sort_order,
                "features": features,
            })

    cache.set(CATALOG_CACHE, categories, CACHE_TTL)
    return categories