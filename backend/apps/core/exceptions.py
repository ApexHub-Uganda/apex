"""Custom exceptions and DRF exception handler."""
from __future__ import annotations

from typing import Any, Optional

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
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

    response = exception_handler(exc, context)

    if response is not None:
        error_body: dict[str, Any] = {
            "success": False,
            "error": {
                "code": getattr(exc, "default_code", "error"),
                "message": _extract_detail(response.data),
                "details": response.data if isinstance(response.data, dict) else None,
            },
        }
        response.data = error_body

    return response


def _extract_detail(data: Any) -> str:
    if isinstance(data, dict):
        if "detail" in data:
            detail = data["detail"]
            return str(detail) if not isinstance(detail, list) else "; ".join(str(d) for d in detail)
        return "; ".join(f"{k}: {v}" for k, v in data.items())
    if isinstance(data, list):
        return "; ".join(str(item) for item in data)
    return str(data)