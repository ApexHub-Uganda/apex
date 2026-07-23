"""API for recent attendance sessions list, detail, and PDF print."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.attendance.session_history import (
    AttendanceSessionHistoryError,
    build_attendance_session_pdf,
    get_attendance_session_detail,
    list_recent_attendance_sessions,
)
from apps.core.exports import pdf_attachment_response
from apps.core.permissions import IsStaffMember, RequiresAnyFeature, TenantActivePermission


def _history_permissions():
    return [
        IsAuthenticated(),
        IsStaffMember(),
        TenantActivePermission(),
        RequiresAnyFeature(
            "attendance_sessions",
            "student_attendance",
            "lesson_attendance",
        )(),
    ]


class AttendanceSessionsRecentView(APIView):
    """List recent taken attendance (class days + lesson sessions) with summaries."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return _history_permissions()

    def get(self, request: Request) -> Response:
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"results": [], "count": 0}})
        try:
            limit = int(request.query_params.get("limit") or 40)
        except (TypeError, ValueError):
            limit = 40
        try:
            days = int(request.query_params.get("days") or 60)
        except (TypeError, ValueError):
            days = 60
        results = list_recent_attendance_sessions(
            tenant, request.user, limit=limit, days=days,
        )
        return Response({
            "success": True,
            "data": {
                "results": results,
                "count": len(results),
            },
        })


class AttendanceSessionDetailView(APIView):
    """Full roster for one attendance session (class day or lesson)."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return _history_permissions()

    def get(self, request: Request, session_key: str) -> Response:
        tenant = request.user.tenant
        if tenant is None:
            return Response(
                {"success": False, "message": "No school context."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            detail = get_attendance_session_detail(tenant, request.user, session_key)
        except AttendanceSessionHistoryError as exc:
            code = 404 if exc.code == "not_found" else (403 if exc.code == "forbidden" else 400)
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=code)
        return Response({"success": True, "data": detail})


class AttendanceSessionPdfView(APIView):
    """Branded PDF printout of a session roster."""

    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        return _history_permissions()

    def get(self, request: Request, session_key: str):
        tenant = request.user.tenant
        if tenant is None:
            return Response(
                {"success": False, "message": "No school context."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            pdf = build_attendance_session_pdf(
                tenant=tenant,
                user=request.user,
                session_key=session_key,
                request=request,
            )
        except AttendanceSessionHistoryError as exc:
            code = 404 if exc.code == "not_found" else (403 if exc.code == "forbidden" else 400)
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=code)

        safe = session_key.replace(":", "-").replace("/", "-")[:80]
        return pdf_attachment_response(
            pdf_bytes=pdf,
            filename=f"attendance-session-{safe}.pdf",
        )
