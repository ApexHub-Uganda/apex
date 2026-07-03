"""Plan upgrade advertisement helpers for super-admin broadcasts."""
from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.communication.services import create_user_notification
from apps.core.constants import PlanSlug, UserRole
from apps.platform.models import PlanAdvertisement
from apps.subscriptions.models import Plan

User = get_user_model()

PLAN_ORDER = [
    PlanSlug.FREE_TRIAL,
    PlanSlug.BASIC,
    PlanSlug.PREMIUM,
    PlanSlug.PREMIUM_PLUS,
]

DEFAULT_UPGRADE = {
    PlanSlug.FREE_TRIAL: PlanSlug.BASIC,
    PlanSlug.BASIC: PlanSlug.PREMIUM,
    PlanSlug.PREMIUM: PlanSlug.PREMIUM_PLUS,
}

PLAN_LABELS = {
    PlanSlug.FREE_TRIAL: "Free Trial",
    PlanSlug.BASIC: "Basic",
    PlanSlug.PREMIUM: "Premium",
    PlanSlug.PREMIUM_PLUS: "Premium Plus",
}

DEFAULT_HIGHLIGHTS = {
    (PlanSlug.FREE_TRIAL, PlanSlug.BASIC): [
        "Expanded academics and finance modules",
        "Advanced reporting and analytics",
        "Higher operational capacity",
    ],
    (PlanSlug.BASIC, PlanSlug.PREMIUM): [
        "Library, hostel, and transport operations",
        "HR management and payroll processing",
        "Deeper analytics across departments",
    ],
    (PlanSlug.PREMIUM, PlanSlug.PREMIUM_PLUS): [
        "Every module unlocked on the platform",
        "Maximum feature coverage for large schools",
        "Priority platform support readiness",
    ],
}


def normalize_plan_slug(slug: str | None) -> str | None:
    if not slug:
        return None
    return str(slug).strip().lower().replace(" ", "_")


def get_upgrade_options(target_plan_slug: str) -> list[str]:
    normalized = normalize_plan_slug(target_plan_slug)
    if not normalized:
        return []
    try:
        idx = PLAN_ORDER.index(normalized)
    except ValueError:
        return []
    return PLAN_ORDER[idx + 1:]


def is_top_tier_plan(slug: str | None) -> bool:
    return normalize_plan_slug(slug) == PlanSlug.PREMIUM_PLUS


def get_plan_label(slug: str) -> str:
    return PLAN_LABELS.get(slug, slug.replace("_", " ").title())


def build_default_advertisement_payload(target_plan_slug: str, suggested_plan_slug: str | None = None) -> dict[str, Any]:
    suggested = suggested_plan_slug or DEFAULT_UPGRADE.get(target_plan_slug)
    if not suggested:
        suggested = get_upgrade_options(target_plan_slug)[0] if get_upgrade_options(target_plan_slug) else target_plan_slug

    target_label = get_plan_label(target_plan_slug)
    suggested_label = get_plan_label(suggested)
    highlights = DEFAULT_HIGHLIGHTS.get(
        (target_plan_slug, suggested),
        [f"Upgrade from {target_label} to {suggested_label}", "More modules and features for your school"],
    )

    return {
        "target_plan_slug": target_plan_slug,
        "suggested_plan_slug": suggested,
        "title": f"Upgrade to {suggested_label}",
        "headline": f"Unlock more with {suggested_label}",
        "message": (
            f"Your school is on the {target_label} plan. "
            f"Move to {suggested_label} to access additional modules, streamline operations, "
            f"and scale with confidence."
        ),
        "highlights": highlights,
        "cta_label": f"View {suggested_label} benefits",
        "cta_url": f"/school-admin/upgrade?plan={suggested}",
        "status": "draft",
    }


def _plan_name_map() -> dict[str, str]:
    return {p.slug: p.name for p in Plan.objects.filter(is_active=True)}


def advertisement_to_feed_item(ad: PlanAdvertisement, *, plan_names: dict[str, str] | None = None) -> dict[str, Any]:
    names = plan_names or _plan_name_map()
    suggested_name = names.get(ad.suggested_plan_slug, get_plan_label(ad.suggested_plan_slug))
    target_name = names.get(ad.target_plan_slug, get_plan_label(ad.target_plan_slug))

    return {
        "id": f"plan-ad-{ad.id}",
        "title": ad.title,
        "message": ad.message,
        "type": "info",
        "is_read": False,
        "priority": "normal",
        "created_at": (ad.broadcast_at or ad.updated_at or timezone.now()).isoformat(),
        "action_url": ad.cta_url or f"/school-admin/upgrade?plan={ad.suggested_plan_slug}",
        "metadata": {
            "synthetic": True,
            "pinned": True,
            "advertisement": True,
            "ad_id": str(ad.id),
            "headline": ad.headline,
            "highlights": ad.highlights or [],
            "cta_label": ad.cta_label,
            "target_plan_slug": ad.target_plan_slug,
            "target_plan_name": target_name,
            "suggested_plan_slug": ad.suggested_plan_slug,
            "suggested_plan_name": suggested_name,
        },
    }


def get_active_plan_advertisements_for_tenant(tenant) -> list[dict[str, Any]]:
    """Return active plan ads for the tenant's current subscription plan."""
    if not tenant:
        return []

    sub = tenant.active_subscription
    if not sub or not sub.plan:
        return []

    now = timezone.now()
    plan_names = _plan_name_map()
    qs = PlanAdvertisement.objects.filter(
        target_plan_slug=sub.plan.slug,
        status="active",
    )
    ads = []
    for ad in qs:
        if ad.starts_at and ad.starts_at > now:
            continue
        if ad.ends_at and ad.ends_at < now:
            continue
        ads.append(advertisement_to_feed_item(ad, plan_names=plan_names))
    return ads


def _school_admins_for_plan(target_plan_slug: str):
    from apps.subscriptions.models import Subscription

    tenant_ids = Subscription.objects.filter(
        plan__slug=target_plan_slug,
        status__in=["active", "trial"],
    ).values_list("tenant_id", flat=True)

    return User.objects.filter(
        tenant_id__in=tenant_ids,
        role=UserRole.SCHOOL_ADMIN,
        is_active=True,
    ).select_related("tenant")


@transaction.atomic
def broadcast_plan_advertisement(ad: PlanAdvertisement, *, actor) -> dict[str, Any]:
    """Activate an advertisement and notify school admins on the target plan."""
    now = timezone.now()

    PlanAdvertisement.objects.filter(
        target_plan_slug=ad.target_plan_slug,
        status="active",
    ).exclude(pk=ad.pk).update(status="paused", updated_at=now)

    ad.status = "active"
    ad.broadcast_at = now
    if not ad.starts_at:
        ad.starts_at = now
    if actor and not ad.created_by_id:
        ad.created_by = actor
    ad.save()

    feed_item = advertisement_to_feed_item(ad)
    recipients = _school_admins_for_plan(ad.target_plan_slug)
    notified = 0

    for user in recipients:
        create_user_notification(
            user=user,
            tenant=user.tenant,
            title=ad.title,
            message=ad.message,
            notification_type="info",
            action_url=ad.cta_url or f"/school-admin/upgrade?plan={ad.suggested_plan_slug}",
            metadata={
                "advertisement_id": str(ad.id),
                "suggested_plan_slug": ad.suggested_plan_slug,
                "target_plan_slug": ad.target_plan_slug,
                "headline": ad.headline,
                "highlights": ad.highlights or [],
                "cta_label": ad.cta_label,
            },
        )
        notified += 1

    ad.broadcast_count = notified
    ad.save(update_fields=["broadcast_count", "updated_at"])

    return {
        "advertisement_id": str(ad.id),
        "status": ad.status,
        "broadcast_at": ad.broadcast_at.isoformat(),
        "schools_notified": notified,
        "feed_preview": feed_item,
    }