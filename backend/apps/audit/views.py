from django.db.models import Count
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.audit.filters import AuditLogFilterSet
from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogDetailSerializer, AuditLogListSerializer
from apps.audit.services import build_audit_log_pdf, build_audit_logs_list_pdf
from apps.core.constants import UserRole
from apps.core.exports import export_filename, pdf_attachment_response
from apps.core.permissions import IsSchoolAdmin, IsSuperAdmin
from apps.tenants.models import Tenant


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    filterset_class = AuditLogFilterSet
    search_fields = ["description", "resource_id", "action", "user__email"]
    ordering_fields = ["created_at", "action", "resource_type", "status_code"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AuditLogDetailSerializer
        return AuditLogListSerializer

    def get_permissions(self):
        return [IsSuperAdmin()] if self.request.user.role == UserRole.SUPER_ADMIN else [IsSchoolAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRole.SUPER_ADMIN:
            tenant_id = self.request.query_params.get("tenant_id")
            qs = AuditLog.objects.select_related("user", "tenant")
            if tenant_id:
                return qs.filter(tenant_id=tenant_id)
            return qs
        return AuditLog.objects.filter(tenant=user.tenant).select_related("user", "tenant")

    @action(detail=False, methods=["get"], url_path="filter-options")
    def filter_options(self, request: Request) -> Response:
        qs = self.filter_queryset(self.get_queryset())
        actions = list(qs.values_list("action", flat=True).distinct().order_by("action"))
        resource_types = list(qs.values_list("resource_type", flat=True).distinct().order_by("resource_type"))
        schools = list(
            Tenant.objects.filter(audit_logs__in=qs)
            .distinct()
            .order_by("name")
            .values("id", "name")
        )
        categories = [
            {"value": "authentication", "label": "Authentication"},
            {"value": "schools", "label": "Schools"},
            {"value": "billing", "label": "Billing"},
            {"value": "users", "label": "Users"},
            {"value": "academics", "label": "Academics"},
            {"value": "communication", "label": "Communication"},
            {"value": "system", "label": "System"},
        ]
        return Response({
            "success": True,
            "data": {
                "actions": actions,
                "resource_types": resource_types,
                "categories": categories,
                "schools": schools,
                "statuses": [
                    {"value": "success", "label": "Success"},
                    {"value": "failed", "label": "Failed"},
                    {"value": "unknown", "label": "Unknown"},
                ],
            },
        })

    @action(detail=True, methods=["get"], url_path="export-pdf")
    def export_pdf(self, request: Request, pk: str = None) -> HttpResponse:
        log = self.get_object()
        data = AuditLogDetailSerializer(log).data
        pdf_bytes = build_audit_log_pdf(data)
        return pdf_attachment_response(
            pdf_bytes=pdf_bytes,
            filename=f"audit-log-{log.id}.pdf",
        )

    @action(detail=False, methods=["get"], url_path="export-pdf")
    def export_list_pdf(self, request: Request) -> HttpResponse:
        qs = self.filter_queryset(self.get_queryset())[:500]
        logs = AuditLogListSerializer(qs, many=True).data
        active_filters = {
            k: v for k, v in request.query_params.items()
            if k in {"created_after", "created_before", "action", "category", "resource_type", "tenant", "status", "search"}
            and v
        }
        pdf_bytes = build_audit_logs_list_pdf(logs, active_filters)
        return pdf_attachment_response(
            pdf_bytes=pdf_bytes,
            filename=export_filename("audit-logs", ext="pdf"),
        )