# Generated manually for multi-campus support

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0005_phase1_phase2_finance_rbac"),
    ]

    operations = [
        migrations.CreateModel(
            name="Campus",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("code", models.CharField(help_text="Short campus code, unique per school", max_length=30)),
                ("address", models.TextField(blank=True)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("phone", models.CharField(blank=True, max_length=20)),
                ("email", models.EmailField(blank=True, max_length=254)),
                (
                    "is_main",
                    models.BooleanField(
                        default=False,
                        help_text="Primary / headquarters campus for the school.",
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="campuses",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ["-is_main", "name"],
            },
        ),
        migrations.AddIndex(
            model_name="campus",
            index=models.Index(fields=["tenant", "is_active"], name="tenants_cam_tenant__0d0f0b_idx"),
        ),
        migrations.AddIndex(
            model_name="campus",
            index=models.Index(fields=["tenant", "is_main"], name="tenants_cam_tenant__9a1f2c_idx"),
        ),
        migrations.AddConstraint(
            model_name="campus",
            constraint=models.UniqueConstraint(fields=("tenant", "code"), name="uniq_tenant_campus_code"),
        ),
    ]
