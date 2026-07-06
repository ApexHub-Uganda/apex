"""School-level broadcast, announcement, and outbound message delivery."""
from __future__ import annotations

from typing import Any, Iterable

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.communication.models import Announcement, Broadcast, EmailMessage
from apps.communication.services import create_user_notification
from apps.core.constants import UserRole
from apps.core.email_validation import filter_deliverable_emails, validate_deliverable_email
from apps.platform.services.integrations import EmailService, SMSService, WhatsAppService
from apps.staff.models import Staff
from apps.students.models import Parent, Student

User = get_user_model()

VALID_CHANNELS = frozenset({"email", "sms", "whatsapp", "notification"})

CHANNEL_LABELS = {
    "email": "Email",
    "sms": "SMS",
    "whatsapp": "WhatsApp",
    "notification": "In-app",
}

STAFF_ROLES = list({
    UserRole.SCHOOL_ADMIN,
    UserRole.HEAD_TEACHER,
    UserRole.DEPUTY_HEAD_TEACHER,
    UserRole.DIRECTOR_OF_STUDIES,
    UserRole.HEAD_OF_DEPARTMENT,
    UserRole.TEACHER,
    UserRole.BURSAR,
    UserRole.LIBRARIAN,
    UserRole.HR_MANAGER,
    UserRole.TRANSPORT_MANAGER,
    UserRole.HOSTEL_MANAGER,
    UserRole.INVENTORY_MANAGER,
})


class MessagingError(Exception):
    """Raised when a school messaging action cannot be completed."""


def normalize_channels(channels: list[str] | None) -> list[str]:
    if not channels:
        return []
    normalized: list[str] = []
    for channel in channels:
        value = str(channel).strip().lower()
        if value in VALID_CHANNELS and value not in normalized:
            normalized.append(value)
    return normalized


def _unique_emails(addresses: Iterable[str]) -> list[str]:
    return filter_deliverable_emails([
        (address or "").strip() for address in addresses if (address or "").strip()
    ])


def _unique_phones(numbers: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for number in numbers:
        phone = (number or "").strip()
        if phone and phone not in seen:
            seen.add(phone)
            result.append(phone)
    return result


def _staff_queryset(tenant):
    return Staff.objects.filter(tenant=tenant, is_deleted=False, status="active")


def _collect_staff_emails(tenant) -> list[str]:
    emails: list[str] = []
    for staff in _staff_queryset(tenant).select_related("user"):
        if staff.email:
            emails.append(staff.email)
        if staff.personal_email:
            emails.append(staff.personal_email)
        if staff.user and staff.user.email:
            emails.append(staff.user.email)
    emails.extend(
        User.objects.filter(tenant=tenant, is_active=True, role__in=STAFF_ROLES)
        .exclude(email="")
        .values_list("email", flat=True),
    )
    return emails


def _collect_parent_emails(tenant) -> list[str]:
    emails: list[str] = []
    for parent in Parent.objects.filter(tenant=tenant, is_deleted=False).select_related("user"):
        if parent.email:
            emails.append(parent.email)
        if parent.alternate_email:
            emails.append(parent.alternate_email)
        if parent.user and parent.user.email:
            emails.append(parent.user.email)
    emails.extend(
        User.objects.filter(tenant=tenant, is_active=True, role=UserRole.PARENT)
        .exclude(email="")
        .values_list("email", flat=True),
    )
    return emails


def _collect_student_emails(tenant) -> list[str]:
    emails: list[str] = []
    for student in Student.objects.filter(tenant=tenant, is_deleted=False).select_related("user"):
        if student.email:
            emails.append(student.email)
        if student.alternate_email:
            emails.append(student.alternate_email)
        if student.user and student.user.email:
            emails.append(student.user.email)
    return emails


def resolve_tenant_emails(*, tenant, audience: str) -> list[str]:
    """Resolve distinct email addresses for a school audience segment."""
    emails: list[str] = []

    if audience in ("all", "staff"):
        emails.extend(_collect_staff_emails(tenant))

    if audience in ("all", "parents"):
        emails.extend(_collect_parent_emails(tenant))

    if audience in ("all", "students"):
        emails.extend(_collect_student_emails(tenant))

    return _unique_emails(emails)


def resolve_tenant_phones(*, tenant, audience: str) -> list[str]:
    phones: list[str] = []

    if audience in ("all", "staff"):
        phones.extend(
            _staff_queryset(tenant).exclude(phone="").values_list("phone", flat=True),
        )
        phones.extend(
            User.objects.filter(tenant=tenant, is_active=True, role__in=STAFF_ROLES)
            .exclude(phone="")
            .values_list("phone", flat=True),
        )

    if audience in ("all", "parents"):
        phones.extend(
            Parent.objects.filter(tenant=tenant, is_deleted=False)
            .exclude(phone="")
            .values_list("phone", flat=True),
        )

    if audience in ("all", "students"):
        phones.extend(
            Student.objects.filter(tenant=tenant, is_deleted=False)
            .exclude(phone="")
            .values_list("phone", flat=True),
        )

    return _unique_phones(phones)


def resolve_tenant_users(*, tenant, audience: str):
    if audience == "staff":
        return User.objects.filter(
            tenant=tenant, is_active=True, role__in=STAFF_ROLES,
        )
    if audience == "parents":
        return User.objects.filter(tenant=tenant, is_active=True, role=UserRole.PARENT)
    if audience == "students":
        return User.objects.filter(tenant=tenant, is_active=True, role=UserRole.STUDENT)
    return User.objects.filter(tenant=tenant, is_active=True).exclude(role=UserRole.SUPER_ADMIN)


def _priority_to_notification_type(priority: str) -> str:
    if priority == "urgent":
        return "error"
    if priority == "high":
        return "warning"
    return "info"


def _format_email_body(*, tenant, title: str, body: str) -> str:
    school_name = getattr(tenant, "name", "Your School")
    footer = (
        f"\n\n—\n{school_name}\n"
        "Sent via Apex Hub School Communication"
    )
    return f"{title}\n{'=' * len(title)}\n\n{body.strip()}{footer}"


def _dispatch_email(
    *,
    tenant,
    recipients: list[str],
    subject: str,
    body: str,
    require_delivery: bool = False,
) -> dict[str, Any]:
    if not recipients:
        result = {
            "sent": 0,
            "failed": 0,
            "skipped": 1,
            "recipient_count": 0,
            "error": (
                "No deliverable email addresses found for the selected audience. "
                "Add real staff/parent/student emails — demo addresses like staff1@school.ug are rejected."
            ),
        }
        if require_delivery:
            raise MessagingError(result["error"])
        return result

    formatted_body = _format_email_body(tenant=tenant, title=subject, body=body)
    mail_result = EmailService.send(
        recipients,
        subject,
        formatted_body,
        tenant=tenant,
    )
    sent = int(mail_result.metadata.get("sent_count", 0))
    failed = int(mail_result.metadata.get("failed_count", 0))
    if sent == 0 and failed == 0 and not mail_result.success:
        failed = len(recipients)

    result = {
        "sent": sent,
        "failed": failed,
        "skipped": 0,
        "recipient_count": len(recipients),
        "recipients": recipients[:10],
        "delivery_message": mail_result.message,
    }
    if require_delivery and sent == 0:
        raise MessagingError(
            mail_result.message or f"Email delivery failed for all {len(recipients)} recipient(s).",
        )
    if require_delivery and failed > 0 and sent == 0:
        raise MessagingError(mail_result.message)
    return result


def _dispatch_sms(*, tenant, recipients: list[str], body: str) -> dict[str, int]:
    sent = failed = skipped = 0
    for phone in recipients:
        result = SMSService.send(phone, body, tenant=tenant)
        if result.success:
            sent += 1
        else:
            failed += 1
    if not recipients:
        skipped = 1
    return {"sent": sent, "failed": failed, "skipped": skipped}


def _dispatch_whatsapp(*, tenant, recipients: list[str], body: str) -> dict[str, int]:
    sent = failed = skipped = 0
    for phone in recipients:
        result = WhatsAppService.send(phone, body, tenant=tenant)
        if result.success:
            sent += 1
        else:
            failed += 1
    if not recipients:
        skipped = 1
    return {"sent": sent, "failed": failed, "skipped": skipped}


def _dispatch_notifications(
    *,
    tenant,
    audience: str,
    title: str,
    body: str,
    notification_type: str = "info",
    metadata: dict[str, Any] | None = None,
) -> dict[str, int]:
    users = list(resolve_tenant_users(tenant=tenant, audience=audience))
    for user in users:
        create_user_notification(
            user=user,
            tenant=tenant,
            title=title,
            message=body,
            notification_type=notification_type,
            action_url="/school-admin/communication",
            metadata=metadata or {},
        )
    return {"sent": len(users), "failed": 0, "skipped": 0}


def _build_delivery_summary(*, channels: list[str], channel_results: dict) -> list[str]:
    warnings: list[str] = []
    if "email" in channels:
        email_stats = channel_results.get("email", {})
        if email_stats.get("skipped"):
            warnings.append(
                "Email channel was selected but no email addresses were found. "
                "Add emails to staff, parent, or student records.",
            )
        elif email_stats.get("sent", 0) == 0 and email_stats.get("recipient_count", 0) > 0:
            warnings.append(email_stats.get("delivery_message") or "Email delivery failed for all recipients.")
        elif email_stats.get("failed", 0) > 0:
            warnings.append(
                f"Email delivered to {email_stats.get('sent', 0)} of "
                f"{email_stats.get('recipient_count', 0)} recipient(s).",
            )
    return warnings


@transaction.atomic
def send_school_broadcast(broadcast: Broadcast, *, actor=None) -> dict[str, Any]:
    if broadcast.status not in ("draft", "scheduled"):
        raise MessagingError("Only draft or scheduled broadcasts can be sent.")

    channels = normalize_channels(broadcast.channels)
    if not channels:
        raise MessagingError("Select at least one delivery channel (email, SMS, or WhatsApp).")

    tenant = broadcast.tenant
    audience = "all"
    emails = resolve_tenant_emails(tenant=tenant, audience=audience) if "email" in channels else []
    phones = resolve_tenant_phones(tenant=tenant, audience=audience) if {"sms", "whatsapp"} & set(channels) else []

    delivered = failed = skipped = 0
    channel_results: dict[str, dict[str, Any]] = {}

    for channel in channels:
        if channel == "email":
            stats = _dispatch_email(
                tenant=tenant,
                recipients=emails,
                subject=broadcast.title,
                body=broadcast.message,
                require_delivery=True,
            )
        elif channel == "sms":
            stats = _dispatch_sms(tenant=tenant, recipients=phones, body=broadcast.message)
        elif channel == "whatsapp":
            stats = _dispatch_whatsapp(tenant=tenant, recipients=phones, body=broadcast.message)
        else:
            stats = _dispatch_notifications(
                tenant=tenant,
                audience=audience,
                title=broadcast.title,
                body=broadcast.message,
                metadata={"broadcast_id": str(broadcast.id), "channels": channels},
            )

        channel_results[channel] = stats
        delivered += stats["sent"]
        failed += stats["failed"]
        skipped += stats["skipped"]

    now = timezone.now()
    broadcast.status = "sent"
    broadcast.sent_at = now
    broadcast.recipient_count = max(len(emails), len(phones), 0)
    broadcast.save(update_fields=["status", "sent_at", "recipient_count", "updated_at"])

    warnings = _build_delivery_summary(channels=channels, channel_results=channel_results)
    return {
        "broadcast_id": str(broadcast.id),
        "status": broadcast.status,
        "sent_at": broadcast.sent_at.isoformat(),
        "channels": channels,
        "recipient_count": broadcast.recipient_count,
        "delivered_count": delivered,
        "failed_count": failed,
        "skipped_count": skipped,
        "channel_results": channel_results,
        "warnings": warnings,
    }


@transaction.atomic
def publish_announcement(
    announcement: Announcement,
    *,
    channels: list[str] | None = None,
    actor=None,
) -> dict[str, Any]:
    if announcement.is_published:
        raise MessagingError("This announcement has already been published.")

    selected = normalize_channels(channels or announcement.channels)
    if not selected:
        selected = ["email", "notification"]

    tenant = announcement.tenant
    audience = announcement.target_audience
    emails = resolve_tenant_emails(tenant=tenant, audience=audience) if "email" in selected else []
    phones = resolve_tenant_phones(tenant=tenant, audience=audience) if {"sms", "whatsapp"} & set(selected) else []

    delivered = failed = skipped = 0
    channel_results: dict[str, dict[str, Any]] = {}
    notification_type = _priority_to_notification_type(announcement.priority)

    for channel in selected:
        if channel == "email":
            stats = _dispatch_email(
                tenant=tenant,
                recipients=emails,
                subject=announcement.title,
                body=announcement.content,
                require_delivery=True,
            )
        elif channel == "sms":
            stats = _dispatch_sms(tenant=tenant, recipients=phones, body=announcement.content)
        elif channel == "whatsapp":
            stats = _dispatch_whatsapp(tenant=tenant, recipients=phones, body=announcement.content)
        else:
            stats = _dispatch_notifications(
                tenant=tenant,
                audience=audience,
                title=announcement.title,
                body=announcement.content,
                notification_type=notification_type,
                metadata={
                    "announcement_id": str(announcement.id),
                    "priority": announcement.priority,
                    "channels": selected,
                },
            )

        channel_results[channel] = stats
        delivered += stats["sent"]
        failed += stats["failed"]
        skipped += stats["skipped"]

    now = timezone.now()
    announcement.is_published = True
    announcement.publish_date = now
    announcement.channels = selected
    announcement.save(update_fields=["is_published", "publish_date", "channels", "updated_at"])

    warnings = _build_delivery_summary(channels=selected, channel_results=channel_results)
    email_stats = channel_results.get("email", {})
    message = "Announcement published."
    if "email" in selected and email_stats.get("sent", 0) > 0:
        message = f"Announcement published. Email sent to {email_stats['sent']} recipient(s)."

    return {
        "announcement_id": str(announcement.id),
        "is_published": True,
        "publish_date": announcement.publish_date.isoformat(),
        "channels": selected,
        "audience": audience,
        "delivered_count": delivered,
        "failed_count": failed,
        "skipped_count": skipped,
        "channel_results": channel_results,
        "email_recipients": email_stats.get("recipient_count", len(emails)),
        "email_sent": email_stats.get("sent", 0),
        "warnings": warnings,
        "message": message,
    }


def send_email_message(email_message: EmailMessage) -> dict[str, Any]:
    if email_message.status == "sent":
        raise MessagingError("This email has already been sent.")

    tenant = email_message.tenant
    formatted_body = _format_email_body(
        tenant=tenant,
        title=email_message.subject,
        body=email_message.body,
    )
    result = EmailService.send(
        email_message.recipient_email,
        email_message.subject,
        formatted_body,
        tenant=tenant,
        log_attempt=False,
    )

    now = timezone.now()
    email_message.status = "sent" if result.success else "failed"
    email_message.sent_at = now if result.success else None
    email_message.save(update_fields=["status", "sent_at", "updated_at"])

    if not result.success:
        raise MessagingError(result.message or "Email delivery failed.")

    return {
        "email_id": str(email_message.id),
        "status": email_message.status,
        "sent_at": email_message.sent_at.isoformat() if email_message.sent_at else None,
        "success": result.success,
        "message": result.message,
        "metadata": result.metadata,
    }


def soft_delete_tenant_messages(*, tenant, model, user=None) -> int:
    """Soft-delete all messages of a model for a tenant."""
    qs = model.all_objects.filter(tenant=tenant, is_deleted=False)
    count = qs.count()
    now = timezone.now()
    qs.update(is_deleted=True, updated_at=now, updated_by=user)
    return count