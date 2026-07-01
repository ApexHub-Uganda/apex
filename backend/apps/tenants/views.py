"""Tenant views."""
from __future__ import annotations

from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsSchoolAdmin, IsSuperAdmin, TenantActivePermission
from apps.tenants.models import Tenant
from apps.tenants.serializers import (
    TenantAdminCreateSerializer,
    TenantAdminListSerializer,
    TenantAdminUpdateSerializer,
    TenantMinimalListSerializer,
    TenantBrandingSerializer,
    TenantRegistrationSerializer,
    TenantSerializer,
    TenantSuspendSerializer,
)


def build_school_context_payload(tenant: Tenant | None, user) -> dict:
    """Lightweight school context for the school-admin SPA."""
    if tenant is None:
        return {
            "id": None,
            "name": getattr(user, "tenant_name", None) or "Your School",
            "code": "",
            "email": user.email,
            "status": getattr(user, "tenant_status", None) or "pending",
            "is_verified": bool(getattr(user, "tenant", None) and user.tenant.is_verified),
            "enabled_feature_keys": ["dashboard_analytics", "school_settings"],
            "feature_flags": {
                "dashboard_analytics": True,
                "school_settings": True,
            },
            "navigation_menu": [],
            "dashboard_widgets": [],
            "subscription": None,
            "primary_color": "#0F766E",
            "secondary_color": "#FF7F50",
            "accent_color": "#F5E6CA",
            "registration_type": getattr(user, "tenant_registration_type", None) or "pending",
        }

    from apps.subscriptions.services import (
        get_enabled_feature_keys,
        get_subscription_summary,
        get_tenant_dashboard_widgets,
        get_tenant_feature_flags,
        get_tenant_navigation,
    )

    enabled_keys = list(get_enabled_feature_keys(tenant))
    feature_flags = get_tenant_feature_flags(tenant)

    # Core modules should always be reachable for authenticated school admins.
    for core_key in ("dashboard_analytics", "school_settings"):
        if core_key not in enabled_keys:
            enabled_keys.append(core_key)
        feature_flags[core_key] = True

    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "code": tenant.code,
        "email": tenant.email,
        "phone": tenant.phone,
        "address": tenant.address,
        "city": tenant.city,
        "country": tenant.country,
        "timezone": tenant.timezone,
        "logo": tenant.logo.url if tenant.logo else None,
        "status": tenant.status,
        "is_verified": tenant.is_verified,
        "is_suspended": tenant.is_suspended,
        "tagline": tenant.tagline,
        "website": tenant.website,
        "registration_type": tenant.registration_type,
        "primary_color": tenant.primary_color,
        "secondary_color": tenant.secondary_color,
        "accent_color": tenant.accent_color,
        "enabled_feature_keys": enabled_keys,
        "feature_flags": feature_flags,
        "navigation_menu": get_tenant_navigation(tenant),
        "dashboard_widgets": get_tenant_dashboard_widgets(tenant),
        "subscription": get_subscription_summary(tenant),
    }


class TenantRegistrationView(generics.CreateAPIView):
    """Public school registration endpoint."""

    serializer_class = TenantRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant = serializer.save()
        return Response(
            {
                "success": True,
                "message": "School registered successfully. Complete onboarding to get started.",
                "tenant": TenantSerializer(tenant).data,
                "tenant_id": str(tenant.id),
            },
            status=status.HTTP_201_CREATED,
        )


class SchoolContextView(APIView):
    """Reliable school-admin context — works even while approval is pending."""

    permission_classes = [IsSchoolAdmin]

    def get(self, request: Request) -> Response:
        tenant = getattr(request.user, "tenant", None)
        return Response({
            "success": True,
            "data": build_school_context_payload(tenant, request.user),
        })


class TenantViewSet(viewsets.ModelViewSet):
    """Tenant CRUD for admins."""

    serializer_class = TenantSerializer
    queryset = Tenant.objects.all()
    filterset_fields = ["status", "is_suspended", "country", "is_verified"]
    search_fields = ["name", "code", "email", "city"]
    ordering_fields = ["name", "created_at"]

    def get_serializer_class(self):
        user = self.request.user
        if user.is_authenticated and user.is_super_admin:
            if self.action == "create":
                return TenantAdminCreateSerializer
            if self.action in ("update", "partial_update"):
                return TenantAdminUpdateSerializer
            if self.action == "list":
                return TenantAdminListSerializer
        return TenantSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsSchoolAdmin()]
        if self.action in ("create", "destroy", "update", "partial_update"):
            return [IsSuperAdmin()]
        return [IsSchoolAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.is_super_admin:
            return Tenant.objects.all()
        if user.tenant_id:
            return Tenant.objects.filter(id=user.tenant_id)
        return Tenant.objects.none()

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdmin])
    def verify(self, request: Request, pk: str = None) -> Response:
        from apps.platform.services.notifications import approve_school_registration

        tenant = self.get_object()
        approve_school_registration(tenant, actor=request.user)
        return Response({"success": True, "message": "School approved and activated.", "tenant": TenantSerializer(tenant).data})

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdmin])
    def suspend(self, request: Request, pk: str = None) -> Response:
        tenant = self.get_object()
        ser = TenantSuspendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tenant.suspend(reason=ser.validated_data.get("reason", ""))
        return Response({"success": True, "message": "Tenant suspended."})

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdmin])
    def unsuspend(self, request: Request, pk: str = None) -> Response:
        tenant = self.get_object()
        tenant.unsuspend()
        return Response({"success": True, "message": "Tenant unsuspended."})

    @action(detail=True, methods=["patch"], permission_classes=[IsSchoolAdmin, TenantActivePermission])
    def branding(self, request: Request, pk: str = None) -> Response:
        tenant = self.get_object()
        ser = TenantBrandingSerializer(tenant, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class CurrentTenantView(generics.RetrieveAPIView):
    """Get current user's tenant (allowed while pending approval)."""

    serializer_class = TenantSerializer
    permission_classes = [IsSchoolAdmin]

    def get_object(self) -> Tenant:
        tenant = getattr(self.request.user, "tenant", None)
        if tenant is None:
            from rest_framework.exceptions import NotFound
            raise NotFound("No school is linked to this account.")
        return tenant

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        try:
            return super().retrieve(request, *args, **kwargs)
        except Exception:
            return Response({
                "success": True,
                "data": build_school_context_payload(getattr(request.user, "tenant", None), request.user),
            })