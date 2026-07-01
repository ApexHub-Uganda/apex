"""Navbar notification feed helpers for super-admin platform notifications."""
from __future__ import annotations

from typing import Any

from django.db.models import Exists, OuterRef
from django.utils import timezone

from apps.platform.models import PlatformNotification, PlatformNotificationReceipt


def _read_subquery(user) -> Exists:
    return Exists(
        PlatformNotificationReceipt.objects.filter(
            notification_id=OuterRef("pk"),
            user=user,
            is_read=True,
        ),
    )


def get_unread_platform_notifications(user) -> int:
    """Count pending platform notifications unread by this super admin."""
    return (
        PlatformNotification.objects.filter(status="pending")
        .annotate(is_read_by_user=_read_subquery(user))
        .filter(is_read_by_user=False)
        .count()
    )


def get_navbar_platform_notifications(user, *, limit: int = 5) -> list[dict[str, Any]]:
    """Recent pending platform notifications for navbar dropdown."""
    qs = (
        PlatformNotification.objects.filter(status="pending")
        .select_related("tenant")
        .annotate(is_read_by_user=_read_subquery(user))
        .order_by("-created_at")[:limit]
    )
    items = []
    for notification in qs:
        items.append({
            "id": str(notification.id),
            "title": notification.title,
            "message": notification.message,
            "type": notification.notification_type,
            "is_read": notification.is_read_by_user,
            "priority": notification.priority,
            "created_at": notification.created_at.isoformat(),
            "action_url": f"/super-admin/schools/{notification.tenant_id}",
            "metadata": {
                "school_name": notification.tenant.name,
                "school_id": str(notification.tenant_id),
                **(notification.metadata or {}),
            },
        })
    return items


def mark_platform_notification_read(notification: PlatformNotification, user) -> None:
    PlatformNotificationReceipt.objects.update_or_create(
        notification=notification,
        user=user,
        defaults={"is_read": True, "read_at": timezone.now()},
    )


def mark_all_platform_notifications_read(user) -> int:
    pending = PlatformNotification.objects.filter(status="pending")
    now = timezone.now()
    for notification in pending:
        PlatformNotificationReceipt.objects.update_or_create(
            notification=notification,
            user=user,
            defaults={"is_read": True, "read_at": now},
        )
    return pending.count()


def get_platform_notification_summary(user) -> dict[str, Any]:
    unread = get_unread_platform_notifications(user)
    recent_qs = (
        PlatformNotification.objects.filter(status="pending")
        .select_related("tenant")
        .annotate(is_read_by_user=_read_subquery(user))
        .order_by("-created_at")[:5]
    )
    return {
        "unread_count": unread,
        "pending_count": PlatformNotification.objects.filter(status="pending").count(),
        "recent": get_navbar_platform_notifications(user, limit=5),
    }