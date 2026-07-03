"""Analytics API views."""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.services import (
    get_attendance_analytics,
    get_billing_operations,
    get_enrollment_analytics,
    get_platform_analytics,
    get_platform_dashboard,
    get_plans_subscriptions_hub,
    get_revenue_analytics,
    get_school_dashboard,
    get_school_detail,
)
from apps.tenants.models import Tenant
from apps.core.constants import UserRole
from apps.core.permissions import IsSchoolAdmin, IsSuperAdmin, RequiresFeature, TenantActivePermission


class SchoolDashboardView(APIView):
    permission_classes = [IsSchoolAdmin, TenantActivePermission]

    def get(self, request: Request) -> Response:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response({
                "success": True,
                "data": {
                    "stats": {},
                    "sections": {},
                    "widgets": [],
                    "module_stats": {},
                    "upgrade_suggestions": [],
                    "recent_activities": [],
                },
            })
        data = get_school_dashboard(str(tenant_id))
        return Response({"success": True, "data": data})


class SchoolDetailView(APIView):
    """Super-admin school detail with profile, stats, and charts."""

    permission_classes = [IsSuperAdmin]

    def get(self, request: Request, tenant_id: str) -> Response:
        if not Tenant.objects.filter(pk=tenant_id).exists():
            return Response({"success": False, "message": "School not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": True, "data": get_school_detail(tenant_id)})


class PlatformDashboardView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request: Request) -> Response:
        return Response({"success": True, "data": get_platform_dashboard()})


class PlatformAnalyticsView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request: Request) -> Response:
        return Response({"success": True, "data": get_platform_analytics()})


class PlansSubscriptionsHubView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request: Request) -> Response:
        return Response({"success": True, "data": get_plans_subscriptions_hub()})


class BillingOperationsView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request: Request) -> Response:
        return Response({"success": True, "data": get_billing_operations()})


class EnrollmentAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, TenantActivePermission]

    def get(self, request: Request) -> Response:
        tenant_id = None if request.user.role == UserRole.SUPER_ADMIN else str(request.user.tenant_id)
        return Response({"success": True, "data": get_enrollment_analytics(tenant_id)})


class AttendanceAnalyticsView(APIView):
    permission_classes = [IsSchoolAdmin, TenantActivePermission]

    def get(self, request: Request) -> Response:
        days = int(request.query_params.get("days", 30))
        data = get_attendance_analytics(str(request.user.tenant_id), days=days)
        return Response({"success": True, "data": data})


class RevenueAnalyticsView(APIView):
    permission_classes = [IsSchoolAdmin, TenantActivePermission]

    def get(self, request: Request) -> Response:
        tenant_id = None if request.user.role == UserRole.SUPER_ADMIN else str(request.user.tenant_id)
        return Response({"success": True, "data": get_revenue_analytics(tenant_id)})