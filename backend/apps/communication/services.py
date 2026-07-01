"""Communication notification helpers."""
from __future__ import annotations

from typing import Any, Optional

from django.utils import timezone

from apps.communication.models import Notification


def create_user_notification(
    *,
    user,
    title: str,
    message: str,
    notification_type: str = "info",
    action_url: str = "",
    metadata: Optional[dict] = None,
    tenant=None,
) -> Notification:
    return Notification.objects.create(
        recipient=user,
        tenant=tenant or getattr(user, "tenant", None),
        title=title,
        message=message,
        notification_type=notification_type,
        action_url=action_url,
        metadata=metadata or {},
    )


def get_unread_user_notifications(user) -> int:
    return Notification.objects.filter(recipient=user, is_read=False, is_deleted=False).count()


def get_navbar_user_notifications(user, *, limit: int = 5) -> list[dict[str, Any]]:
    qs = Notification.objects.filter(
        recipient=user, is_deleted=False,
    ).order_by("-created_at")[:limit]
    return [
        {
            "id": str(n.id),
            "title": n.title,
            "message": n.message,
            "type": n.notification_type,
            "is_read": n.is_read,
            "priority": "normal",
            "created_at": n.created_at.isoformat(),
            "action_url": n.action_url or "",
            "metadata": n.metadata or {},
        }
        for n in qs
    ]


def mark_all_user_notifications_read(user) -> int:
    updated = Notification.objects.filter(recipient=user, is_read=False).update(
        is_read=True, read_at=timezone.now(),
    )
    return updated