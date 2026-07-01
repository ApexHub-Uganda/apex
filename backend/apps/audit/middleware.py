"""Audit middleware for API request logging."""
from __future__ import annotations

import json
import logging
from typing import Callable

from django.http import HttpRequest, HttpResponse

from apps.audit.models import AuditLog
from apps.core.mixins import get_client_ip
from apps.tenants.context import TenantContext

logger = logging.getLogger(__name__)

AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
AUDIT_PATH_PREFIXES = ("/api/v1/",)


class AuditMiddleware:
    """Log mutating API requests to audit trail."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        if request.method in AUDIT_METHODS and request.path.startswith(AUDIT_PATH_PREFIXES):
            self._log_request(request, response)

        return response

    def _log_request(self, request: HttpRequest, response: HttpResponse) -> None:
        try:
            user = getattr(request, "user", None)
            tenant = TenantContext.get_tenant()

            if not user or not user.is_authenticated:
                return

            action_map = {
                "POST": "create",
                "PUT": "update",
                "PATCH": "update",
                "DELETE": "delete",
            }

            resource_type = self._extract_resource_type(request.path)

            AuditLog.objects.create(
                tenant=tenant or (user.tenant if user and user.is_authenticated else None),
                user=user if user and user.is_authenticated else None,
                action=action_map.get(request.method, request.method.lower()),
                resource_type=resource_type,
                resource_id=self._extract_resource_id(request.path),
                description=f"{request.method} {request.path}",
                ip_address=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                request_method=request.method,
                request_path=request.path[:500],
                status_code=response.status_code,
            )
        except Exception:
            logger.exception("Failed to write audit log")

    @staticmethod
    def _extract_resource_type(path: str) -> str:
        parts = [p for p in path.split("/") if p and p != "api" and p != "v1"]
        return parts[0] if parts else "unknown"

    @staticmethod
    def _extract_resource_id(path: str) -> str:
        parts = [p for p in path.split("/") if p]
        for part in reversed(parts):
            if len(part) == 36 and "-" in part:
                return part
        return ""