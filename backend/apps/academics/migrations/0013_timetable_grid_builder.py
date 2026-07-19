# Timetable class-grid builder: nullable subject, break slots

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0012_phase_bde_ops_pastoral"),
    ]

    operations = [
        migrations.AlterField(
            model_name="timetable",
            name="subject",
            field=models.ForeignKey(
                blank=True,
                help_text="Null for break / free periods.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="timetable_entries",
                to="academics.subject",
            ),
        ),
        migrations.AddField(
            model_name="timetable",
            name="is_break_slot",
            field=models.BooleanField(
                default=False,
                help_text="True when this cell is a break / free period (no subject).",
            ),
        ),
        migrations.AddField(
            model_name="timetable",
            name="slot_label",
            field=models.CharField(
                blank=True,
                help_text="Display label for break or free periods (e.g. Break, Assembly).",
                max_length=80,
            ),
        ),
        migrations.AddIndex(
            model_name="timetable",
            index=models.Index(fields=["tenant", "teacher", "day_of_week"], name="academics_tt_t_day_idx"),
        ),
        migrations.AlterField(
            model_name="period",
            name="name",
            field=models.CharField(help_text="e.g. Period 1, Break, Lunch", max_length=50),
        ),
        migrations.AlterField(
            model_name="period",
            name="start_time",
            field=models.TimeField(help_text="Start time (same for all weekdays)"),
        ),
        migrations.AlterField(
            model_name="period",
            name="end_time",
            field=models.TimeField(help_text="End time (same for all weekdays)"),
        ),
        migrations.AlterField(
            model_name="period",
            name="is_break",
            field=models.BooleanField(
                default=False,
                help_text="Break / assembly / free slot — pre-filled on class grids, no subject required.",
            ),
        ),
    ]
