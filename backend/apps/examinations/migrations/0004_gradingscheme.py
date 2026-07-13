# Generated manually for GradingScheme models

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_legacy_scales(apps, schema_editor):
    GradingScale = apps.get_model("examinations", "GradingScale")
    GradingScheme = apps.get_model("examinations", "GradingScheme")
    GradingSchemeBand = apps.get_model("examinations", "GradingSchemeBand")

    tenant_ids = (
        GradingScale.objects.filter(is_deleted=False)
        .values_list("tenant_id", flat=True)
        .distinct()
    )
    for tenant_id in tenant_ids:
        if tenant_id is None:
            continue
        scales = GradingScale.objects.filter(tenant_id=tenant_id, is_deleted=False).order_by("-min_score")
        if not scales.exists():
            continue
        names = scales.values_list("name", flat=True).distinct()
        scheme_name = names[0] if len(names) == 1 else "Legacy Grading"
        scheme, _ = GradingScheme.objects.get_or_create(
            tenant_id=tenant_id,
            name=scheme_name,
            defaults={"description": "Migrated from legacy grading scales.", "is_default": True},
        )
        for scale in scales:
            GradingSchemeBand.objects.get_or_create(
                tenant_id=tenant_id,
                scheme=scheme,
                grade=scale.grade,
                min_score=scale.min_score,
                defaults={
                    "max_score": scale.max_score,
                    "grade_point": scale.grade_point,
                    "remarks": scale.remarks,
                    "id": uuid.uuid4(),
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ("examinations", "0003_phase2_academic_workflows"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="GradingScheme",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True)),
                ("is_default", models.BooleanField(default=False)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="tenants.tenant")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "grading scheme",
                "ordering": ["name"],
                "unique_together": {("tenant", "name")},
            },
        ),
        migrations.CreateModel(
            name="GradingSchemeBand",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("min_score", models.DecimalField(decimal_places=2, max_digits=5)),
                ("max_score", models.DecimalField(decimal_places=2, max_digits=5)),
                ("grade", models.CharField(max_length=5)),
                ("grade_point", models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ("remarks", models.CharField(blank=True, max_length=100)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("scheme", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bands", to="examinations.gradingscheme")),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="tenants.tenant")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "grading scheme band",
                "ordering": ["-min_score"],
            },
        ),
        migrations.RunPython(migrate_legacy_scales, migrations.RunPython.noop),
    ]