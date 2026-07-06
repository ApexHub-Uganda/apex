"""Communication notification helpers."""
from __future__ import annotations

from typing import Any, Optional

from django.utils import timezone

from apps.communication.models import FeedItemDismissal, Notification

NOTIFICATION_INBOX_LIMIT = 20
NOTIFICATION_INBOX_WARNING_AT = 16


def get_user_notification_inbox_stats(user) -> dict[str, Any]:
    count = Notification.objects.filter(recipient=user, is_deleted=False).count()
    return {
        "count": count,
        "limit": NOTIFICATION_INBOX_LIMIT,
        "warning_at": NOTIFICATION_INBOX_WARNING_AT,
        "show_warning": count >= NOTIFICATION_INBOX_WARNING_AT,
        "slots_remaining": max(0, NOTIFICATION_INBOX_LIMIT - count),
    }


def enforce_user_notification_inbox_limit(
    user,
    *,
    limit: int = NOTIFICATION_INBOX_LIMIT,
) -> int:
    """Soft-delete oldest notifications beyond the per-user inbox cap."""
    active_ids = list(
        Notification.objects.filter(recipient=user, is_deleted=False)
        .order_by("-created_at")
        .values_list("id", flat=True),
    )
    if len(active_ids) <= limit:
        return 0
    overflow_ids = active_ids[limit:]
    return Notification.objects.filter(id__in=overflow_ids).update(
        is_deleted=True,
        updated_at=timezone.now(),
    )


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
    notification = Notification.objects.create(
        recipient=user,
        tenant=tenant or getattr(user, "tenant", None),
        title=title,
        message=message,
        notification_type=notification_type,
        action_url=action_url,
        metadata=metadata or {},
    )
    enforce_user_notification_inbox_limit(user)
    return notification


def get_unread_user_notifications(user) -> int:
    return Notification.objects.filter(recipient=user, is_read=False, is_deleted=False).count()


def get_navbar_user_notifications(user, *, limit: int = NOTIFICATION_INBOX_LIMIT) -> list[dict[str, Any]]:
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
    updated = Notification.objects.filter(
        recipient=user, is_read=False, is_deleted=False,
    ).update(
        is_read=True, read_at=timezone.now(),
    )
    return updated


def delete_user_notification(user, notification_id: str) -> bool:
    updated = Notification.objects.filter(
        recipient=user, id=notification_id, is_deleted=False,
    ).update(is_deleted=True, updated_at=timezone.now())
    return updated > 0


def delete_all_user_notifications(user) -> int:
    return Notification.objects.filter(recipient=user, is_deleted=False).update(
        is_deleted=True, updated_at=timezone.now(),
    )


def dismiss_feed_item(user, item_id: str) -> None:
    FeedItemDismissal.objects.update_or_create(
        user=user,
        item_id=item_id,
        defaults={"dismissed_at": timezone.now()},
    )


def dismiss_feed_items(user, item_ids: list[str]) -> int:
    count = 0
    for item_id in item_ids:
        dismiss_feed_item(user, item_id)
        count += 1
    return count


def get_dismissed_feed_item_ids(user) -> set[str]:
    return set(
        FeedItemDismissal.objects.filter(user=user).values_list("item_id", flat=True),
    )


def is_synthetic_feed_item(item_id: str) -> bool:
    if not item_id:
        return True
    prefixes = ("plan-ad-", "pending-", "subscription-")
    return item_id.startswith(prefixes)


def delete_user_feed_item(user, item_id: str) -> bool:
    if is_synthetic_feed_item(item_id):
        dismiss_feed_item(user, item_id)
        return True
    return delete_user_notification(user, item_id)