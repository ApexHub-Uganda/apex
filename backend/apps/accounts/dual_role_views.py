"""API: dual portal roles — admin grant + user switch."""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.dual_roles import (
    DualRoleError,
    dual_role_options,
    grant_roles_to_candidate,
    issue_tokens_for_user,
    revoke_role,
    role_payload,
    search_dual_role_candidates,
    switch_role,
)
from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer
from apps.core.constants import UserRole, normalize_role
from apps.core.permissions import TenantActivePermission
from apps.tenants.role_permissions import user_is_school_admin


def _require_school_admin(user) -> bool:
    return bool(
        getattr(user, "is_super_admin", False)
        or user_is_school_admin(user)
        or normalize_role(getattr(user, "role", "")) == UserRole.SCHOOL_ADMIN
    )


class DualRoleOptionsView(APIView):
    """Roles that can be dual-granted."""

    permission_classes = [IsAuthenticated, TenantActivePermission]

    def get(self, request: Request) -> Response:
        if not _require_school_admin(request.user):
            return Response({"success": False, "message": "School admin only."}, status=403)
        return Response({"success": True, "data": dual_role_options()})


class DualRoleCandidatesView(APIView):
    """
    Search school portal users **and** parent/staff directory records
    for dual-role configuration.
    """

    permission_classes = [IsAuthenticated, TenantActivePermission]

    def get(self, request: Request) -> Response:
        if not _require_school_admin(request.user):
            return Response({"success": False, "message": "School admin only."}, status=403)
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": False, "message": "No school."}, status=400)

        q = (request.query_params.get("q") or request.query_params.get("search") or "").strip()
        try:
            limit = min(int(request.query_params.get("limit") or 60), 100)
        except (TypeError, ValueError):
            limit = 60

        rows = search_dual_role_candidates(tenant=tenant, q=q, limit=limit)
        return Response({
            "success": True,
            "data": {
                "results": rows,
                "count": len(rows),
                "includes_parents": True,
                "includes_staff": True,
            },
        })


class DualRoleGrantView(APIView):
    """Grant one or more additional roles to a school user / parent / staff row."""

    permission_classes = [IsAuthenticated, TenantActivePermission]

    def post(self, request: Request) -> Response:
        if not _require_school_admin(request.user):
            return Response({"success": False, "message": "School admin only."}, status=403)
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": False, "message": "No school."}, status=400)

        roles = request.data.get("roles") or []
        if isinstance(roles, str):
            roles = [roles]
        if not roles:
            return Response({"success": False, "message": "Select at least one new role."}, status=400)

        user_id = request.data.get("user_id") or request.data.get("user")
        parent_id = request.data.get("parent_id") or request.data.get("parent")
        staff_id = request.data.get("staff_id") or request.data.get("staff")

        # Support composite ids from search: "parent:<uuid>" / "staff:<uuid>"
        raw_id = request.data.get("id") or ""
        if isinstance(raw_id, str) and ":" in raw_id and not parent_id and not staff_id and not user_id:
            kind, _, pk = raw_id.partition(":")
            if kind == "parent":
                parent_id = pk
            elif kind == "staff":
                staff_id = pk
            else:
                user_id = pk

        try:
            data = grant_roles_to_candidate(
                tenant=tenant,
                actor=request.user,
                roles=roles,
                user_id=str(user_id) if user_id else None,
                parent_id=str(parent_id) if parent_id else None,
                staff_id=str(staff_id) if staff_id else None,
            )
        except DualRoleError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=400,
            )

        user = User.objects.filter(pk=data["user_id"]).first()
        if user:
            data["user"] = UserSerializer(user).data
            data["dual_role"] = role_payload(user)
        return Response({
            "success": True,
            "message": data.get("message"),
            "data": data,
        })


class DualRoleRevokeView(APIView):
    permission_classes = [IsAuthenticated, TenantActivePermission]

    def post(self, request: Request) -> Response:
        if not _require_school_admin(request.user):
            return Response({"success": False, "message": "School admin only."}, status=403)
        tenant = request.user.tenant
        user_id = request.data.get("user_id") or request.data.get("user")
        role = request.data.get("role")
        target = User.objects.filter(pk=user_id, tenant=tenant).first()
        if not target:
            return Response({"success": False, "message": "User not found."}, status=404)
        try:
            data = revoke_role(user=target, role=role, actor=request.user)
        except DualRoleError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=400,
            )
        target.refresh_from_db()
        data["dual_role"] = role_payload(target)
        return Response({"success": True, "data": data, "message": f"Role “{role}” removed."})


class SwitchRoleView(APIView):
    """
    Authenticated user switches their active portal role.

    Re-issues JWT access/refresh so the rest of the stack sees the new User.role.
    """

    permission_classes = [IsAuthenticated, TenantActivePermission]

    def post(self, request: Request) -> Response:
        role = request.data.get("role")
        if not role:
            return Response({"success": False, "message": "role is required."}, status=400)
        try:
            user = switch_role(user=request.user, role=role)
        except DualRoleError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=400,
            )
        tokens = issue_tokens_for_user(user)
        user_data = UserSerializer(user).data
        dual = role_payload(user)
        user_data.update({
            "available_roles": dual["available_roles"],
            "can_switch_role": dual["can_switch_role"],
            "primary_role": dual["primary_role"],
            "active_role": dual["active_role"],
            "role_labels": dual["role_labels"],
        })
        return Response({
            "success": True,
            "message": f"Switched to {dual['role_labels'].get(dual['active_role'], dual['active_role'])}.",
            "data": {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": user_data,
            },
        })
