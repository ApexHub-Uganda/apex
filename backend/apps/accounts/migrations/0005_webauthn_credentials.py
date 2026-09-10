# Generated manually for WebAuthn staff biometric verification

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_user_role_assignment"),
        ("tenants", "0006_campus_model"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebAuthnCredential",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("credential_id", models.CharField(db_index=True, max_length=512, unique=True)),
                ("public_key", models.TextField(help_text="Base64url COSE public key")),
                ("sign_count", models.PositiveIntegerField(default=0)),
                ("transports", models.JSONField(blank=True, default=list)),
                ("device_label", models.CharField(blank=True, default="This device", max_length=120)),
                ("aaguid", models.CharField(blank=True, default="", max_length=64)),
                (
                    "backed_by_platform",
                    models.BooleanField(
                        default=True,
                        help_text="True when registered with a platform authenticator (fingerprint preferred).",
                    ),
                ),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="webauthn_credentials",
                        to="tenants.tenant",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="webauthn_credentials",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-last_used_at", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="WebAuthnChallenge",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "purpose",
                    models.CharField(
                        choices=[("register", "Register"), ("authenticate", "Authenticate")],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("challenge", models.CharField(db_index=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("consumed", models.BooleanField(default=False)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="webauthn_challenges",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="webauthncredential",
            index=models.Index(fields=["user", "is_active"], name="accounts_we_user_id_3a0c0a_idx"),
        ),
        migrations.AddIndex(
            model_name="webauthncredential",
            index=models.Index(fields=["tenant", "user"], name="accounts_we_tenant__7e2f1b_idx"),
        ),
        migrations.AddIndex(
            model_name="webauthnchallenge",
            index=models.Index(fields=["user", "purpose", "consumed"], name="accounts_we_user_id_9c1d2e_idx"),
        ),
    ]
