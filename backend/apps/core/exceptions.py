"""Custom exceptions and DRF exception handler."""
from __future__ import annotations

from typing import Any, Optional

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import ProtectedError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


class ApexHubException(APIException):
    """Base Apex Hub API exception."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "An error occurred."
    default_code = "error"


class TenantNotFoundError(ApexHubException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Tenant not found."
    default_code = "tenant_not_found"


class TenantSuspendedError(ApexHubException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "This school account has been suspended."
    default_code = "tenant_suspended"


class TenantPendingApprovalError(ApexHubException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Your school account is pending super admin approval."
    default_code = "tenant_pending_approval"


class SubscriptionExpiredError(ApexHubException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = "Subscription has expired. Please renew to continue."
    default_code = "subscription_expired"


class FeatureNotAvailableError(ApexHubException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "This feature is not available on your current plan."
    default_code = "feature_not_available"


class TenantIsolationError(ApexHubException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Cross-tenant access is not permitted."
    default_code = "tenant_isolation_violation"


def custom_exception_handler(exc: Exception, context: dict) -> Optional[Response]:
    """Normalize API error responses."""
    if isinstance(exc, DjangoValidationError):
        exc = ApexHubException(detail=exc.messages if hasattr(exc, "messages") else str(exc))
    elif isinstance(exc, DjangoPermissionDenied):
        exc = ApexHubException(detail=str(exc))
        exc.status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, Http404):
        exc = ApexHubException(detail="Resource not found.")
        exc.status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ProtectedError):
        message = "This record cannot be deleted because other records still depend on it."
        return Response(
            {
                "success": False,
                "message": message,
                "error": {
                    "code": "protected_delete",
                    "message": message,
                    "details": None,
                },
            },
            status=status.HTTP_409_CONFLICT,
        )

    response = exception_handler(exc, context)

    if response is not None:
        error_body: dict[str, Any] = {
            "success": False,
            "error": {
                "code": _extract_error_code(response.data, exc),
                "message": _extract_detail(response.data),
                "details": _normalize_error_details(response.data),
            },
        }
        response.data = error_body

    return response


def _format_error_value(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return str(value)


def _extract_detail(data: Any) -> str:
    if isinstance(data, dict):
        if "detail" in data:
            return _format_error_value(data["detail"])
        if "non_field_errors" in data:
            return _format_error_value(data["non_field_errors"])
        parts = [
            f"{key}: {_format_error_value(value)}"
            for key, value in data.items()
        ]
        return "; ".join(parts) if parts else "An error occurred."
    if isinstance(data, list):
        return _format_error_value(data)
    return str(data)


def _extract_error_code(data: Any, exc: Exception) -> str:
    if isinstance(data, dict):
        for key in ("non_field_errors", "detail"):
            values = data.get(key)
            if isinstance(values, list) and values:
                code = getattr(values[0], "code", None)
                if code:
                    return str(code)
    return getattr(exc, "default_code", "error")


def _normalize_error_details(data: Any) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    normalized: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, list):
            normalized[key] = [str(item) for item in value]
        else:
            normalized[key] = str(value)
    return normalized or None