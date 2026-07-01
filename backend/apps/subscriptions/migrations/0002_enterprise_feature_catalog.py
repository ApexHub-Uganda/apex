"""Enterprise feature catalog and extended plan limits."""
from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion
import uuid


def seed_catalog_and_plans(apps, schema_editor):
    """Seeding deferred to migration 0003 after schema alignment."""


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FeatureCategory",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(db_index=True, max_length=50, unique=True)),
                ("description", models.TextField(blank=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name_plural": "Feature categories",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="PlanFeature",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(db_index=True, max_length=80, unique=True)),
                ("description", models.TextField(blank=True)),
                ("nav_key", models.CharField(blank=True, help_text="Sidebar module key", max_length=50)),
                ("gate_slug", models.CharField(blank=True, help_text="Coarse permission slug for API feature gates", max_length=50)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="features", to="subscriptions.featurecategory")),
            ],
            options={
                "ordering": ["category__sort_order", "sort_order", "name"],
            },
        ),
        migrations.AddField(
            model_name="plan",
            name="grace_period_days",
            field=models.PositiveIntegerField(default=7),
        ),
        migrations.AddField(
            model_name="plan",
            name="max_branches",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="plan",
            name="max_parents",
            field=models.PositiveIntegerField(default=500),
        ),
        migrations.AddField(
            model_name="plan",
            name="enabled_features",
            field=models.ManyToManyField(blank=True, related_name="plans", to="subscriptions.planfeature"),
        ),
        migrations.RunPython(seed_catalog_and_plans, migrations.RunPython.noop),
    ]