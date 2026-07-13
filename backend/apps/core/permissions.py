"""Base permission classes."""
from __future__ import annotations

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.constants import UserRole, is_school_portal_role
from apps.core.constants import TenantStatus
from apps.core.exceptions import (
    FeatureNotAvailableError,
    SubscriptionExpiredError,
    TenantPendingApprovalError,
    TenantSuspendedError,
)


class IsSuperAdmin(BasePermission):
    """Allow only platform super admins."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.SUPER_ADMIN
        )


class IsSchoolAdmin(BasePermission):
    """Allow school administrators."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
        )


class IsSchoolPortalUser(BasePermission):
    """Allow any authenticated school portal role (admin, staff, parent)."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.role == UserRole.SUPER_ADMIN:
            return True
        return is_school_portal_role(user.role)


class IsStaffMember(BasePermission):
    """Allow any school staff role."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.role == UserRole.SUPER_ADMIN
                or request.user.role in UserRole.STAFF_ROLES
            )
        )


class IsTeacherOrAbove(BasePermission):
    """Allow teachers, head teachers, and admins."""

    ALLOWED = {UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN, UserRole.HEAD_TEACHER, UserRole.TEACHER}

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in self.ALLOWED
        )


def HasRole(roles: list[str]) -> type[BasePermission]:
    """Factory for role-based permission classes."""

    class _HasRolePermission(BasePermission):
        def has_permission(self, request: Request, view: APIView) -> bool:
            return bool(
                request.user
                and request.user.is_authenticated
                and (
                    request.user.role == UserRole.SUPER_ADMIN
                    or request.user.role in roles
                )
            )

    return _HasRolePermission


class TenantActivePermission(BasePermission):
    """Ensure tenant is active and subscription valid."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.role == UserRole.SUPER_ADMIN:
            return True

        tenant = getattr(user, "tenant", None)
        if tenant is None:
            return False

        if tenant.is_suspended or tenant.status == TenantStatus.SUSPENDED:
            raise TenantSuspendedError()

        if tenant.status == TenantStatus.PENDING or not tenant.is_verified:
            raise TenantPendingApprovalError()

        subscription = getattr(tenant, "active_subscription", None)
        if subscription and subscription.is_expired and not subscription.in_grace_period:
            raise SubscriptionExpiredError()

        return True


def mutation_requires_write(request: Request, view: APIView) -> bool:
    """True when the request mutates data (POST/PUT/PATCH/DELETE or write viewset actions)."""
    action = getattr(view, "action", None)
    if action in {"prefects", "remove_prefect"}:
        return False
    if request.method not in SAFE_METHODS:
        return True
    return action in {
        "create", "update", "partial_update", "destroy",
        "validate_import", "commit_import",
        "link_student", "unlink_student", "set_children",
        "publish", "send", "delete_all",
    }


def RequiresModuleAccess(module_key: str, *, require_write: bool = False) -> type[BasePermission]:
    """Factory: plan feature + school role module permission."""

    class _RequiresModuleAccessPermission(BasePermission):
        def has_permission(self, request: Request, view: APIView) -> bool:
            user = request.user
            if not user or not user.is_authenticated:
                return False
            if user.role == UserRole.SUPER_ADMIN:
                return True

            tenant = getattr(user, "tenant", None)
            if tenant is None:
                return False

            from apps.tenants.role_permissions import user_can_access_module

            needs_write = require_write or mutation_requires_write(request, view)
            if not user_can_access_module(
                tenant, user, module_key, require_write=needs_write,
            ):
                action = "modify" if needs_write else "view"
                raise FeatureNotAvailableError(
                    detail=f"You do not have permission to {action} the {module_key.replace('_', ' ')} module.",
                )
            return True

    return _RequiresModuleAccessPermission


def RequiresFeature(feature: str) -> type[BasePermission]:
    """Factory: plan + role feature permission (read for GET, write for mutations)."""

    class _RequiresFeaturePermission(BasePermission):
        def has_permission(self, request: Request, view: APIView) -> bool:
            user = request.user
            if not user or not user.is_authenticated:
                return False

            if user.role == UserRole.SUPER_ADMIN:
                return True

            tenant = getattr(user, "tenant", None)
            if tenant is None:
                return False

            if not tenant.has_feature(feature):
                raise FeatureNotAvailableError(
                    detail=f"Feature '{feature}' is not available on your plan."
                )

            from apps.tenants.role_permissions import user_can_access_feature, user_is_school_admin

            if user_is_school_admin(user):
                return True

            needs_write = mutation_requires_write(request, view)
            if not user_can_access_feature(tenant, user, feature, require_write=needs_write):
                label = feature.replace("_", " ")
                if needs_write:
                    raise FeatureNotAvailableError(
                        detail=f"You do not have write permission for '{label}'.",
                    )
                raise FeatureNotAvailableError(
                    detail=f"You do not have permission to access '{label}'.",
                )
            return True

    return _RequiresFeaturePermission


def RequiresAnyFeature(*features: str) -> type[BasePermission]:
    """Factory: allow access when the tenant plan and role permit any listed feature."""

    class _RequiresAnyFeaturePermission(BasePermission):
        def has_permission(self, request: Request, view: APIView) -> bool:
            user = request.user
            if not user or not user.is_authenticated:
                return False

            if user.role == UserRole.SUPER_ADMIN:
                return True

            tenant = getattr(user, "tenant", None)
            if tenant is None:
                return False

            from apps.tenants.role_permissions import user_can_access_feature

            needs_write = mutation_requires_write(request, view)
            matched: list[str] = []
            for feature in features:
                if not tenant.has_feature(feature):
                    continue
                if user_can_access_feature(tenant, user, feature, require_write=needs_write):
                    matched.append(feature)

            if matched:
                return True

            labels = ", ".join(f.replace("_", " ") for f in features)
            if needs_write:
                raise FeatureNotAvailableError(
                    detail=f"You do not have write permission for any of: {labels}.",
                )
            raise FeatureNotAvailableError(
                detail=f"Feature not available. Enable one of: {labels}.",
            )

    return _RequiresAnyFeaturePermission


class IsOwnerOrStaff(BasePermission):
    """Object-level: owner or staff can access."""

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.role == UserRole.SUPER_ADMIN:
            return True

        if user.role in UserRole.STAFF_ROLES:
            if hasattr(obj, "tenant_id") and user.tenant_id:
                return obj.tenant_id == user.tenant_id
            return True

        if hasattr(obj, "user"):
            return obj.user_id == user.id
        if hasattr(obj, "id"):
            return obj.id == user.id

        return False