"""User and authentication models."""
from __future__ import annotations

import uuid
from typing import Any, Optional

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.accounts.managers import UserManager
from apps.core.constants import UserRole


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user with email login and role-based access."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    role = models.CharField(max_length=30, choices=UserRole.CHOICES, default=UserRole.TEACHER, db_index=True)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users",
        db_index=True,
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    # 2FA ready
    is_2fa_enabled = models.BooleanField(default=False)
    totp_secret = models.CharField(max_length=32, blank=True)
    backup_codes = models.JSONField(default=list, blank=True)

    # Password reset
    password_reset_token = models.CharField(max_length=100, blank=True)
    password_reset_expires = models.DateTimeField(null=True, blank=True)
    must_change_password = models.BooleanField(
        default=False,
        help_text="When true, user must set a new password before using the dashboard.",
    )

    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Legacy mirror of profile_picture.image — prefer UserProfilePicture for new uploads.
    avatar_updated_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["tenant", "role"]),
            models.Index(fields=["tenant", "is_active"]),
        ]


    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN

    def verify_email(self) -> None:
        self.is_email_verified = True
        self.email_verified_at = timezone.now()
        self.save(update_fields=["is_email_verified", "email_verified_at", "updated_at"])

    def has_role(self, *roles: str) -> bool:
        """True if the *active* role matches (or any granted dual role)."""
        if self.role in roles:
            return True
        try:
            granted = set(
                self.role_assignments.filter(is_active=True).values_list("role", flat=True)
            )
        except Exception:
            granted = set()
        return bool(granted.intersection(roles))

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.role == UserRole.SUPER_ADMIN:
            self.is_staff = True
            self.tenant = None
        elif self.role in UserRole.STAFF_ROLES:
            self.is_staff = True
        super().save(*args, **kwargs)


class UserRoleAssignment(models.Model):
    """
    Extra portal roles granted to a user (dual-role support).

    `User.role` is the *active* role used for permissions and dashboards.
    Assignments list every role the user may switch into.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="role_assignments",
        db_index=True,
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="user_role_assignments",
        db_index=True,
    )
    role = models.CharField(max_length=30, choices=UserRole.CHOICES, db_index=True)
    is_primary = models.BooleanField(
        default=False,
        help_text="Default role restored at login when multiple roles exist.",
    )
    is_active = models.BooleanField(default=True)
    source = models.CharField(
        max_length=30,
        blank=True,
        default="admin",
        help_text="How this role was granted: admin | staff_onboard | parent_link | system",
    )
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="roles_granted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "role"]
        unique_together = [("user", "tenant", "role")]
        indexes = [
            models.Index(fields=["tenant", "role"]),
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.role}"


class UserProfilePicture(models.Model):
    """Canonical profile picture record with upload metadata."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile_picture",
    )
    image = models.ImageField(upload_to="avatars/")
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "user profile picture"
        verbose_name_plural = "user profile pictures"

    def __str__(self) -> str:
        return f"Profile picture for {self.user.email}"


class UserSession(models.Model):
    """Active user sessions for token tracking."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    refresh_token_jti = models.CharField(max_length=255, unique=True, db_index=True)
    device_name = models.CharField(max_length=255, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-last_activity"]
        indexes = [models.Index(fields=["user", "is_active"])]


class UserDevice(models.Model):
    """Registered devices for push notifications."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")
    device_id = models.CharField(max_length=255, db_index=True)
    device_name = models.CharField(max_length=255, blank=True)
    platform = models.CharField(max_length=50, blank=True)
    push_token = models.TextField(blank=True)
    is_trusted = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "device_id")]
        indexes = [models.Index(fields=["user", "platform"])]


class LoginHistory(models.Model):
    """Login attempt history."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="login_history", null=True, blank=True)
    email = models.EmailField(db_index=True)
    success = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Login histories"
        indexes = [models.Index(fields=["email", "success", "created_at"])]