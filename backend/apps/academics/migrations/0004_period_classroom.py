from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0003_ea_context_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="Period",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("name", models.CharField(max_length=50)),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("sort_order", models.PositiveSmallIntegerField(default=1)),
                ("is_break", models.BooleanField(default=False)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="accounts.user")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)ss", to="tenants.tenant")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="accounts.user")),
            ],
            options={
                "ordering": ["sort_order", "start_time"],
                "unique_together": {("tenant", "name")},
            },
        ),
        migrations.CreateModel(
            name="Classroom",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("name", models.CharField(max_length=100)),
                ("code", models.CharField(max_length=20)),
                ("building", models.CharField(blank=True, max_length=100)),
                ("floor", models.CharField(blank=True, max_length=20)),
                ("capacity", models.PositiveIntegerField(default=40)),
                ("room_type", models.CharField(choices=[("classroom", "Classroom"), ("lab", "Laboratory"), ("hall", "Hall"), ("office", "Office"), ("other", "Other")], default="classroom", max_length=20)),
                ("is_available", models.BooleanField(default=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="accounts.user")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)ss", to="tenants.tenant")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="accounts.user")),
            ],
            options={
                "ordering": ["name"],
                "unique_together": {("tenant", "code")},
            },
        ),
    ]