"""Bursar-facing results fee-clearance policy APIs."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsSchoolPortalUser, IsStaffMember, RequiresAnyFeature, TenantActivePermission
from apps.finance.results_access import (
    assert_can_manage_results_policy,
    get_or_create_results_policy,
    list_class_policies,
    serialize_school_policy,
    update_school_results_policy,
    upsert_class_results_policy,
)


class ResultsAccessPolicyView(APIView):
    """GET/PUT school-wide results clearance percentage."""

    permission_classes = [
        IsAuthenticated,
        IsStaffMember,
        TenantActivePermission,
        RequiresAnyFeature("bursar_workspace", "assistant_bursar_workspace", "financial_reports"),
    ]

    def get(self, request: Request) -> Response:
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": None})
        policy = get_or_create_results_policy(tenant)
        return Response({
            "success": True,
            "data": {
                "school": serialize_school_policy(policy),
                "classes": list_class_policies(tenant),
            },
        })

    def put(self, request: Request) -> Response:
        assert_can_manage_results_policy(request.user)
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": False, "message": "No school context."}, status=400)
        policy = update_school_results_policy(
            tenant,
            actor=request.user,
            default_cleared_percent=request.data.get("default_cleared_percent", 100),
            is_active=request.data.get("is_active", True),
            notes=request.data.get("notes", ""),
        )
        return Response({
            "success": True,
            "message": "School-wide results access policy updated.",
            "data": serialize_school_policy(policy),
        })


class ClassResultsAccessPolicyView(APIView):
    """PUT per-class clearance override."""

    permission_classes = [
        IsAuthenticated,
        IsStaffMember,
        TenantActivePermission,
        RequiresAnyFeature("bursar_workspace", "assistant_bursar_workspace", "financial_reports"),
    ]

    def put(self, request: Request, class_id: str) -> Response:
        assert_can_manage_results_policy(request.user)
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": False, "message": "No school context."}, status=400)
        policy = upsert_class_results_policy(
            tenant,
            actor=request.user,
            school_class_id=class_id,
            cleared_percent=request.data.get("cleared_percent", 100),
            is_active=request.data.get("is_active", True),
            notes=request.data.get("notes", ""),
        )
        return Response({
            "success": True,
            "message": "Class results access policy saved.",
            "data": {
                "school_class_id": str(policy.school_class_id),
                "cleared_percent": str(policy.cleared_percent),
                "is_active": policy.is_active,
                "notes": policy.notes,
            },
        }, status=status.HTTP_200_OK)
