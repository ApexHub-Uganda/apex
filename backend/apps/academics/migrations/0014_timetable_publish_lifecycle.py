from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0013_timetable_grid_builder"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="timetableschedule",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("active", "Active"),
                    ("published", "Published"),
                    ("archived", "Archived"),
                ],
                db_index=True,
                default="draft",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="timetableschedule",
            name="published_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="timetableschedule",
            name="published_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="published_timetable_schedules",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
