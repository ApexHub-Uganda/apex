"""Hostel report API endpoints."""
from __future__ import annotations

from datetime import datetime

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exports import csv_attachment_response, rows_from_summary
from apps.core.permissions import IsStaffMember, RequiresFeature, TenantActivePermission
from apps.hostel.reports import build_hostel_reports


class HostelReportsView(APIView):
    permission_classes = [IsAuthenticated, IsStaffMember, TenantActivePermission]

    def get_permissions(self):
        perms = super().get_permissions()
        perms.append(RequiresFeature("hostel_reports")())
        return perms

    def get(self, request):
        tenant = request.user.tenant
        if tenant is None:
            return Response({"success": True, "data": {"rows": [], "totals": {}, "summary": {}}})

        report_type = request.query_params.get("type", "occupancy")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        export_format = request.query_params.get("format", "json")

        parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
        data = build_hostel_reports(
            tenant=tenant,
            report_type=report_type,
            start_date=parsed_start,
            end_date=parsed_end,
        )

        if export_format == "csv":
            rows = data.get("rows") or []
            if not rows and data.get("summary"):
                rows = rows_from_summary(data["summary"])
            return csv_attachment_response(
                rows=rows,
                filename=f"hostel-{report_type}.csv",
            )

        return Response({"success": True, "data": data})
