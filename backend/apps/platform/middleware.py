"""Platform middleware."""
from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse

from apps.platform.services.maintenance import (
    MAINTENANCE_MESSAGE,
    authenticate_request_user,
    is_maintenance_mode,
    should_bypass_maintenance,
)


class JWTAuthenticationMiddleware:
    """Attach JWT user to the request before maintenance checks."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = authenticate_request_user(request)
        if user is not None:
            request.user = user
        return self.get_response(request)


class MaintenanceModeMiddleware:
    """Block API access during maintenance except for super admins and auth/health."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if is_maintenance_mode() and not should_bypass_maintenance(request):
            return JsonResponse(
                {
                    "success": False,
                    "error": {
                        "code": "maintenance_mode",
                        "message": MAINTENANCE_MESSAGE,
                    },
                },
                status=503,
            )
        return self.get_response(request)