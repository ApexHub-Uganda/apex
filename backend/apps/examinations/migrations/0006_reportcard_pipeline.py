import uuid
from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("examinations", "0005_exam_assignment_term_optional"),
        ("academics", "0011_phase_a_promotion_reports"),
        ("accounts", "0003_user_must_change_password"),
    ]

    operations = [
        migrations.AddField(model_name="reportcard", name="stream", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="report_cards", to="academics.stream")),
        migrations.AddField(model_name="reportcard", name="academic_year", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="report_cards", to="academics.academicyear")),
        migrations.AddField(model_name="reportcard", name="version", field=models.PositiveIntegerField(default=1)),
        migrations.AddField(model_name="reportcard", name="is_latest", field=models.BooleanField(db_index=True, default=True)),
        migrations.AddField(model_name="reportcard", name="stream_rank", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="reportcard", name="class_size", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="reportcard", name="stream_size", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="reportcard", name="aggregate_points", field=models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
        migrations.AddField(model_name="reportcard", name="division", field=models.CharField(blank=True, max_length=20)),
        migrations.AddField(model_name="reportcard", name="dos_remarks", field=models.TextField(blank=True)),
        migrations.AddField(model_name="reportcard", name="published_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="reportcard", name="published_by", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="published_report_cards", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="reportcard", name="days_present", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="reportcard", name="days_absent", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="reportcard", name="days_late", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="reportcard", name="days_excused", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="reportcard", name="next_term_opens", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="reportcard", name="generation_meta", field=models.JSONField(blank=True, default=dict)),
        migrations.AlterUniqueTogether(name="reportcard", unique_together=set()),
        migrations.CreateModel(
            name="ReportCardSubjectLine",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("subject_name", models.CharField(max_length=120)),
                ("subject_code", models.CharField(blank=True, max_length=30)),
                ("paper_breakdown", models.JSONField(blank=True, default=list)),
                ("ca_score", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("exam_score", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("total_score", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("max_score", models.DecimalField(decimal_places=2, default=100, max_digits=6)),
                ("grade", models.CharField(blank=True, max_length=10)),
                ("grade_point", models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True)),
                ("remarks", models.CharField(blank=True, max_length=120)),
                ("sort_order", models.PositiveSmallIntegerField(default=1)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("report_card", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="subject_lines", to="examinations.reportcard")),
                ("subject", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="report_card_lines", to="academics.subject")),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="tenants.tenant")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["sort_order", "subject_name"]},
        ),
    ]
