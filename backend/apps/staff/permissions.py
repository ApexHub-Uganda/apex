"""Staff profile management permissions."""
from __future__ import annotations

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.profile_service import user_is_profile_admin
from apps.core.constants import UserRole


class CanManageStaffRecords(BasePermission):
    """School admin or HR write access may create/update staff employment records."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.role == UserRole.SUPER_ADMIN:
            return True
        return user_is_profile_admin(user)