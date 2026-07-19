"""Multi-campus (branch) management for school tenants."""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import IsSchoolAdmin, RequiresFeature, TenantActivePermission
from apps.tenants.models import Campus
from apps.tenants.serializers import CampusSerializer


class CampusViewSet(viewsets.ModelViewSet):
    """CRUD for school campuses when multi_campus_support is on the plan."""

    serializer_class = CampusSerializer
    permission_classes = [
        IsAuthenticated,
        IsSchoolAdmin,
        TenantActivePermission,
        RequiresFeature("multi_campus_support"),
    ]
    filterset_fields = ["is_active", "is_main", "city"]
    search_fields = ["name", "code", "city", "address", "phone", "email"]
    ordering_fields = ["name", "code", "created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = Campus.objects.all()
        if getattr(user, "is_super_admin", False):
            tenant_id = self.request.query_params.get("tenant_id")
            if tenant_id:
                qs = qs.filter(tenant_id=tenant_id)
            return qs
        return qs.filter(tenant=user.tenant)

    def perform_create(self, serializer):
        tenant = self.request.user.tenant
        if tenant is None:
            raise ValidationError({"tenant": "No school context for this user."})
        self._enforce_branch_limit(tenant, excluding_id=None)
        serializer.save(tenant=tenant)

    def perform_update(self, serializer):
        serializer.save()

    def _enforce_branch_limit(self, tenant, excluding_id=None) -> None:
        sub = tenant.active_subscription
        plan = sub.plan if sub else None
        if not plan:
            return
        max_branches = int(getattr(plan, "max_branches", 0) or 0)
        if max_branches <= 0:
            return
        qs = Campus.objects.filter(tenant=tenant)
        if excluding_id:
            qs = qs.exclude(pk=excluding_id)
        if qs.count() >= max_branches:
            raise ValidationError({
                "non_field_errors": [
                    f"Your plan allows up to {max_branches} campus"
                    f"{'es' if max_branches != 1 else ''}. "
                    "Upgrade the plan to add more campuses.",
                ],
            })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_main:
            others = Campus.objects.filter(tenant=instance.tenant).exclude(pk=instance.pk).exists()
            if others:
                return Response(
                    {
                        "success": False,
                        "message": "Set another campus as main before deleting the main campus.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
