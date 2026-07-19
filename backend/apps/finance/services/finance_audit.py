"""Immutable finance audit events via existing AuditLog model."""
from __future__ import annotations

from typing import Any

from apps.audit.models import AuditLog


def log_finance_action(
    *,
    tenant,
    user,
    action: str,
    resource_type: str,
    resource_id: str = "",
    description: str = "",
    changes: dict[str, Any] | None = None,
    request=None,
) -> AuditLog:
    ip = None
    ua = ""
    method = ""
    path = ""
    if request is not None:
        ip = (
            request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR")
        )
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:500]
        method = request.method or ""
        path = (request.path or "")[:500]
    return AuditLog.objects.create(
        tenant=tenant,
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action[:50],
        resource_type=resource_type[:100],
        resource_id=str(resource_id or "")[:100],
        description=description or "",
        changes=changes or {},
        ip_address=ip or None,
        user_agent=ua,
        request_method=method[:10],
        request_path=path,
        status_code=200,
    )
