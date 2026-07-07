"""Platform broadcast audience resolution and multi-channel delivery."""
from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.communication.services import create_user_notification
from apps.core.constants import PlanSlug, UserRole
from apps.core.email_templates import build_platform_broadcast_email
from apps.platform.models import PlatformBroadcast, PlatformBroadcastDelivery
from apps.platform.services.integrations import EmailService, SMSService, WhatsAppService
from apps.subscriptions.models import Subscription
from apps.tenants.models import Tenant

User = get_user_model()

VALID_CHANNELS = frozenset({"email", "sms", "whatsapp"})

AUDIENCE_PLAN_MAP = {
    "trial": PlanSlug.FREE_TRIAL,
    "basic": PlanSlug.BASIC,
    "premium": PlanSlug.PREMIUM,
    "premium_plus": PlanSlug.PREMIUM_PLUS,
}

CHANNEL_LABELS = {
    "email": "Email",
    "sms": "SMS",
    "whatsapp": "WhatsApp",
}


class BroadcastError(Exception):
    """Raised when a broadcast action cannot be completed."""


def normalize_channels(channels: list[str] | None) -> list[str]:
    if not channels:
        return []
    normalized = []
    for channel in channels:
        value = str(channel).strip().lower()
        if value in VALID_CHANNELS and value not in normalized:
            normalized.append(value)
    return normalized


def _tenant_ids_for_audience(audience: str) -> list:
    if audience == "all":
        return list(Tenant.objects.values_list("id", flat=True))
    if audience == "active":
        return list(
            Tenant.objects.filter(
                status="active",
                is_suspended=False,
            ).values_list("id", flat=True),
        )

    plan_slug = AUDIENCE_PLAN_MAP.get(audience)
    if not plan_slug:
        return []

    return list(
        Subscription.objects.filter(
            plan__slug=plan_slug,
            status__in=["trial", "active", "grace_period"],
        ).values_list("tenant_id", flat=True).distinct(),
    )


def resolve_recipients(audience: str):
    tenant_ids = _tenant_ids_for_audience(audience)
    if not tenant_ids:
        return User.objects.none()
    return User.objects.filter(
        tenant_id__in=tenant_ids,
        role=UserRole.SCHOOL_ADMIN,
        is_active=True,
    ).select_related("tenant")


def preview_audience(*, audience: str, channels: list[str] | None = None) -> dict[str, Any]:
    channels = normalize_channels(channels)
    recipients = resolve_recipients(audience)
    total_recipients = recipients.count()
    total_schools = recipients.values("tenant_id").distinct().count()

    channel_stats: dict[str, dict[str, int]] = {}
    for channel in channels:
        if channel == "email":
            reachable = recipients.exclude(email="").count()
        else:
            reachable = recipients.exclude(phone="").count()
        channel_stats[channel] = {
            "label": CHANNEL_LABELS[channel],
            "reachable": reachable,
            "unreachable": max(total_recipients - reachable, 0),
        }

    sample = []
    for user in recipients[:5]:
        sample.append({
            "id": str(user.id),
            "name": user.full_name or user.email,
            "email": user.email,
            "phone": user.phone,
            "school": getattr(user.tenant, "name", ""),
        })

    return {
        "audience": audience,
        "channels": channels,
        "total_recipients": total_recipients,
        "total_schools": total_schools,
        "channel_stats": channel_stats,
        "sample_recipients": sample,
    }


def _severity_to_notification_type(severity: str) -> str:
    if severity == "critical":
        return "error"
    if severity == "warning":
        return "warning"
    return "info"


def _dispatch_channel(
    *,
    channel: str,
    user,
    title: str,
    message: str,
    severity: str = "info",
) -> tuple[str, str, str]:
    """Return (status, error_message, provider_reference)."""
    if channel == "email":
        address = (user.email or "").strip()
        if not address:
            return "skipped", "No email address on file", ""
        branded = build_platform_broadcast_email(
            title=title,
            message=message,
            severity=severity,
        )
        result = EmailService.send(
            address,
            title,
            branded.text_body,
            html_body=branded.html_body,
            tenant=user.tenant,
        )
        status = "sent" if result.success else "failed"
        return status, "" if result.success else result.message, result.reference

    phone = (user.phone or "").strip()
    if not phone:
        return "skipped", "No phone number on file", ""

    if channel == "sms":
        result = SMSService.send(phone, message, tenant=user.tenant)
    else:
        result = WhatsAppService.send(phone, message, tenant=user.tenant)

    status = "sent" if result.success else "failed"
    return status, "" if result.success else result.message, result.reference


@transaction.atomic
def send_platform_broadcast(broadcast: PlatformBroadcast, *, actor=None) -> dict[str, Any]:
    if broadcast.status not in ("draft", "scheduled"):
        raise BroadcastError("Only draft or scheduled broadcasts can be sent.")

    channels = normalize_channels(broadcast.channels)
    if not channels:
        raise BroadcastError("Select at least one broadcast channel (email, SMS, or WhatsApp).")

    recipients = list(resolve_recipients(broadcast.audience))
    now = timezone.now()
    deliveries: list[PlatformBroadcastDelivery] = []
    delivered_count = 0
    failed_count = 0
    skipped_count = 0
    notification_type = _severity_to_notification_type(broadcast.severity)

    for user in recipients:
        for channel in channels:
            status, error_message, provider_reference = _dispatch_channel(
                channel=channel,
                user=user,
                title=broadcast.title,
                message=broadcast.message,
                severity=broadcast.severity,
            )
            if status == "sent":
                delivered_count += 1
            elif status == "failed":
                failed_count += 1
            else:
                skipped_count += 1

            deliveries.append(PlatformBroadcastDelivery(
                broadcast=broadcast,
                recipient=user,
                tenant=user.tenant,
                channel=channel,
                recipient_email=user.email if channel == "email" else "",
                recipient_phone=user.phone if channel != "email" else "",
                status=status,
                error_message=error_message,
                provider_reference=provider_reference,
                sent_at=now if status == "sent" else None,
            ))

        create_user_notification(
            user=user,
            tenant=user.tenant,
            title=broadcast.title,
            message=broadcast.message,
            notification_type=notification_type,
            action_url="/school-admin/notifications",
            metadata={
                "platform_broadcast_id": str(broadcast.id),
                "severity": broadcast.severity,
                "channels": channels,
            },
        )

    if deliveries:
        PlatformBroadcastDelivery.objects.bulk_create(deliveries)

    if actor and not broadcast.created_by_id:
        broadcast.created_by = actor

    broadcast.status = "sent"
    broadcast.sent_at = now
    broadcast.recipient_count = len(recipients)
    broadcast.delivered_count = delivered_count
    broadcast.failed_count = failed_count
    broadcast.skipped_count = skipped_count
    broadcast.is_active = True
    broadcast.save(update_fields=[
        "status", "sent_at", "recipient_count", "delivered_count",
        "failed_count", "skipped_count", "created_by", "is_active", "updated_at",
    ])

    return {
        "broadcast_id": str(broadcast.id),
        "status": broadcast.status,
        "sent_at": broadcast.sent_at.isoformat(),
        "recipient_count": broadcast.recipient_count,
        "delivered_count": broadcast.delivered_count,
        "failed_count": broadcast.failed_count,
        "skipped_count": broadcast.skipped_count,
        "channels": channels,
    }


def schedule_platform_broadcast(
    broadcast: PlatformBroadcast,
    *,
    starts_at=None,
) -> PlatformBroadcast:
    if broadcast.status != "draft":
        raise BroadcastError("Only draft broadcasts can be scheduled.")

    channels = normalize_channels(broadcast.channels)
    if not channels:
        raise BroadcastError("Select at least one broadcast channel before scheduling.")

    if starts_at:
        broadcast.starts_at = starts_at
    if not broadcast.starts_at:
        raise BroadcastError("A schedule date and time is required.")

    if broadcast.starts_at <= timezone.now():
        raise BroadcastError("Schedule time must be in the future.")

    broadcast.status = "scheduled"
    broadcast.save(update_fields=["status", "starts_at", "updated_at"])
    return broadcast


def cancel_platform_broadcast(broadcast: PlatformBroadcast) -> PlatformBroadcast:
    if broadcast.status != "scheduled":
        raise BroadcastError("Only scheduled broadcasts can be cancelled.")

    broadcast.status = "cancelled"
    broadcast.cancelled_at = timezone.now()
    broadcast.save(update_fields=["status", "cancelled_at", "updated_at"])
    return broadcast


def duplicate_platform_broadcast(
    broadcast: PlatformBroadcast,
    *,
    actor=None,
) -> PlatformBroadcast:
    return PlatformBroadcast.objects.create(
        title=f"{broadcast.title} (Copy)",
        message=broadcast.message,
        channels=list(broadcast.channels or []),
        audience=broadcast.audience,
        status="draft",
        severity=broadcast.severity,
        is_active=False,
        starts_at=timezone.now(),
        ends_at=broadcast.ends_at,
        created_by=actor,
    )


DELETABLE_STATUSES = frozenset({"draft", "scheduled", "sent", "cancelled", "expired"})


@transaction.atomic
def delete_platform_broadcast(broadcast: PlatformBroadcast, *, actor=None) -> dict[str, Any]:
    """Permanently remove a broadcast and its delivery log from the database."""
    if broadcast.status not in DELETABLE_STATUSES:
        raise BroadcastError(f"Broadcasts with status '{broadcast.status}' cannot be deleted.")

    delivery_count = broadcast.deliveries.count()
    payload = {
        "broadcast_id": str(broadcast.id),
        "title": broadcast.title,
        "previous_status": broadcast.status,
        "deliveries_removed": delivery_count,
        "deleted_by": str(actor.id) if actor else None,
    }
    broadcast.delete()
    return payload


def process_scheduled_broadcasts(*, now=None) -> dict[str, int]:
    now = now or timezone.now()
    due = PlatformBroadcast.objects.filter(
        status="scheduled",
        starts_at__lte=now,
    ).order_by("starts_at")

    processed = 0
    for broadcast in due:
        send_platform_broadcast(broadcast, actor=None)
        processed += 1

    return {"processed": processed}