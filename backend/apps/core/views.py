"""Core shared views."""
from __future__ import annotations

from rest_framework import viewsets

from apps.core.mixins import AuditFieldsMixin, SoftDeleteMixin, TenantFilterMixin
from apps.core.permissions import RequiresFeature


class FeatureGateMixin:
    """Attach granular subscription feature gate to a viewset."""

    required_feature_key: str | None = None

    def get_permissions(self):
        perms = super().get_permissions()
        if self.required_feature_key:
            perms.append(RequiresFeature(self.required_feature_key)())
        return perms


class BaseModelViewSet(
    FeatureGateMixin, TenantFilterMixin, AuditFieldsMixin, SoftDeleteMixin, viewsets.ModelViewSet,
):
    """Standard CRUD viewset with tenant filtering, audit fields, and optional feature gate."""

    pass