"""Tenant views."""
from __future__ import annotations

from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.constants import UserRole, normalize_role
from apps.core.permissions import IsSchoolAdmin, IsSchoolPortalUser, IsSuperAdmin, TenantActivePermission
from apps.tenants.models import Tenant
from apps.tenants.serializers import (
    TenantAdminCreateSerializer,
    TenantAdminListSerializer,
    TenantAdminUpdateSerializer,
    TenantMinimalListSerializer,
    TenantBrandingSerializer,
    TenantChangePlanSerializer,
    TenantPermanentDeleteSerializer,
    ResetRolePermissionsSerializer,
    TenantRegistrationSerializer,
    TenantSerializer,
    TenantSuspendSerializer,
)


def _resolve_user_tenant(user) -> Tenant | None:
    """Resolve school tenant from user FK (JWT may not prefetch tenant)."""
    tenant = getattr(user, "tenant", None)
    if tenant is not None:
        return tenant
    tenant_id = getattr(user, "tenant_id", None)
    if not tenant_id:
        return None
    return Tenant.objects.filter(pk=tenant_id).first()


def build_school_context_payload(tenant: Tenant | None, user) -> dict:
    """Lightweight school context for the school portal SPA."""
    from apps.tenants.role_dashboards import (
        filter_dashboard_widgets,
        filter_quick_actions,
        get_role_profile,
    )
    from apps.tenants.role_permissions import (
        get_user_feature_permissions,
        get_user_module_menu,
        get_user_module_permissions,
        permissions_to_strings,
    )

    user_role = normalize_role(getattr(user, "role", None))
    is_school_admin = bool(
        user
        and getattr(user, "is_authenticated", False)
        and user.role in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
    )

    if tenant is None:
        tenant = _resolve_user_tenant(user)

    if tenant is None:
        return {
            "id": None,
            "name": getattr(user, "tenant_name", None) or "Your School",
            "code": "",
            "email": user.email,
            "status": getattr(user, "tenant_status", None) or "pending",
            "is_verified": bool(getattr(user, "tenant", None) and user.tenant.is_verified),
            "is_suspended": False,
            "access_blocked": False,
            "suspension_reason": "",
            "enabled_feature_keys": ["dashboard_analytics", "school_settings"],
            "feature_flags": {
                "dashboard_analytics": True,
                "school_settings": True,
            },
            "navigation_menu": [],
            "module_menu": [],
            "dashboard_widgets": [],
            "module_permissions": {},
            "permissions": [],
            "role_profile": get_role_profile(user),
            "user_role": user_role,
            "is_school_admin": is_school_admin,
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
        get_tenant_module_menu,
        get_tenant_navigation,
    )

    if tenant.is_suspended:
        return {
            "id": str(tenant.id),
            "name": tenant.name,
            "code": tenant.code,
            "email": tenant.email,
            "phone": tenant.phone,
            "status": tenant.status,
            "is_verified": tenant.is_verified,
            "is_suspended": True,
            "access_blocked": True,
            "suspension_reason": tenant.suspension_reason or "",
            "suspended_at": tenant.suspended_at.isoformat() if tenant.suspended_at else None,
            "registration_type": tenant.registration_type,
            "primary_color": tenant.primary_color,
            "secondary_color": tenant.secondary_color,
            "accent_color": tenant.accent_color,
            "enabled_feature_keys": [],
            "feature_flags": {},
            "navigation_menu": [],
            "module_menu": [],
            "dashboard_widgets": [],
            "subscription": get_subscription_summary(tenant),
            "features_revision": "suspended",
        }

    enabled_keys = list(get_enabled_feature_keys(tenant))
    feature_flags = get_tenant_feature_flags(tenant)
    plan_module_menu = get_tenant_module_menu(tenant)
    module_permissions = get_user_module_permissions(tenant, user)
    feature_permissions = get_user_feature_permissions(tenant, user)
    module_menu = get_user_module_menu(tenant, user)
    role_profile = get_role_profile(user)
    plan_widgets = get_tenant_dashboard_widgets(tenant)
    dashboard_widgets = filter_dashboard_widgets(
        plan_widgets, module_permissions, role_profile, feature_permissions,
    )
    role_profile = {
        **role_profile,
        "quick_actions": filter_quick_actions(
            role_profile, module_permissions, feature_permissions,
        ),
    }
    sub = tenant.active_subscription

    core_keys = ("dashboard_analytics", "school_settings")
    if is_school_admin:
        for core_key in core_keys:
            if core_key not in enabled_keys:
                enabled_keys.append(core_key)
            feature_flags[core_key] = True
    else:
        enabled_keys = [
            k for k in enabled_keys
            if feature_permissions.get(k, {}).get("can_read")
            or k in core_keys[:1]
        ]
        feature_flags = {k: v for k, v in feature_flags.items() if k in enabled_keys}

    features_revision = "none"
    if sub and sub.plan:
        features_revision = (
            f"{sub.plan_id}:{sub.updated_at.isoformat()}:{len(enabled_keys)}:"
            f"{len(module_menu)}:{user_role}"
        )

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
        "is_suspended": False,
        "access_blocked": False,
        "suspension_reason": "",
        "tagline": tenant.tagline,
        "website": tenant.website,
        "registration_type": tenant.registration_type,
        "primary_color": tenant.primary_color,
        "secondary_color": tenant.secondary_color,
        "accent_color": tenant.accent_color,
        "enabled_feature_keys": enabled_keys,
        "feature_flags": feature_flags,
        "navigation_menu": module_menu,
        "module_menu": module_menu,
        "module_permissions": module_permissions,
        "feature_permissions": feature_permissions,
        "permissions": permissions_to_strings(module_permissions, feature_permissions),
        "role_profile": role_profile,
        "user_role": user_role,
        "is_school_admin": is_school_admin,
        "dashboard_widgets": dashboard_widgets,
        "subscription": get_subscription_summary(tenant),
        "features_revision": features_revision,
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
    """Reliable school portal context — works even while approval is pending."""

    permission_classes = [IsSchoolPortalUser]

    def get(self, request: Request) -> Response:
        tenant = _resolve_user_tenant(request.user)
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
        from apps.subscriptions.services import invalidate_tenant_cache

        invalidate_tenant_cache(str(tenant.id))
        return Response({"success": True, "message": "Tenant suspended."})

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdmin])
    def unsuspend(self, request: Request, pk: str = None) -> Response:
        tenant = self.get_object()
        tenant.unsuspend()
        from apps.subscriptions.services import invalidate_tenant_cache

        invalidate_tenant_cache(str(tenant.id))
        return Response({"success": True, "message": "Tenant unsuspended."})

    @action(detail=True, methods=["get"], permission_classes=[IsSuperAdmin], url_path="deletion-preview")
    def deletion_preview(self, request: Request, pk: str = None) -> Response:
        from apps.tenants.services import get_tenant_deletion_preview

        tenant = self.get_object()
        return Response({
            "success": True,
            "data": get_tenant_deletion_preview(tenant),
        })

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdmin], url_path="change-plan")
    def change_plan(self, request: Request, pk: str = None) -> Response:
        from apps.subscriptions.models import Plan
        from apps.subscriptions.serializers import SubscriptionSerializer
        from apps.subscriptions.services import (
            get_enabled_feature_keys,
            get_subscription_summary,
            get_tenant_module_menu,
        )
        from apps.tenants.services import assign_tenant_plan

        tenant = self.get_object()
        ser = TenantChangePlanSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        plan = Plan.objects.get(slug=data["plan_slug"], is_active=True)
        sub = assign_tenant_plan(
            tenant,
            plan,
            billing_cycle=data.get("billing_cycle", "monthly"),
            subscription_status=data.get("subscription_status", "trial"),
            period_days=data.get("period_days", 30),
            notes=data.get("notes", ""),
            actor=request.user,
        )

        module_menu = get_tenant_module_menu(tenant)
        return Response({
            "success": True,
            "message": f"Plan updated to {plan.name}. {len(module_menu)} modules now active for this school.",
            "subscription": SubscriptionSerializer(sub).data,
            "subscription_summary": get_subscription_summary(tenant),
            "module_count": len(module_menu),
            "feature_count": len(get_enabled_feature_keys(tenant)),
            "school_verified": tenant.is_verified,
        })

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdmin], url_path="permanent-delete")
    def permanent_delete(self, request: Request, pk: str = None) -> Response:
        from apps.tenants.services import delete_tenant_permanently

        tenant = self.get_object()
        ser = TenantPermanentDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            result = delete_tenant_permanently(
                tenant,
                actor=request.user,
                confirmation_name=ser.validated_data["confirmation_name"],
            )
        except ValueError as exc:
            return Response(
                {"success": False, "error": {"message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "success": True,
            "message": f'School "{result["school_name"]}" and all associated data have been permanently removed.',
            "data": result,
        })

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        return Response(
            {
                "success": False,
                "error": {
                    "message": (
                        "Direct delete is disabled. Use POST /tenants/{id}/permanent-delete/ "
                        "with confirmation_name and acknowledge_permanent."
                    ),
                },
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["patch"], permission_classes=[IsSchoolAdmin, TenantActivePermission])
    def branding(self, request: Request, pk: str = None) -> Response:
        tenant = self.get_object()
        ser = TenantBrandingSerializer(tenant, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class RolePermissionMatrixView(APIView):
    """School-admin matrix for configuring role module permissions."""

    permission_classes = [IsSchoolAdmin]

    def get(self, request: Request) -> Response:
        tenant = _resolve_user_tenant(request.user)
        if tenant is None:
            return Response(
                {"success": False, "error": {"message": "No school linked to this account."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        from apps.tenants.role_permissions import get_role_permission_matrix

        return Response({
            "success": True,
            "data": get_role_permission_matrix(tenant),
        })

    def put(self, request: Request) -> Response:
        tenant = _resolve_user_tenant(request.user)
        if tenant is None:
            return Response(
                {"success": False, "error": {"message": "No school linked to this account."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        from apps.tenants.role_permissions import save_role_permissions

        permissions = request.data.get("permissions", [])
        if not isinstance(permissions, list):
            return Response(
                {"success": False, "error": {"message": "permissions must be a list."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        matrix = save_role_permissions(tenant, permissions, actor=request.user)
        return Response({
            "success": True,
            "message": "Role permissions updated.",
            "data": matrix,
        })

    def post(self, request: Request) -> Response:
        """Reset role permissions to defaults (requires password confirmation)."""
        tenant = _resolve_user_tenant(request.user)
        if tenant is None:
            return Response(
                {"success": False, "error": {"message": "No school linked to this account."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        payload = {
            "role": request.data.get("role") or request.query_params.get("role") or "",
            "acknowledge_risk": request.data.get("acknowledge_risk"),
            "password": request.data.get("password", ""),
        }
        serializer = ResetRolePermissionsSerializer(data=payload, context={"request": request})
        serializer.is_valid(raise_exception=True)

        from apps.tenants.role_permissions import reset_role_permissions

        role = serializer.validated_data.get("role") or None
        matrix = reset_role_permissions(tenant, role=role)
        return Response({
            "success": True,
            "message": "Role permissions reset to defaults.",
            "data": matrix,
        })


class CurrentTenantView(generics.RetrieveAPIView):
    """Get current user's tenant (allowed while pending approval)."""

    serializer_class = TenantSerializer
    permission_classes = [IsSchoolPortalUser]

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