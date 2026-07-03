"""Celery tasks for subscription maintenance."""
from __future__ import annotations

from celery import shared_task

from apps.subscriptions.subscription_lifecycle import process_subscription_lifecycle


@shared_task(name="subscriptions.process_subscription_lifecycle")
def process_subscription_lifecycle_task() -> dict:
    return process_subscription_lifecycle()