"""Send platform broadcasts that are due for delivery."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.platform.services.broadcasts import process_scheduled_broadcasts


class Command(BaseCommand):
    help = "Send scheduled platform broadcasts whose start time has passed."

    def handle(self, *args, **options):
        stats = process_scheduled_broadcasts()
        self.stdout.write(
            self.style.SUCCESS(
                f"Scheduled broadcasts processed: {stats['processed']}",
            ),
        )