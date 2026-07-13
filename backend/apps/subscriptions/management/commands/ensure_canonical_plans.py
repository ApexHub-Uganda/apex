"""Ensure only the four fixed platform subscription tiers exist."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.subscriptions.canonical_plans import ensure_canonical_plans, prune_orphan_plans


class Command(BaseCommand):
    help = (
        "Upsert the four platform subscription tiers and optionally remove orphan plans "
        "left behind by automated tests or manual experiments."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--prune",
            action="store_true",
            help="Delete non-canonical plans that have no subscriptions.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="With --prune, report orphan plans without deleting them.",
        )
        parser.add_argument(
            "--skip-features",
            action="store_true",
            help="Only upsert plan rows; do not refresh the feature catalog defaults.",
        )
        parser.add_argument(
            "--reassign-orphans-to",
            default="",
            help=(
                "When pruning, move subscriptions on orphan plans to this canonical slug "
                "(free_trial, basic, premium, premium_plus) before deleting them."
            ),
        )

    def handle(self, *args, **options) -> None:
        plans = ensure_canonical_plans(seed_features=not options["skip_features"])
        self.stdout.write(self.style.SUCCESS(f"Ensured {len(plans)} canonical plan(s)."))
        for plan in plans:
            self.stdout.write(f"  - {plan.name} ({plan.slug})")

        if not options["prune"]:
            return

        reassign_slug = (options["reassign_orphans_to"] or "").strip() or None
        result = prune_orphan_plans(
            dry_run=options["dry_run"],
            reassign_orphans_to=reassign_slug,
        )
        deleted = result["deleted"]
        skipped = result["skipped"]
        reassigned = result["reassigned"]

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run: no orphan plans were deleted."))

        if deleted:
            label = "Would delete" if options["dry_run"] else "Deleted"
            self.stdout.write(self.style.SUCCESS(f"{label} {len(deleted)} orphan plan(s):"))
            for row in deleted:
                self.stdout.write(f"  - {row['name']} ({row['slug']})")
        else:
            self.stdout.write("No orphan plans without subscriptions found.")

        if reassigned:
            label = "Would reassign" if options["dry_run"] else "Reassigned"
            self.stdout.write(self.style.SUCCESS(
                f"{label} subscriptions on {len(reassigned)} orphan plan(s) to "
                f"{reassign_slug}:",
            ))
            for row in reassigned:
                self.stdout.write(
                    f"  - {row['name']} ({row['slug']}): "
                    f"{row['subscription_count']} subscription(s)",
                )

        if skipped:
            self.stdout.write(self.style.WARNING(
                f"Skipped {len(skipped)} orphan plan(s) still tied to subscriptions:",
            ))
            for row in skipped:
                self.stdout.write(
                    f"  - {row['name']} ({row['slug']}): "
                    f"{row['subscription_count']} subscription(s)",
                )
            self.stdout.write(
                "  Re-run with --reassign-orphans-to=basic (or another canonical slug) "
                "to migrate those schools before deleting the orphan plans.",
            )