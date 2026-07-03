"""Process trial, billing period, and grace expirations."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.subscriptions.subscription_lifecycle import process_subscription_lifecycle


class Command(BaseCommand):
    help = "Expire trials, billing periods, and grace windows based on calendar dates."

    def handle(self, *args, **options):
        stats = process_subscription_lifecycle()
        self.stdout.write(
            self.style.SUCCESS(
                "Subscription lifecycle processed: "
                f"trial→grace={stats['trial_to_grace']}, "
                f"active→grace={stats['active_to_grace']}, "
                f"grace→expired={stats['grace_to_expired']}",
            ),
        )