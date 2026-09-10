# Generated manually for stream-level class teacher assignment

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("staff", "0003_phase1_phase2_hostel_rbac"),
        ("academics", "0015_timetable_display_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="stream",
            name="class_teacher",
            field=models.ForeignKey(
                blank=True,
                help_text="Class teacher for this stream only (optional).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="headed_streams",
                to="staff.teacher",
            ),
        ),
    ]
