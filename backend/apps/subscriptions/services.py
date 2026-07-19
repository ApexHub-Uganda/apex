"""Subscription feature resolution with caching."""
from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.db import transaction

from apps.subscriptions.models import FeatureCategory, FeatureFlag, Plan, PlanFeature

TENANT_FLAGS_CACHE = "sub:tenant_flags:{tenant_id}"
TENANT_NAV_CACHE = "sub:tenant_nav:{tenant_id}"
TENANT_MODULES_CACHE = "sub:tenant_modules:{tenant_id}"
TENANT_WIDGETS_CACHE = "sub:tenant_widgets:{tenant_id}"
PLAN_FLAGS_CACHE = "sub:plan_flags:{plan_id}"
CATALOG_CACHE = "sub:feature_catalog"
CACHE_TTL = 60
UNLIMITED_CAPACITY = 0  # 0 = no cap enforced


def invalidate_plan_cache(plan_id: str) -> None:
    cache.delete(PLAN_FLAGS_CACHE.format(plan_id=plan_id))


def invalidate_tenant_cache(tenant_id: str) -> None:
    cache.delete(TENANT_FLAGS_CACHE.format(tenant_id=tenant_id))
    cache.delete(TENANT_NAV_CACHE.format(tenant_id=tenant_id))
    cache.delete(TENANT_MODULES_CACHE.format(tenant_id=tenant_id))
    cache.delete(TENANT_WIDGETS_CACHE.format(tenant_id=tenant_id))
    from apps.tenants.role_permissions import invalidate_role_permissions_cache

    invalidate_role_permissions_cache(tenant_id)


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
        "max_students": UNLIMITED_CAPACITY,
        "max_staff": UNLIMITED_CAPACITY,
        "max_parents": UNLIMITED_CAPACITY,
        "max_branches": UNLIMITED_CAPACITY,
        "limits_enforced": False,
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


def get_tenant_module_menu(tenant) -> list[dict[str, Any]]:
    """Return enabled school-admin modules (15 bundles) with child features."""
    from apps.subscriptions.module_registry import SCHOOL_MODULES

    key = TENANT_MODULES_CACHE.format(tenant_id=tenant.id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    enabled = set(get_enabled_feature_keys(tenant))
    modules: list[dict[str, Any]] = []

    for module in SCHOOL_MODULES:
        module_keys = set(module["feature_keys"])
        if not enabled.intersection(module_keys):
            continue
        children = [
            child for child in module["children"]
            if child["feature_key"] in enabled and child["feature_key"] != "streams"
        ]
        modules.append({
            "key": module["key"],
            "label": module["label"],
            "path": module["path"],
            "icon": module["icon"],
            "sort_order": module["sort_order"],
            "feature_key": module["feature_keys"][0],
            "enabled_count": len(children),
            "total_count": len(module["children"]),
            "children": children,
        })

    cache.set(key, modules, CACHE_TTL)
    return modules


def get_tenant_navigation(tenant) -> list[dict[str, Any]]:
    """Flat sidebar nav derived from enabled module bundles."""
    key = TENANT_NAV_CACHE.format(tenant_id=tenant.id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    items = [
        {
            "key": module["key"],
            "label": module["label"],
            "path": module["path"],
            "icon": module["icon"],
            "feature_key": module["feature_key"],
            "children": module.get("children", []),
            "badge": module.get("enabled_count"),
        }
        for module in get_tenant_module_menu(tenant)
    ]

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
    from apps.subscriptions.plan_tiers import merge_plan_feature_keys
    from apps.subscriptions.seed_features import RETIRED_PLAN_FEATURE_KEYS

    feature_keys = merge_plan_feature_keys(plan.slug, feature_keys)
    # Never attach retired core capabilities as plan SKUs.
    feature_keys = [k for k in feature_keys if k not in RETIRED_PLAN_FEATURE_KEYS]
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
    """Super-admin plan editor catalog — grouped into 15 school modules."""
    from apps.subscriptions.module_registry import SCHOOL_MODULES
    from apps.subscriptions.seed_features import RETIRED_PLAN_FEATURE_KEYS

    cached = cache.get(CATALOG_CACHE)
    if cached is not None:
        return cached

    feature_map = {
        f.feature_key: f
        for f in FeatureFlag.objects.filter(is_active=True)
        .exclude(feature_key__in=RETIRED_PLAN_FEATURE_KEYS)
        .select_related("category")
    }

    categories = []
    for module in SCHOOL_MODULES:
        features = []
        for idx, feature_key in enumerate(module["feature_keys"]):
            if feature_key in RETIRED_PLAN_FEATURE_KEYS:
                continue
            feat = feature_map.get(feature_key)
            if not feat:
                continue
            features.append({
                "id": str(feat.id),
                "feature_key": feat.feature_key,
                "feature_name": feat.feature_name,
                "description": feat.description,
                "nav_key": module["key"],
                "route_path": feat.route_path or module["path"],
                "icon": feat.icon or module["icon"],
                "show_in_nav": True,
                "show_on_dashboard": feat.show_on_dashboard,
                "widget_key": feat.widget_key,
                "sort_order": idx,
            })
        if features:
            categories.append({
                "id": module["key"],
                "slug": module["key"],
                "name": module["label"],
                "description": f"{module['label']} module bundle",
                "sort_order": module["sort_order"],
                "features": features,
            })

    cache.set(CATALOG_CACHE, categories, CACHE_TTL)
    return categories


def _school_admins_for_tenant(tenant):
    from django.contrib.auth import get_user_model

    from apps.core.constants import UserRole

    User = get_user_model()
    return User.objects.filter(
        tenant=tenant,
        role=UserRole.SCHOOL_ADMIN,
        is_active=True,
    )


def _subscription_has_completed_payment(subscription) -> bool:
    from apps.subscriptions.models import PaymentTransaction

    return PaymentTransaction.objects.filter(
        subscription=subscription,
        status="completed",
    ).exists()


def _build_subscription_notification_content(
    subscription,
    *,
    event: str,
    previous_plan_name: str | None = None,
) -> tuple[str, str, str]:
    """Return (title, message, notification_type)."""
    plan_name = subscription.plan.name if subscription.plan else "Unknown"
    status_label = subscription.status.replace("_", " ").title()
    payment_pending = not _subscription_has_completed_payment(subscription)

    if event == "plan_changed":
        title = "Subscription plan updated"
        if previous_plan_name and previous_plan_name != plan_name:
            body = (
                f"Your school's plan has been changed from {previous_plan_name} "
                f"to {plan_name} ({status_label})."
            )
        else:
            body = f"Your school's subscription has been updated to {plan_name} ({status_label})."
        notification_type = "info"
    elif event == "subscription_activated":
        title = "Subscription activated"
        body = f"Your {plan_name} subscription is now active."
        notification_type = "success"
    elif event == "subscription_suspended":
        title = "Subscription suspended"
        body = f"Your {plan_name} subscription has been suspended."
        notification_type = "warning"
    elif event == "subscription_created":
        title = "New subscription assigned"
        body = f"A {plan_name} subscription ({status_label}) has been assigned to your school."
        notification_type = "info"
    elif event == "trial_grace_started":
        title = "Free trial ended"
        body = (
            f"Your {plan_name} trial has ended. You are now in a grace period — "
            f"renew or upgrade before access is removed."
        )
        notification_type = "warning"
    elif event == "grace_period_started":
        title = "Billing period ended"
        body = (
            f"Your {plan_name} billing period has ended. You are in a grace period — "
            f"please renew to keep full access."
        )
        notification_type = "warning"
    elif event == "subscription_expired":
        title = "Subscription expired"
        body = (
            f"Your {plan_name} subscription has expired after the grace period. "
            f"Renew or upgrade to restore access."
        )
        notification_type = "error"
    else:
        title = "Subscription updated"
        body = f"Your {plan_name} subscription status is now {status_label}."
        notification_type = "info"

    if payment_pending and event != "subscription_suspended":
        body += (
            " Payment has not been completed yet — you can settle billing "
            "from your dashboard when ready."
        )

    return title, body, notification_type


def notify_tenant_subscription_update(
    subscription,
    *,
    event: str = "plan_changed",
    previous_plan_name: str | None = None,
) -> int:
    """Notify all active school admins about a subscription or plan change."""
    from apps.communication.services import create_user_notification

    tenant = subscription.tenant
    title, message, notification_type = _build_subscription_notification_content(
        subscription,
        event=event,
        previous_plan_name=previous_plan_name,
    )
    payment_pending = not _subscription_has_completed_payment(subscription)
    metadata = {
        "event": event,
        "subscription_id": str(subscription.id),
        "plan_slug": subscription.plan.slug if subscription.plan else "",
        "plan_name": subscription.plan.name if subscription.plan else "",
        "subscription_status": subscription.status,
        "payment_pending": payment_pending,
    }
    if previous_plan_name:
        metadata["previous_plan"] = previous_plan_name

    notified = 0
    for user in _school_admins_for_tenant(tenant):
        create_user_notification(
            user=user,
            tenant=tenant,
            title=title,
            message=message,
            notification_type=notification_type,
            action_url="/school-admin/notifications",
            metadata=metadata,
        )
        notified += 1
    return notified