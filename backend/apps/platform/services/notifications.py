"""Platform notification helpers for super-admin workflows."""
from __future__ import annotations

from typing import Any, Optional

from django.utils import timezone

from apps.core.constants import RegistrationType
from apps.platform.models import PlatformNotification
from apps.platform.services.integrations import EmailService
from apps.tenants.models import Tenant


def create_registration_notification(
    tenant: Tenant,
    *,
    registration_type: str,
    plan_name: str = "",
    plan_slug: str = "",
    payment_reference: str = "",
    extra_metadata: Optional[dict[str, Any]] = None,
) -> PlatformNotification:
    """Create or refresh a pending super-admin notification for a school registration."""
    metadata = {
        "registration_type": registration_type,
        "plan_name": plan_name,
        "plan_slug": plan_slug,
        "payment_reference": payment_reference,
        "school_code": tenant.code,
        "admin_email": tenant.email,
        **(extra_metadata or {}),
    }

    type_map = {
        RegistrationType.TRIAL_EMAIL: ("trial_request", "Trial offer claim requested"),
        RegistrationType.TRIAL_PLAN: ("school_registration", "New school — trial plan selected"),
        RegistrationType.PAID: ("payment_attempt", "New school — payment attempted"),
        RegistrationType.PENDING: ("school_registration", "New school registered"),
    }
    notification_type, action_label = type_map.get(
        registration_type,
        ("school_registration", "New school registered"),
    )

    priority = "high" if registration_type == RegistrationType.PAID else "normal"
    title = f"{action_label}: {tenant.name}"

    if registration_type == RegistrationType.TRIAL_EMAIL:
        message = (
            f"{tenant.name} requested a free trial via email. "
            "Review and approve to grant dashboard access."
        )
    elif registration_type == RegistrationType.PAID:
        message = (
            f"{tenant.name} selected the {plan_name or 'paid'} plan and attempted payment. "
            "Activate the account after verifying payment."
        )
    elif plan_name:
        message = (
            f"{tenant.name} selected the {plan_name} plan. "
            "Approve to grant dashboard access for the free trial."
        )
    else:
        message = f"{tenant.name} completed registration and awaits onboarding."

    existing = PlatformNotification.objects.filter(
        tenant=tenant,
        status="pending",
        notification_type=notification_type,
    ).order_by("-created_at").first()

    if existing:
        existing.title = title
        existing.message = message
        existing.priority = priority
        existing.metadata = metadata
        existing.is_read = False
        existing.read_at = None
        existing.save()
        return existing

    return PlatformNotification.objects.create(
        notification_type=notification_type,
        title=title,
        message=message,
        tenant=tenant,
        status="pending",
        priority=priority,
        metadata=metadata,
    )


def approve_school_registration(tenant: Tenant, *, actor) -> Tenant:
    """Verify tenant and resolve pending registration notifications."""
    tenant.verify()

    from apps.accounts.models import User

    User.objects.filter(tenant=tenant, role="school_admin").update(is_email_verified=True)

    now = timezone.now()
    PlatformNotification.objects.filter(tenant=tenant, status="pending").update(
        status="approved",
        action_taken_by=actor,
        action_taken_at=now,
        is_read=True,
        read_at=now,
    )

    admin = User.objects.filter(tenant=tenant, role="school_admin").first()
    if admin:
        from apps.communication.services import create_user_notification

        create_user_notification(
            user=admin,
            tenant=tenant,
            title="Account approved",
            message=f"Your school account for {tenant.name} has been approved. You can now access your dashboard.",
            notification_type="success",
            action_url="/school-admin",
        )
        EmailService.send(
            admin.email,
            "Your Apex Hub school account is approved",
            f"Hello {admin.first_name},\n\nYour school account for {tenant.name} has been approved. "
            "You can now sign in and access your dashboard.",
        )

    return tenant


def get_pending_registration_count() -> int:
    return PlatformNotification.objects.filter(status="pending").count()