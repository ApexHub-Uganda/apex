"""Celery tasks for platform maintenance."""
from __future__ import annotations

from celery import shared_task

from apps.platform.services.broadcasts import process_scheduled_broadcasts


@shared_task(name="platform.process_scheduled_broadcasts")
def process_scheduled_broadcasts_task() -> dict:
    return process_scheduled_broadcasts()