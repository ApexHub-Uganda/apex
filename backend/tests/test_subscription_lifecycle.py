"""Subscription trial, period, and grace expiry tests."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.core.constants import SubscriptionStatus
from apps.subscriptions.models import Subscription
from apps.subscriptions.subscription_lifecycle import process_subscription_lifecycle


@pytest.mark.django_db
class TestSubscriptionLifecycle:
    def test_trial_moves_to_grace_then_expires(self, tenant, plan):
        sub = tenant.active_subscription
        sub.status = SubscriptionStatus.TRIAL
        sub.trial_ends_at = timezone.now() - timedelta(days=1)
        sub.grace_period_ends_at = timezone.now() + timedelta(days=3)
        sub.save()

        stats = process_subscription_lifecycle()
        sub.refresh_from_db()
        assert stats["trial_to_grace"] == 1
        assert sub.status == SubscriptionStatus.GRACE_PERIOD
        assert sub.in_grace_period is True

        sub.grace_period_ends_at = timezone.now() - timedelta(minutes=1)
        sub.save(update_fields=["grace_period_ends_at", "updated_at"])
        stats = process_subscription_lifecycle()
        sub.refresh_from_db()
        assert stats["grace_to_expired"] == 1
        assert sub.status == SubscriptionStatus.EXPIRED
        assert tenant.active_subscription is None

    def test_active_moves_to_grace_on_period_end(self, tenant, plan):
        sub = tenant.active_subscription
        sub.activate(period_days=30)
        sub.current_period_end = timezone.now() - timedelta(hours=1)
        sub.grace_period_ends_at = timezone.now() + timedelta(days=5)
        sub.save()

        stats = process_subscription_lifecycle()
        sub.refresh_from_db()
        assert stats["active_to_grace"] == 1
        assert sub.status == SubscriptionStatus.GRACE_PERIOD
        assert sub.is_expired is True
        assert sub.in_grace_period is True

    def test_active_subscription_not_expired_before_period_end(self, tenant, plan):
        sub = tenant.active_subscription
        sub.activate(period_days=30)
        assert sub.is_expired is False
        assert sub.in_grace_period is False