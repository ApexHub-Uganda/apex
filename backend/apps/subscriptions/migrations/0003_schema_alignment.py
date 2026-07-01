"""Align schema to subscriptions_feature_flag / subscriptions_plan_feature tables."""
from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


def copy_m2m_assignments(apps, schema_editor):
    PlanFeature = apps.get_model("subscriptions", "PlanFeature")
    connection = schema_editor.connection
    table = "subscriptions_plan_enabled_features"
    cols: set[str] = set()
    with connection.cursor() as cursor:
        if connection.vendor == "sqlite":
            cursor.execute(f"PRAGMA table_info({table})")
            cols = {row[1] for row in cursor.fetchall()}
        else:
            cursor.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = %s
                """,
                [table],
            )
            cols = {row[0] for row in cursor.fetchall()}
    feature_col = "featureflag_id" if "featureflag_id" in cols else "planfeature_id"
    if feature_col not in cols or "plan_id" not in cols:
        return
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT plan_id, {feature_col} FROM {table}")
        rows = cursor.fetchall()
    for plan_id, feature_id in rows:
        PlanFeature.objects.get_or_create(plan_id=plan_id, feature_id=feature_id)


def reseed_catalog(apps, schema_editor):
    from apps.subscriptions.seed_features import seed_feature_catalog, seed_plan_defaults

    seed_feature_catalog()
    seed_plan_defaults()


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0002_enterprise_feature_catalog"),
    ]

    operations = [
        migrations.RenameModel("PlanFeature", "FeatureFlag"),
        migrations.RenameField("FeatureFlag", "slug", "feature_key"),
        migrations.RenameField("FeatureFlag", "name", "feature_name"),
        migrations.RemoveField("FeatureFlag", "gate_slug"),
        migrations.AddField(
            model_name="featureflag",
            name="route_path",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="featureflag",
            name="icon",
            field=models.CharField(blank=True, default="FiGrid", max_length=50),
        ),
        migrations.AddField(
            model_name="featureflag",
            name="show_in_nav",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="featureflag",
            name="show_on_dashboard",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="featureflag",
            name="widget_key",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="featureflag",
            name="dashboard_label",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AlterField(
            model_name="featurecategory",
            name="name",
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterModelTable("FeatureCategory", "subscriptions_feature_category"),
        migrations.AlterModelTable("FeatureFlag", "subscriptions_feature_flag"),
        migrations.AlterModelTable("Plan", "subscriptions_plan"),
        migrations.CreateModel(
            name="PlanFeature",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("feature", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="plan_features", to="subscriptions.featureflag")),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="plan_features", to="subscriptions.plan")),
            ],
            options={
                "db_table": "subscriptions_plan_feature",
                "unique_together": {("plan", "feature")},
            },
        ),
        migrations.RunPython(copy_m2m_assignments, migrations.RunPython.noop),
        migrations.RemoveField("plan", "enabled_features"),
        migrations.AddField(
            model_name="plan",
            name="features",
            field=models.ManyToManyField(
                blank=True, related_name="plans",
                through="subscriptions.PlanFeature", to="subscriptions.featureflag",
            ),
        ),
        migrations.RunPython(reseed_catalog, migrations.RunPython.noop),
    ]