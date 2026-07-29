"""WebAuthn / passkey credentials for staff identity verification."""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class WebAuthnCredential(models.Model):
    """
    Platform authenticator (fingerprint / face / device PIN) bound to a portal user.

    Used as a second factor at staff GPS check-in so one phone cannot freely
    mark attendance for a colleague without that person's biometric.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="webauthn_credentials",
        db_index=True,
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="webauthn_credentials",
        db_index=True,
    )
    # Base64url-encoded credential id (unique globally for lookups)
    credential_id = models.CharField(max_length=512, unique=True, db_index=True)
    public_key = models.TextField(help_text="Base64url COSE public key")
    sign_count = models.PositiveIntegerField(default=0)
    transports = models.JSONField(default=list, blank=True)
    device_label = models.CharField(max_length=120, blank=True, default="This device")
    aaguid = models.CharField(max_length=64, blank=True, default="")
    backed_by_platform = models.BooleanField(
        default=True,
        help_text="True when registered with a platform authenticator (fingerprint preferred).",
    )
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-last_used_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["tenant", "user"]),
        ]

    def __str__(self) -> str:
        return f"{self.device_label} ({self.user_id})"

    def touch_used(self) -> None:
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at", "updated_at"])


class WebAuthnChallenge(models.Model):
    """Short-lived challenge for registration or authentication ceremonies."""

    PURPOSE_REGISTER = "register"
    PURPOSE_AUTH = "authenticate"
    PURPOSE_CHOICES = [
        (PURPOSE_REGISTER, "Register"),
        (PURPOSE_AUTH, "Authenticate"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="webauthn_challenges",
    )
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, db_index=True)
    challenge = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    consumed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "purpose", "consumed"])]

    @property
    def is_valid(self) -> bool:
        return (not self.consumed) and timezone.now() < self.expires_at
