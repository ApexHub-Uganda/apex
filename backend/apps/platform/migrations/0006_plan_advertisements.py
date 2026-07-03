import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("platform", "0005_notification_receipts"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PlanAdvertisement",
            fields=[
                ("id", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("target_plan_slug", models.CharField(db_index=True, max_length=50)),
                ("suggested_plan_slug", models.CharField(max_length=50)),
                ("title", models.CharField(max_length=255)),
                ("headline", models.CharField(blank=True, max_length=255)),
                ("message", models.TextField()),
                ("highlights", models.JSONField(blank=True, default=list)),
                ("cta_label", models.CharField(default="Explore upgrade", max_length=80)),
                ("cta_url", models.CharField(blank=True, default="/school-admin/notifications", max_length=255)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("paused", "Paused"), ("ended", "Ended")], db_index=True, default="draft", max_length=20)),
                ("starts_at", models.DateTimeField(blank=True, null=True)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("broadcast_at", models.DateTimeField(blank=True, null=True)),
                ("broadcast_count", models.PositiveIntegerField(default=0)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="plan_advertisements_created", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-updated_at"],
                "indexes": [
                    models.Index(fields=["target_plan_slug", "status"], name="platform_pl_target__a8f4b2_idx"),
                    models.Index(fields=["status", "broadcast_at"], name="platform_pl_status__5fd201_idx"),
                ],
            },
        ),
    ]