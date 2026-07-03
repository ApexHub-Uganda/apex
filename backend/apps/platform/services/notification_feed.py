"""Navbar notification feed helpers for super-admin platform notifications."""
from __future__ import annotations

from typing import Any

from django.db.models import Exists, OuterRef
from django.utils import timezone

from apps.platform.models import PlatformNotification, PlatformNotificationReceipt


def _receipt_subquery(user, *, field: str) -> Exists:
    return Exists(
        PlatformNotificationReceipt.objects.filter(
            notification_id=OuterRef("pk"),
            user=user,
            **{field: True},
        ),
    )


def _hidden_subquery(user) -> Exists:
    return _receipt_subquery(user, field="is_deleted")


def _read_subquery(user) -> Exists:
    return _receipt_subquery(user, field="is_read")


def get_unread_platform_notifications(user) -> int:
    """Count pending platform notifications unread by this super admin."""
    return (
        PlatformNotification.objects.filter(status="pending")
        .annotate(
            is_read_by_user=_read_subquery(user),
            is_hidden_by_user=_hidden_subquery(user),
        )
        .filter(is_read_by_user=False, is_hidden_by_user=False)
        .count()
    )


def get_navbar_platform_notifications(user, *, limit: int = 5) -> list[dict[str, Any]]:
    """Recent pending platform notifications for navbar dropdown."""
    qs = (
        PlatformNotification.objects.filter(status="pending")
        .select_related("tenant")
        .annotate(
            is_read_by_user=_read_subquery(user),
            is_hidden_by_user=_hidden_subquery(user),
        )
        .filter(is_hidden_by_user=False)
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


def hide_platform_notification(notification: PlatformNotification, user) -> None:
    PlatformNotificationReceipt.objects.update_or_create(
        notification=notification,
        user=user,
        defaults={
            "is_deleted": True,
            "deleted_at": timezone.now(),
            "is_read": True,
            "read_at": timezone.now(),
        },
    )


def hide_platform_notification_by_id(user, notification_id: str) -> bool:
    try:
        notification = PlatformNotification.objects.get(pk=notification_id)
    except PlatformNotification.DoesNotExist:
        return False
    hide_platform_notification(notification, user)
    return True


def hide_all_platform_notifications(user) -> int:
    visible = platform_notifications_queryset_for_user(user)
    now = timezone.now()
    count = 0
    for notification in visible:
        receipt, _ = PlatformNotificationReceipt.objects.get_or_create(
            notification=notification,
            user=user,
        )
        if not receipt.is_deleted:
            receipt.is_deleted = True
            receipt.deleted_at = now
            receipt.is_read = True
            receipt.read_at = receipt.read_at or now
            receipt.save(update_fields=["is_deleted", "deleted_at", "is_read", "read_at"])
            count += 1
    return count


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
    return {
        "unread_count": unread,
        "pending_count": PlatformNotification.objects.filter(status="pending").count(),
        "recent": get_navbar_platform_notifications(user, limit=5),
    }


def platform_notifications_queryset_for_user(user):
    """Base queryset excluding notifications hidden by the current super admin."""
    return (
        PlatformNotification.objects.select_related("tenant", "action_taken_by")
        .annotate(is_hidden_by_user=_hidden_subquery(user))
        .filter(is_hidden_by_user=False)
    )