"""Remove test or junk schools that leaked into the operational database."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.tenants.test_artifacts import get_probable_test_schools, prune_test_schools


class Command(BaseCommand):
    help = (
        "Delete schools created by automated tests or junk registration attempts. "
        "Seeded demo schools are preserved."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List matching schools without deleting them.",
        )

    def handle(self, *args, **options) -> None:
        dry_run = options["dry_run"]
        candidates = get_probable_test_schools()

        if not candidates:
            self.stdout.write(self.style.SUCCESS("No test or junk schools found."))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"Dry run: would delete {len(candidates)} school(s):",
            ))
            for tenant in candidates:
                self.stdout.write(f"  - {tenant.name} ({tenant.code}) <{tenant.email}>")
            return

        result = prune_test_schools(dry_run=False)
        deleted = result["deleted"]
        self.stdout.write(self.style.SUCCESS(f"Deleted {len(deleted)} test/junk school(s):"))
        for row in deleted:
            self.stdout.write(f"  - {row['name']} ({row['code']}) <{row['email']}>")