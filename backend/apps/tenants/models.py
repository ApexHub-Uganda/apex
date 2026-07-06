"""Tenant (School) models."""
from __future__ import annotations

import uuid
from typing import Any, Optional

from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.core.constants import COLOR_ACCENT, COLOR_PRIMARY, COLOR_SECONDARY, RegistrationType, TenantStatus, UserRole


def tenant_upload_path(instance: Any, filename: str) -> str:
    return f"tenants/{instance.id}/{filename}"


class Tenant(models.Model):
    """School / organization tenant."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    code = models.CharField(max_length=20, unique=True, db_index=True, help_text="Short school code")
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="Kenya")
    timezone = models.CharField(max_length=50, default="Africa/Nairobi")

    # Branding
    logo = models.ImageField(upload_to=tenant_upload_path, blank=True, null=True)
    favicon = models.ImageField(upload_to=tenant_upload_path, blank=True, null=True)
    banner = models.ImageField(upload_to=tenant_upload_path, blank=True, null=True)
    login_bg = models.ImageField(upload_to=tenant_upload_path, blank=True, null=True)
    primary_color = models.CharField(max_length=7, default=COLOR_PRIMARY)
    secondary_color = models.CharField(max_length=7, default=COLOR_SECONDARY)
    accent_color = models.CharField(max_length=7, default=COLOR_ACCENT)
    tagline = models.CharField(max_length=255, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=TenantStatus.CHOICES, default=TenantStatus.PENDING)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    is_suspended = models.BooleanField(default=False, db_index=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspension_reason = models.TextField(blank=True)

    # Registration
    registration_number = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    registration_type = models.CharField(
        max_length=20,
        choices=RegistrationType.CHOICES,
        default=RegistrationType.PENDING,
        db_index=True,
    )
    payment_attempted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["status", "is_suspended"]),
            models.Index(fields=["country", "city"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            base = slugify(self.name)
            slug = base
            counter = 1
            while Tenant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def active_subscription(self) -> Optional[Any]:
        return self.subscriptions.filter(
            status__in=["trial", "active", "grace_period"]
        ).order_by("-created_at").first()

    def has_feature(self, feature_key: str) -> bool:
        from apps.subscriptions.services import tenant_has_feature
        return tenant_has_feature(self, feature_key)

    def verify(self) -> None:
        self.is_verified = True
        self.verified_at = timezone.now()
        self.status = TenantStatus.ACTIVE
        self.save(update_fields=["is_verified", "verified_at", "status", "updated_at"])

    def suspend(self, reason: str = "") -> None:
        self.is_suspended = True
        self.suspended_at = timezone.now()
        self.suspension_reason = reason
        self.status = TenantStatus.SUSPENDED
        self.save(update_fields=[
            "is_suspended", "suspended_at", "suspension_reason", "status", "updated_at"
        ])

    def unsuspend(self) -> None:
        self.is_suspended = False
        self.suspended_at = None
        self.suspension_reason = ""
        self.status = TenantStatus.ACTIVE
        self.save(update_fields=[
            "is_suspended", "suspended_at", "suspension_reason", "status", "updated_at"
        ])

    def get_feature_flags(self) -> dict[str, bool]:
        from apps.subscriptions.services import get_tenant_feature_flags
        return get_tenant_feature_flags(self)

    def get_enabled_features(self) -> list[str]:
        sub = self.active_subscription
        if not sub or not sub.plan:
            return []
        return list(
            sub.plan.features.filter(is_active=True)
            .order_by("category__sort_order", "sort_order")
            .values_list("feature_name", flat=True)
        )

    def get_navigation_menu(self) -> list[dict]:
        from apps.subscriptions.services import get_tenant_navigation
        return get_tenant_navigation(self)

    def get_dashboard_widgets(self) -> list[dict]:
        from apps.subscriptions.services import get_tenant_dashboard_widgets
        return get_tenant_dashboard_widgets(self)


class SchoolRoleModulePermission(models.Model):
    """Per-tenant module read/write permissions configured by school admin."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="role_module_permissions",
        db_index=True,
    )
    role = models.CharField(max_length=30, choices=UserRole.CHOICES, db_index=True)
    module_key = models.CharField(max_length=50, db_index=True)
    can_read = models.BooleanField(default=False)
    can_write = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["role", "module_key"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "role", "module_key"],
                name="uniq_tenant_role_module_permission",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "role"]),
            models.Index(fields=["tenant", "module_key"]),
        ]

    def __str__(self) -> str:
        access = "rw" if self.can_write else ("r" if self.can_read else "—")
        return f"{self.tenant.code}:{self.role}:{self.module_key} ({access})"


class SchoolRoleFeaturePermission(models.Model):
    """Per-tenant sub-module (feature) read/write permissions by role."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="role_feature_permissions",
        db_index=True,
    )
    role = models.CharField(max_length=30, choices=UserRole.CHOICES, db_index=True)
    feature_key = models.CharField(max_length=80, db_index=True)
    can_read = models.BooleanField(default=False)
    can_write = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["role", "feature_key"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "role", "feature_key"],
                name="uniq_tenant_role_feature_permission",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "role"]),
            models.Index(fields=["tenant", "feature_key"]),
        ]

    def __str__(self) -> str:
        access = "rw" if self.can_write else ("r" if self.can_read else "—")
        return f"{self.tenant.code}:{self.role}:{self.feature_key} ({access})"