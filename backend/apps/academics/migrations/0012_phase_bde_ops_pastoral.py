# Phase B–E: homework submissions, discipline workflow, subject combinations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0011_phase_a_promotion_reports"),
        ("students", "0004_uganda_identity"),
        ("staff", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="homework",
            name="kind",
            field=models.CharField(
                choices=[
                    ("homework", "Homework"),
                    ("assignment", "Assignment"),
                    ("project", "Project"),
                ],
                default="homework",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="homework",
            name="max_score",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name="homework",
            name="requires_parent_ack",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="disciplineremark",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "Open"),
                    ("in_progress", "In progress"),
                    ("resolved", "Resolved"),
                    ("closed", "Closed"),
                ],
                db_index=True,
                default="open",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="disciplineremark",
            name="suspension_days",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="disciplineremark",
            name="parent_meeting_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="disciplineremark",
            name="counsellor_referral",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="disciplineremark",
            name="conduct_points",
            field=models.IntegerField(
                default=0,
                help_text="Negative for sanctions, positive for commendations; rolls into report conduct grade.",
            ),
        ),
        migrations.AddField(
            model_name="disciplineremark",
            name="resolution_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="disciplineremark",
            name="remark_type",
            field=models.CharField(
                choices=[
                    ("commendation", "Commendation"),
                    ("warning", "Warning"),
                    ("sanction", "Sanction"),
                    ("suspension", "Suspension"),
                    ("parent_meeting", "Parent meeting"),
                    ("counsellor", "Counsellor referral"),
                ],
                default="warning",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="HomeworkSubmission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("submitted", "Submitted"),
                            ("late", "Late"),
                            ("graded", "Graded"),
                            ("missing", "Missing"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("score", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("teacher_feedback", models.TextField(blank=True)),
                ("parent_acknowledged", models.BooleanField(default=False)),
                ("parent_acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "homework",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="submissions",
                        to="academics.homework",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="homework_submissions",
                        to="students.student",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(app_label)s_%(class)s_set",
                        to="tenants.tenant",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-submitted_at", "student__last_name"],
                "indexes": [
                    models.Index(fields=["tenant", "homework", "status"], name="academics_hwsub_t_h_s_idx"),
                ],
                "unique_together": {("tenant", "homework", "student")},
            },
        ),
        migrations.CreateModel(
            name="SubjectCombination",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("code", models.CharField(max_length=40)),
                ("name", models.CharField(max_length=120)),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("primary", "Primary"),
                            ("o_level", "O-Level"),
                            ("a_level", "A-Level"),
                        ],
                        default="a_level",
                        max_length=20,
                    ),
                ),
                ("subjects", models.JSONField(blank=True, default=list)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(app_label)s_%(class)s_set",
                        to="tenants.tenant",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["level", "code"],
                "unique_together": {("tenant", "code")},
            },
        ),
        migrations.AddIndex(
            model_name="disciplineremark",
            index=models.Index(fields=["tenant", "status"], name="academics_disc_t_status_idx"),
        ),
    ]
