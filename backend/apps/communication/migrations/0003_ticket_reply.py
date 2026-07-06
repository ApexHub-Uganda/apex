from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("communication", "0002_feed_item_dismissal"),
        ("accounts", "0002_user_profile_picture"),
    ]

    operations = [
        migrations.CreateModel(
            name="TicketReply",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("message", models.TextField()),
                ("is_internal", models.BooleanField(default=False)),
                ("author", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ticket_replies", to="accounts.user")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="accounts.user")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)ss", to="tenants.tenant")),
                ("ticket", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="replies", to="communication.supportticket")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="accounts.user")),
            ],
            options={"ordering": ["created_at"]},
        ),
    ]