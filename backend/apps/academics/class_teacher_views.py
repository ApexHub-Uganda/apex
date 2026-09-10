"""API for class-teacher assignment (whole class or stream)."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.services.class_teachers import (
    ClassTeacherError,
    assign_class_teacher,
    form_options_class_teachers,
    list_class_teacher_assignments,
    unassign_class_teacher,
)
from apps.core.permissions import IsStaffMember, RequiresAnyFeature, TenantActivePermission
from apps.tenants.role_permissions import user_is_school_admin


def _can_manage_class_teachers(user) -> bool:
    if user_is_school_admin(user):
        return True
    from apps.tenants.role_permissions import user_can_access_feature

    tenant = user.tenant
    if tenant is None:
        return False
    return (
        user_can_access_feature(tenant, user, "teacher_assignments", require_write=True)
        or user_can_access_feature(tenant, user, "subject_assignment", require_write=True)
        or user_can_access_feature(tenant, user, "classes", require_write=True)
        or user_can_access_feature(tenant, user, "dos_workspace", require_write=True)
    )


class ClassTeacherAssignmentListView(APIView):
    """List class/stream heads for the school."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(),
            IsStaffMember(),
            TenantActivePermission(),
            RequiresAnyFeature(
                "teacher_assignments",
                "subject_assignment",
                "classes",
                "class_teacher_tools",
                "dos_workspace",
            )(),
        ]

    def get(self, request: Request) -> Response:
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"results": [], "count": 0}})
        rows = list_class_teacher_assignments(tenant=tenant)
        # Optional filters
        teacher = request.query_params.get("teacher")
        school_class = request.query_params.get("school_class")
        assigned = request.query_params.get("assigned")
        if teacher:
            rows = [r for r in rows if r.get("teacher_id") == str(teacher)]
        if school_class:
            rows = [r for r in rows if r.get("school_class_id") == str(school_class)]
        if assigned == "1":
            rows = [r for r in rows if r.get("is_assigned")]
        elif assigned == "0":
            rows = [r for r in rows if not r.get("is_assigned")]
        return Response({
            "success": True,
            "data": {
                "results": rows,
                "count": len(rows),
                "can_manage": _can_manage_class_teachers(request.user),
            },
        })


class ClassTeacherFormOptionsView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(),
            IsStaffMember(),
            TenantActivePermission(),
            RequiresAnyFeature(
                "teacher_assignments",
                "subject_assignment",
                "classes",
                "dos_workspace",
            )(),
        ]

    def get(self, request: Request) -> Response:
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"teachers": [], "classes": []}})
        data = form_options_class_teachers(tenant=tenant)
        data["can_manage"] = _can_manage_class_teachers(request.user)
        return Response({"success": True, "data": data})


class ClassTeacherAssignView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(),
            IsStaffMember(),
            TenantActivePermission(),
            RequiresAnyFeature(
                "teacher_assignments",
                "subject_assignment",
                "classes",
                "dos_workspace",
            )(),
        ]

    def post(self, request: Request) -> Response:
        if not _can_manage_class_teachers(request.user):
            return Response(
                {"success": False, "message": "You do not have permission to assign class teachers."},
                status=status.HTTP_403_FORBIDDEN,
            )
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": False, "message": "No school context."}, status=400)
        try:
            data = assign_class_teacher(
                tenant=tenant,
                actor=request.user,
                school_class_id=request.data.get("school_class") or request.data.get("school_class_id"),
                teacher_id=request.data.get("teacher") or request.data.get("teacher_id"),
                stream_id=request.data.get("stream") or request.data.get("stream_id") or None,
                notes=request.data.get("notes") or "",
            )
        except ClassTeacherError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({
            "success": True,
            "message": (
                f"Assigned {data['teacher_name']} as class teacher for {data['school_class_name']}"
                + (f" · {data['stream_name']}" if data.get("stream_name") else "")
                + ". Dual-role class teacher access is enabled for their portal account."
            ),
            "data": data,
        })


class ClassTeacherUnassignView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return [
            IsAuthenticated(),
            IsStaffMember(),
            TenantActivePermission(),
            RequiresAnyFeature(
                "teacher_assignments",
                "subject_assignment",
                "classes",
                "dos_workspace",
            )(),
        ]

    def post(self, request: Request) -> Response:
        if not _can_manage_class_teachers(request.user):
            return Response(
                {"success": False, "message": "You do not have permission to unassign class teachers."},
                status=status.HTTP_403_FORBIDDEN,
            )
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": False, "message": "No school context."}, status=400)
        try:
            data = unassign_class_teacher(
                tenant=tenant,
                actor=request.user,
                school_class_id=request.data.get("school_class") or request.data.get("school_class_id"),
                stream_id=request.data.get("stream") or request.data.get("stream_id") or None,
            )
        except ClassTeacherError as exc:
            return Response(
                {"success": False, "message": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({
            "success": True,
            "message": f"Class teacher removed for the selected class/stream.",
            "data": data,
        })
