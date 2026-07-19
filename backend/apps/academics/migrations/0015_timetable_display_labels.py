from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0014_timetable_publish_lifecycle"),
    ]

    operations = [
        migrations.AddField(
            model_name="timetable",
            name="display_subject",
            field=models.CharField(
                blank=True,
                help_text="Cached subject name at save time for PDF/print.",
                max_length=120,
            ),
        ),
        migrations.AddField(
            model_name="timetable",
            name="display_teacher",
            field=models.CharField(
                blank=True,
                help_text="Cached teacher name at save time for PDF/print.",
                max_length=120,
            ),
        ),
    ]
