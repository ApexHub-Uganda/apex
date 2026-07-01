"""View and serializer mixins."""
from __future__ import annotations

from typing import Any, Optional

from django.db import models
from rest_framework import serializers

from apps.tenants.context import TenantContext


class TenantFilterMixin:
    """Filter queryset by tenant from request context."""

    def get_queryset(self) -> models.QuerySet:
        qs = super().get_queryset()  # type: ignore[misc]
        user = self.request.user  # type: ignore[attr-defined]

        if user.is_authenticated and user.is_super_admin:
            tenant_id = self.request.query_params.get("tenant_id")  # type: ignore[attr-defined]
            if tenant_id:
                return qs.filter(tenant_id=tenant_id)
            return qs

        if hasattr(qs.model, "tenant"):
            return qs.filter(tenant=user.tenant)

        return qs


class AuditFieldsMixin:
    """Auto-set created_by/updated_by on save."""

    def perform_create(self, serializer: serializers.BaseSerializer) -> None:
        extra: dict[str, Any] = {"created_by": self.request.user, "updated_by": self.request.user}
        if hasattr(serializer.Meta.model, "tenant"):
            tenant = TenantContext.get_tenant() or self.request.user.tenant
            if tenant:
                extra["tenant"] = tenant
        serializer.save(**extra)

    def perform_update(self, serializer: serializers.BaseSerializer) -> None:
        serializer.save(updated_by=self.request.user)


class SoftDeleteMixin:
    """Soft delete instead of hard delete."""

    def perform_destroy(self, instance: models.Model) -> None:
        if hasattr(instance, "soft_delete"):
            instance.soft_delete(user=self.request.user)
        else:
            instance.delete()


class TenantSerializerMixin(serializers.ModelSerializer):
    """Auto-assign tenant on create."""

    def create(self, validated_data: dict) -> models.Model:
        request = self.context.get("request")
        if request and hasattr(self.Meta.model, "tenant"):
            tenant = TenantContext.get_tenant() or request.user.tenant
            if tenant and "tenant" not in validated_data:
                validated_data["tenant"] = tenant
        if request:
            validated_data.setdefault("created_by", request.user)
            validated_data.setdefault("updated_by", request.user)
        return super().create(validated_data)

    def update(self, instance: models.Model, validated_data: dict) -> models.Model:
        request = self.context.get("request")
        if request:
            validated_data["updated_by"] = request.user
        return super().update(instance, validated_data)


def get_client_ip(request: Any) -> Optional[str]:
    """Extract client IP from request."""
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")