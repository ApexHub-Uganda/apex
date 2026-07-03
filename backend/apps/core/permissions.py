"""Base permission classes."""
from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
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

            if not user_can_access_module(
                tenant, user, module_key, require_write=require_write,
            ):
                action = "modify" if require_write else "view"
                raise FeatureNotAvailableError(
                    detail=f"You do not have permission to {action} the {module_key.replace('_', ' ')} module.",
                )
            return True

    return _RequiresModuleAccessPermission


def RequiresFeature(feature: str) -> type[BasePermission]:
    """Factory for subscription feature flag permissions."""

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
            return True

    return _RequiresFeaturePermission


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