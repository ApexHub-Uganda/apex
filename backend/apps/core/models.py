"""Core base models and managers."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Optional

from django.conf import settings
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.tenants.models import Tenant


class TenantAwareQuerySet(models.QuerySet):
    """QuerySet that filters by current tenant context."""

    def for_tenant(self, tenant: Optional[Tenant]) -> TenantAwareQuerySet:
        if tenant is None:
            return self
        return self.filter(tenant=tenant)

    def active(self) -> TenantAwareQuerySet:
        return self.filter(is_deleted=False)

    def deleted(self) -> TenantAwareQuerySet:
        return self.filter(is_deleted=True)


class TenantAwareManager(models.Manager):
    """Manager applying tenant and soft-delete filters."""

    def get_queryset(self) -> TenantAwareQuerySet:
        from apps.tenants.context import TenantContext

        qs = TenantAwareQuerySet(self.model, using=self._db).active()
        tenant = TenantContext.get_tenant()
        user = TenantContext.get_user()

        if user and getattr(user, "is_super_admin", False):
            return qs

        if tenant is not None:
            return qs.filter(tenant=tenant)

        return qs

    def all_with_deleted(self) -> TenantAwareQuerySet:
        return TenantAwareQuerySet(self.model, using=self._db)

    def for_tenant(self, tenant: Optional[Tenant]) -> TenantAwareQuerySet:
        return self.all_with_deleted().for_tenant(tenant).active()


class BaseModel(models.Model):
    """Abstract base with UUID pk, tenant, audit fields, soft delete."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
        null=True,
        blank=True,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
    )
    is_deleted = models.BooleanField(default=False, db_index=True)

    objects = TenantAwareManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def soft_delete(self, user: Any = None) -> None:
        self.is_deleted = True
        if user:
            self.updated_by = user
        self.save(update_fields=["is_deleted", "updated_at", "updated_by"])

    def restore(self, user: Any = None) -> None:
        self.is_deleted = False
        if user:
            self.updated_by = user
        self.save(update_fields=["is_deleted", "updated_at", "updated_by"])


class PlatformModel(models.Model):
    """Base for platform-level models without tenant scoping."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class TimestampedModel(models.Model):
    """Simple timestamp mixin for non-tenant models."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True