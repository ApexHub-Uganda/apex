"""Parent/sponsor portal HTTP endpoints."""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.constants import UserRole, normalize_role
from apps.core.permissions import IsSchoolPortalUser, TenantActivePermission
from apps.students.parent_portal import (
    build_parent_academics_bundle,
    build_parent_finance_bundle,
    build_parent_portal_overview,
)


class ParentPortalMixin:
    def _require_parent(self, request: Request):
        if normalize_role(getattr(request.user, "role", "")) != UserRole.PARENT:
            return Response(
                {"success": False, "message": "This portal is only available to parent accounts."},
                status=403,
            )
        return None


class ParentPortalOverviewView(ParentPortalMixin, APIView):
    permission_classes = [IsAuthenticated, IsSchoolPortalUser, TenantActivePermission]

    def get(self, request: Request) -> Response:
        denied = self._require_parent(request)
        if denied:
            return denied
        data = build_parent_portal_overview(tenant=request.user.tenant, user=request.user)
        return Response({"success": True, "data": data})


class ParentPortalFinanceView(ParentPortalMixin, APIView):
    permission_classes = [IsAuthenticated, IsSchoolPortalUser, TenantActivePermission]

    def get(self, request: Request) -> Response:
        denied = self._require_parent(request)
        if denied:
            return denied
        data = build_parent_finance_bundle(
            tenant=request.user.tenant,
            user=request.user,
            student_id=request.query_params.get("student_id"),
        )
        return Response({"success": True, "data": data})


class ParentPortalAcademicsView(ParentPortalMixin, APIView):
    permission_classes = [IsAuthenticated, IsSchoolPortalUser, TenantActivePermission]

    def get(self, request: Request) -> Response:
        denied = self._require_parent(request)
        if denied:
            return denied
        data = build_parent_academics_bundle(
            tenant=request.user.tenant,
            user=request.user,
            student_id=request.query_params.get("student_id"),
        )
        return Response({"success": True, "data": data})
