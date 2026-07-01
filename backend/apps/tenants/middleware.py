"""Tenant resolution middleware."""
from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse

from apps.core.constants import UserRole
from apps.tenants.context import TenantContext


class TenantMiddleware:
    """Set tenant context from authenticated user's JWT."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        TenantContext.clear()

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            TenantContext.set_user(user)

            if user.role == UserRole.SUPER_ADMIN:
                tenant_id = request.headers.get("X-Tenant-ID") or request.GET.get("tenant_id")
                if tenant_id:
                    from apps.tenants.models import Tenant
                    try:
                        tenant = Tenant.objects.get(id=tenant_id)
                        TenantContext.set_tenant(tenant)
                    except (Tenant.DoesNotExist, ValueError):
                        pass
            elif user.tenant_id:
                TenantContext.set_tenant(user.tenant)

        response = self.get_response(request)
        TenantContext.clear()
        return response