# Generated manually for TeachingAssignment model

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("staff", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("academics", "0007_phase2_academic_workflows"),
    ]

    operations = [
        migrations.CreateModel(
            name="TeachingAssignment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("notes", models.CharField(blank=True, max_length=255)),
                (
                    "academic_year",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="teaching_assignments",
                        to="academics.academicyear",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "school_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="teaching_assignments",
                        to="academics.class",
                    ),
                ),
                (
                    "subject",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="teaching_assignments",
                        to="academics.subject",
                    ),
                ),
                (
                    "teacher",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="teaching_assignments",
                        to="staff.teacher",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_set",
                        to="tenants.tenant",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "teaching assignment",
                "ordering": ["school_class__name", "subject__code", "teacher__staff__last_name"],
            },
        ),
        migrations.AddIndex(
            model_name="teachingassignment",
            index=models.Index(fields=["tenant", "teacher", "is_active"], name="academics_t_tenant__a4e2c1_idx"),
        ),
        migrations.AddIndex(
            model_name="teachingassignment",
            index=models.Index(fields=["tenant", "school_class", "is_active"], name="academics_t_tenant__b8f3d2_idx"),
        ),
        migrations.AddIndex(
            model_name="teachingassignment",
            index=models.Index(fields=["tenant", "subject", "is_active"], name="academics_t_tenant__c1a4e3_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="teachingassignment",
            unique_together={("tenant", "teacher", "school_class", "subject")},
        ),
    ]