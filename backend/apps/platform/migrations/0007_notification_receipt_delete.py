from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("platform", "0006_plan_advertisements"),
    ]

    operations = [
        migrations.AddField(
            model_name="platformnotificationreceipt",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="platformnotificationreceipt",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddIndex(
            model_name="platformnotificationreceipt",
            index=models.Index(fields=["user", "is_deleted"], name="platform_pn_user_id_d4a8c1_idx"),
        ),
    ]