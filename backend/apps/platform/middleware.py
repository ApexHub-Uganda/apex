"""Platform middleware."""
from __future__ import annotations

import json
from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse


class MaintenanceModeMiddleware:
    """Block API access during maintenance (except super admin paths)."""

    BYPASS_PATHS = ("/api/v1/auth/login/", "/api/v1/platform/health/", "/admin/")

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if getattr(settings, "MAINTENANCE_MODE", False):
            if not any(request.path.startswith(p) for p in self.BYPASS_PATHS):
                return JsonResponse(
                    {
                        "success": False,
                        "error": {
                            "code": "maintenance_mode",
                            "message": "Apex Hub is currently under maintenance. Please try again later.",
                        },
                    },
                    status=503,
                )
        return self.get_response(request)