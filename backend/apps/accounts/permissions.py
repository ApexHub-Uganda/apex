"""Account-specific permissions."""
from __future__ import annotations

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.constants import UserRole


class CanManageUsers(BasePermission):
    """School admin or super admin can manage users."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
        )


class CanViewOwnProfile(BasePermission):
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        if user.role == UserRole.SUPER_ADMIN:
            return True
        if obj.id == user.id:
            return True
        if user.role == UserRole.SCHOOL_ADMIN and obj.tenant_id == user.tenant_id:
            return True
        return False