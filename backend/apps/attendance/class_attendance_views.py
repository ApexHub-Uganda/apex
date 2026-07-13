"""Teacher class attendance marking APIs."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.attendance.class_attendance import (
    ClassAttendanceError,
    bulk_save_class_attendance,
    class_attendance_options_payload,
)
from apps.core.permissions import IsStaffMember, RequiresFeature, TenantActivePermission


class ClassAttendanceOptionsView(APIView):
    """Class list → stream list → students with existing attendance for a date."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("student_attendance")())
        return perms

    def get(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"classes": []}})

        try:
            data = class_attendance_options_payload(
                tenant,
                request.user,
                school_class_id=request.query_params.get("school_class"),
                stream_id=request.query_params.get("stream"),
                mark_date=request.query_params.get("date"),
            )
        except ClassAttendanceError as exc:
            status_code = status.HTTP_404_NOT_FOUND if exc.code == "not_found" else status.HTTP_403_FORBIDDEN
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=status_code)

        return Response({"success": True, "data": data})


class ClassAttendanceBulkView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("student_attendance")())
        return perms

    def post(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response(
                {"success": False, "message": "No school context."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        school_class_id = request.data.get("school_class")
        if not school_class_id:
            return Response(
                {"success": False, "message": "Class is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entries = request.data.get("entries") or []
        if not entries:
            return Response(
                {"success": False, "message": "No students to save."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = bulk_save_class_attendance(
                tenant=tenant,
                user=request.user,
                school_class_id=school_class_id,
                stream_id=request.data.get("stream"),
                mark_date=request.data.get("date"),
                check_in=request.data.get("check_in"),
                entries=entries,
            )
        except ClassAttendanceError as exc:
            status_code = status.HTTP_400_BAD_REQUEST
            if exc.code == "forbidden":
                status_code = status.HTTP_403_FORBIDDEN
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=status_code)

        return Response({
            "success": True,
            "message": f"Saved attendance for {result['saved']} student(s).",
            "data": result,
        })