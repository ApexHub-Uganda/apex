"""Seed subscription feature catalog from JSON data file."""
from __future__ import annotations

import json
from pathlib import Path

from apps.subscriptions.models import FeatureCategory, FeatureFlag, Plan, PlanFeature
from apps.subscriptions.services import assign_plan_features, invalidate_catalog_cache

DATA_FILE = Path(__file__).resolve().parent / "data" / "feature_catalog.json"


def _load_catalog_data() -> dict:
    with DATA_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


def seed_feature_catalog() -> int:
    """Upsert categories and features from JSON. Returns feature count."""
    data = _load_catalog_data()
    count = 0
    for cat_data in data.get("categories", []):
        category, _ = FeatureCategory.objects.update_or_create(
            slug=cat_data["slug"],
            defaults={
                "name": cat_data["name"],
                "sort_order": cat_data.get("sort_order", 0),
                "description": cat_data.get("description", ""),
                "is_active": True,
            },
        )
        for feat in cat_data.get("features", []):
            FeatureFlag.objects.update_or_create(
                feature_key=feat["feature_key"],
                defaults={
                    "category": category,
                    "feature_name": feat["feature_name"],
                    "description": feat.get("description", ""),
                    "nav_key": feat.get("nav_key", ""),
                    "route_path": feat.get("route_path", ""),
                    "icon": feat.get("icon", "FiGrid"),
                    "show_in_nav": feat.get("show_in_nav", False),
                    "show_on_dashboard": feat.get("show_on_dashboard", False),
                    "widget_key": feat.get("widget_key", ""),
                    "dashboard_label": feat.get("dashboard_label", ""),
                    "sort_order": feat.get("sort_order", 0),
                    "is_active": True,
                },
            )
            count += 1
    invalidate_catalog_cache()
    return count


def seed_plan_defaults() -> None:
    """Assign default features to standard plans from JSON."""
    for plan_slug in _load_catalog_data().get("plan_defaults", {}):
        seed_plan_defaults_for_slug(plan_slug)


def sync_all_plan_feature_flags() -> None:
    for plan in Plan.objects.all():
        plan.sync_feature_flags()
        plan.save(update_fields=["feature_flags", "updated_at"])


# Backward compatibility for migration 0002
def assign_default_plan_features(plan_slug: str) -> None:
    seed_plan_defaults_for_slug(plan_slug)


def seed_plan_defaults_for_slug(plan_slug: str) -> None:
    data = _load_catalog_data()
    defaults = data.get("plan_defaults", {})
    plan = Plan.objects.filter(slug=plan_slug).first()
    if not plan:
        return
    keys = defaults.get(plan_slug)
    if keys == "all":
        keys = list(FeatureFlag.objects.filter(is_active=True).values_list("feature_key", flat=True))
    if keys:
        assign_plan_features(plan, list(keys))