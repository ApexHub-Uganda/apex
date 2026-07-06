from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("communication", "0003_ticket_reply"),
    ]

    operations = [
        migrations.AddField(
            model_name="announcement",
            name="channels",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Delivery channels: email, sms, whatsapp, notification",
            ),
        ),
        migrations.AlterField(
            model_name="announcement",
            name="is_published",
            field=models.BooleanField(default=False),
        ),
    ]