import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("examinations", "0003_phase2_academic_workflows"),
        ("academics", "0009_classprefect"),
    ]

    operations = [
        migrations.CreateModel(
            name="TimetableSchedule",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("name", models.CharField(max_length=255)),
                ("schedule_type", models.CharField(choices=[("lesson", "Lesson timetable"), ("exam", "Exam timetable")], db_index=True, default="lesson", max_length=20)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("archived", "Archived")], db_index=True, default="draft", max_length=20)),
                ("is_locked", models.BooleanField(default=False, help_text="When true, only school admins may edit or delete entries for this schedule.")),
                ("generation_seed", models.PositiveIntegerField(blank=True, null=True)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("stats", models.JSONField(blank=True, default=dict)),
                ("applied_at", models.DateTimeField(blank=True, null=True)),
                ("academic_year", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="timetable_schedules", to="academics.academicyear")),
                ("applied_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="applied_timetable_schedules", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("examination_session", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="timetable_schedules", to="examinations.examinationsession")),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="tenants.tenant")),
                ("term", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="timetable_schedules", to="academics.term")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="TimetableGenerationDraft",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("schedule_type", models.CharField(choices=[("lesson", "Lesson timetable"), ("exam", "Exam timetable")], max_length=20)),
                ("name", models.CharField(blank=True, max_length=255)),
                ("seed", models.PositiveIntegerField(default=0)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("slots", models.JSONField(blank=True, default=list)),
                ("stats", models.JSONField(blank=True, default=dict)),
                ("warnings", models.JSONField(blank=True, default=list)),
                ("expires_at", models.DateTimeField()),
                ("academic_year", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="timetable_drafts", to="academics.academicyear")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("examination_session", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="timetable_drafts", to="examinations.examinationsession")),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="tenants.tenant")),
                ("term", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="timetable_drafts", to="academics.term")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="timetable",
            name="exam_date",
            field=models.DateField(blank=True, help_text="Used for exam timetable slots", null=True),
        ),
        migrations.AddField(
            model_name="timetable",
            name="examination_session",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="timetable_entries", to="examinations.examinationsession"),
        ),
        migrations.AddField(
            model_name="timetable",
            name="period",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="timetable_entries", to="academics.period"),
        ),
        migrations.AddField(
            model_name="timetable",
            name="schedule",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="entries", to="academics.timetableschedule"),
        ),
        migrations.AddField(
            model_name="timetable",
            name="schedule_type",
            field=models.CharField(choices=[("lesson", "Lesson timetable"), ("exam", "Exam timetable")], db_index=True, default="lesson", max_length=20),
        ),
        migrations.AddField(
            model_name="timetable",
            name="stream",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="timetables", to="academics.stream"),
        ),
        migrations.AddField(
            model_name="timetable",
            name="term",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="timetable_entries", to="academics.term"),
        ),
        migrations.AlterField(
            model_name="timetable",
            name="day_of_week",
            field=models.PositiveSmallIntegerField(blank=True, choices=[(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday"), (5, "Saturday"), (6, "Sunday")], null=True),
        ),
        migrations.AddIndex(
            model_name="timetableschedule",
            index=models.Index(fields=["tenant", "schedule_type", "status"], name="academics_t_tenant__sched_idx"),
        ),
        migrations.AddIndex(
            model_name="timetableschedule",
            index=models.Index(fields=["tenant", "term", "status"], name="academics_t_tenant__term_idx"),
        ),
        migrations.AddIndex(
            model_name="timetablegenerationdraft",
            index=models.Index(fields=["tenant", "created_by", "schedule_type"], name="academics_t_tenant__draft_idx"),
        ),
        migrations.AddIndex(
            model_name="timetable",
            index=models.Index(fields=["tenant", "schedule", "schedule_type"], name="academics_t_tenant__sch2_idx"),
        ),
        migrations.AddIndex(
            model_name="timetable",
            index=models.Index(fields=["tenant", "exam_date"], name="academics_t_tenant__exam_idx"),
        ),
    ]
