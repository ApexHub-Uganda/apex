"""Sync feature categories to 15 school modules and refresh plan caches."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.subscriptions.models import FeatureCategory, FeatureFlag, Plan
from apps.subscriptions.module_registry import SCHOOL_MODULES
from apps.subscriptions.services import (
    assign_plan_features,
    build_plan_feature_flags,
    invalidate_all_subscription_caches,
    invalidate_tenant_cache,
)
from apps.subscriptions.seed_features import seed_feature_catalog
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Align feature catalog with 15 school modules and refresh tenant caches."

    def handle(self, *args, **options):
        seed_feature_catalog()
        self.stdout.write("Seeded base feature catalog.")

        for module in SCHOOL_MODULES:
            category, _ = FeatureCategory.objects.update_or_create(
                slug=module["key"],
                defaults={
                    "name": module["label"],
                    "description": f"{module['label']} module bundle",
                    "sort_order": module["sort_order"],
                    "is_active": True,
                },
            )
            for sort_order, feature_key in enumerate(module["feature_keys"]):
                FeatureFlag.objects.filter(feature_key=feature_key).update(
                    category=category,
                    sort_order=sort_order,
                    nav_key=module["key"],
                    route_path=module["path"],
                    show_in_nav=True,
                )

        # Deactivate legacy standalone categories merged into modules
        legacy_slugs = {"payroll", "timetable", "platform"}
        FeatureCategory.objects.filter(slug__in=legacy_slugs).update(is_active=False)

        for plan in Plan.objects.all():
            keys = list(plan.features.filter(is_active=True).values_list("feature_key", flat=True))
            if keys:
                plan.feature_flags = build_plan_feature_flags(plan)
                plan.save(update_fields=["feature_flags", "updated_at"])

        invalidate_all_subscription_caches()
        for tenant in Tenant.objects.all():
            invalidate_tenant_cache(str(tenant.id))

        self.stdout.write(self.style.SUCCESS(
            f"Synced {len(SCHOOL_MODULES)} modules. Tenant caches cleared.",
        ))