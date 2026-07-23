"""Geofence + staff GPS attendance APIs."""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.attendance.geofence import (
    GeofenceError,
    evaluate_location,
    geofence_payload,
    get_geofence,
    save_geofence,
)
from apps.attendance.staff_geo_attendance import (
    StaffAttendanceError,
    staff_attendance_status,
    staff_check_in,
    staff_check_out,
)
from apps.core.constants import UserRole, normalize_role
from apps.core.permissions import TenantActivePermission
from apps.tenants.role_permissions import user_is_school_admin


def _is_school_admin(user) -> bool:
    return bool(
        getattr(user, "is_super_admin", False)
        or user_is_school_admin(user)
        or normalize_role(getattr(user, "role", "")) == UserRole.SCHOOL_ADMIN
    )


class SchoolGeofenceView(APIView):
    """GET: current campus boundary. PUT/PATCH: school admin save."""

    permission_classes = [IsAuthenticated, TenantActivePermission]

    def get(self, request: Request) -> Response:
        tenant = request.user.tenant
        fence = get_geofence(tenant)
        return Response({"success": True, "data": geofence_payload(fence)})

    def put(self, request: Request) -> Response:
        return self._save(request)

    def patch(self, request: Request) -> Response:
        return self._save(request)

    def _save(self, request: Request) -> Response:
        if not _is_school_admin(request.user):
            return Response({"success": False, "message": "Only school admin can set the campus boundary."}, status=403)
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": False, "message": "No school."}, status=400)
        try:
            fence = save_geofence(
                tenant=tenant,
                user=request.user,
                vertices=request.data.get("vertices") or [],
                buffer_meters=request.data.get("buffer_meters", 25),
                is_enabled=request.data.get("is_enabled", True),
                name=request.data.get("name") or "Main campus",
            )
        except GeofenceError as exc:
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=400)
        return Response({
            "success": True,
            "message": "School boundary saved.",
            "data": geofence_payload(fence),
        })


class StaffAttendanceStatusView(APIView):
    permission_classes = [IsAuthenticated, TenantActivePermission]

    def get(self, request: Request) -> Response:
        data = staff_attendance_status(tenant=request.user.tenant, user=request.user)
        return Response({"success": True, "data": data})


class StaffCheckInView(APIView):
    permission_classes = [IsAuthenticated, TenantActivePermission]

    def post(self, request: Request) -> Response:
        try:
            data = staff_check_in(
                tenant=request.user.tenant,
                user=request.user,
                lat=request.data.get("lat"),
                lng=request.data.get("lng"),
                accuracy_m=request.data.get("accuracy_m") or request.data.get("accuracy"),
            )
        except StaffAttendanceError as exc:
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=400)
        return Response({"success": True, "message": data.get("message"), "data": data})


class StaffCheckOutView(APIView):
    permission_classes = [IsAuthenticated, TenantActivePermission]

    def post(self, request: Request) -> Response:
        try:
            data = staff_check_out(
                tenant=request.user.tenant,
                user=request.user,
                lat=request.data.get("lat"),
                lng=request.data.get("lng"),
                accuracy_m=request.data.get("accuracy_m") or request.data.get("accuracy"),
            )
        except StaffAttendanceError as exc:
            return Response({"success": False, "message": exc.message, "code": exc.code}, status=400)
        return Response({"success": True, "message": data.get("message"), "data": data})


class LocationCheckView(APIView):
    """Dry-run: is current GPS inside campus? Used by class attendance UI."""

    permission_classes = [IsAuthenticated, TenantActivePermission]

    def post(self, request: Request) -> Response:
        evaluation = evaluate_location(
            tenant=request.user.tenant,
            lat=request.data.get("lat"),
            lng=request.data.get("lng"),
            accuracy_m=request.data.get("accuracy_m") or request.data.get("accuracy"),
        )
        return Response({
            "success": True,
            "data": evaluation,
            "message": evaluation.get("reason"),
        })
