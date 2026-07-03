"""Calendar-based subscription trial, billing period, and grace expiry."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.core.constants import SubscriptionStatus
from apps.subscriptions.models import Subscription


def _grace_days(subscription: Subscription) -> int:
    if subscription.plan and subscription.plan.grace_period_days:
        return int(subscription.plan.grace_period_days)
    return 7


@transaction.atomic
def enter_grace_period(subscription: Subscription, *, now=None) -> Subscription:
    """Move a subscription into grace after trial or billing period ends."""
    now = now or timezone.now()
    subscription.status = SubscriptionStatus.GRACE_PERIOD
    grace_end = now + timedelta(days=_grace_days(subscription))
    if not subscription.grace_period_ends_at or subscription.grace_period_ends_at < now:
        subscription.grace_period_ends_at = grace_end
    subscription.save(update_fields=["status", "grace_period_ends_at", "updated_at"])
    return subscription


@transaction.atomic
def mark_subscription_expired(subscription: Subscription) -> Subscription:
    subscription.status = SubscriptionStatus.EXPIRED
    subscription.save(update_fields=["status", "updated_at"])
    return subscription


def process_subscription_lifecycle(*, now=None) -> dict[str, Any]:
    """
    Advance subscriptions based on calendar dates:
    - trial -> grace when trial_ends_at passes
    - active -> grace when current_period_end passes
    - grace -> expired when grace_period_ends_at passes
    """
    from apps.subscriptions.services import invalidate_tenant_cache, notify_tenant_subscription_update

    now = now or timezone.now()
    stats = {
        "trial_to_grace": 0,
        "active_to_grace": 0,
        "grace_to_expired": 0,
        "processed_at": now.isoformat(),
    }

    trial_qs = Subscription.objects.filter(
        status=SubscriptionStatus.TRIAL,
        trial_ends_at__isnull=False,
        trial_ends_at__lte=now,
    ).select_related("tenant", "plan")

    for subscription in trial_qs:
        enter_grace_period(subscription, now=now)
        notify_tenant_subscription_update(subscription, event="trial_grace_started")
        invalidate_tenant_cache(str(subscription.tenant_id))
        stats["trial_to_grace"] += 1

    active_qs = Subscription.objects.filter(
        status=SubscriptionStatus.ACTIVE,
        current_period_end__isnull=False,
        current_period_end__lte=now,
    ).select_related("tenant", "plan")

    for subscription in active_qs:
        enter_grace_period(subscription, now=now)
        notify_tenant_subscription_update(subscription, event="grace_period_started")
        invalidate_tenant_cache(str(subscription.tenant_id))
        stats["active_to_grace"] += 1

    grace_qs = Subscription.objects.filter(
        status=SubscriptionStatus.GRACE_PERIOD,
        grace_period_ends_at__isnull=False,
        grace_period_ends_at__lte=now,
    ).select_related("tenant", "plan")

    for subscription in grace_qs:
        mark_subscription_expired(subscription)
        notify_tenant_subscription_update(subscription, event="subscription_expired")
        invalidate_tenant_cache(str(subscription.tenant_id))
        stats["grace_to_expired"] += 1

    return stats