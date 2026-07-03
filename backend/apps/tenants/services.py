"""Tenant administration services — plan assignment and permanent deletion."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.apps import apps
from django.db import transaction
from django.utils import timezone

from apps.core.constants import SubscriptionStatus
from apps.tenants.models import Tenant

ACTIVE_SUBSCRIPTION_STATUSES = (
    SubscriptionStatus.TRIAL,
    SubscriptionStatus.ACTIVE,
    SubscriptionStatus.GRACE_PERIOD,
)


@transaction.atomic
def assign_tenant_plan(
    tenant: Tenant,
    plan,
    *,
    billing_cycle: str = "monthly",
    subscription_status: str = SubscriptionStatus.TRIAL,
    period_days: int = 30,
    notes: str = "",
    actor=None,
):
    """Assign or upgrade a school's subscription plan (super-admin or onboarding)."""
    from apps.subscriptions.models import Subscription
    from apps.subscriptions.services import invalidate_tenant_cache

    previous = tenant.active_subscription
    previous_plan = previous.plan.name if previous and previous.plan else None

    tenant.subscriptions.filter(status__in=ACTIVE_SUBSCRIPTION_STATUSES).update(
        status=SubscriptionStatus.CANCELLED,
        cancelled_at=timezone.now(),
    )

    status = subscription_status
    if status not in ACTIVE_SUBSCRIPTION_STATUSES:
        status = SubscriptionStatus.TRIAL

    sub = Subscription.objects.create(
        tenant=tenant,
        plan=plan,
        status=status,
        billing_cycle=billing_cycle,
        notes=notes or "",
    )

    if status == SubscriptionStatus.ACTIVE:
        sub.activate(period_days=period_days)
    elif status == SubscriptionStatus.TRIAL:
        sub.trial_ends_at = timezone.now() + timedelta(days=plan.trial_days or 14)
        sub.save(update_fields=["trial_ends_at", "updated_at"])
    elif status == SubscriptionStatus.GRACE_PERIOD:
        sub.grace_period_ends_at = timezone.now() + timedelta(days=plan.grace_period_days or 7)
        sub.save(update_fields=["grace_period_ends_at", "updated_at"])

    from apps.subscriptions.services import invalidate_plan_cache

    invalidate_tenant_cache(str(tenant.id))
    invalidate_plan_cache(str(plan.id))

    # Super-admin plan assignment activates the school so the admin dashboard unlocks.
    from apps.core.constants import UserRole

    if actor and getattr(actor, "role", None) == UserRole.SUPER_ADMIN:
        if not tenant.is_verified or tenant.status in ("pending", "suspended"):
            tenant.verify()
        elif tenant.status != "active":
            tenant.status = "active"
            tenant.save(update_fields=["status", "updated_at"])

    if actor:
        from apps.audit.models import AuditLog

        AuditLog.objects.create(
            tenant=tenant,
            user=actor,
            action="plan_changed",
            resource_type="Tenant",
            resource_id=str(tenant.id),
            description=f"Plan changed from {previous_plan or 'none'} to {plan.name}",
            changes={
                "previous_plan": previous_plan,
                "new_plan": plan.name,
                "new_plan_slug": plan.slug,
                "billing_cycle": billing_cycle,
                "subscription_status": sub.status,
                "period_days": period_days if status == SubscriptionStatus.ACTIVE else None,
            },
        )

    from apps.subscriptions.services import notify_tenant_subscription_update

    notify_tenant_subscription_update(
        sub,
        event="plan_changed",
        previous_plan_name=previous_plan,
    )

    return sub


def _models_with_tenant_fk() -> list[type]:
    tenant_model = Tenant
    matched: list[type] = []
    for model in apps.get_models():
        if model._meta.abstract:
            continue
        for field in model._meta.fields:
            remote = getattr(field, "remote_field", None)
            if remote and remote.model is tenant_model and field.name == "tenant":
                matched.append(model)
                break
    return matched


def get_tenant_deletion_preview(tenant: Tenant) -> dict[str, Any]:
    """Summarize data that will be removed when a school is permanently deleted."""
    from apps.accounts.models import User
    from apps.subscriptions.models import PaymentTransaction, Subscription

    tenant_id = tenant.id
    category_map: dict[str, list[dict[str, Any]]] = {}
    total_records = 0

    for model in _models_with_tenant_fk():
        if model is Tenant:
            continue
        try:
            count = model.objects.filter(tenant_id=tenant_id).count()
        except Exception:
            continue
        if not count:
            continue
        app_label = model._meta.app_config.verbose_name if model._meta.app_config else model._meta.app_label
        category_map.setdefault(app_label, []).append({
            "key": model._meta.label_lower,
            "label": str(model._meta.verbose_name_plural).title(),
            "count": count,
        })
        total_records += count

    users_count = User.objects.filter(tenant_id=tenant_id).count()
    subscriptions_count = Subscription.objects.filter(tenant_id=tenant_id).count()
    payments_count = PaymentTransaction.objects.filter(tenant_id=tenant_id).count()

    categories = [
        {
            "name": name,
            "items": sorted(items, key=lambda x: x["label"]),
            "total": sum(i["count"] for i in items),
        }
        for name, items in sorted(category_map.items())
    ]

    return {
        "school": {
            "id": str(tenant.id),
            "name": tenant.name,
            "code": tenant.code,
            "status": tenant.status,
            "is_verified": tenant.is_verified,
            "created_at": tenant.created_at.isoformat(),
        },
        "summary": {
            "users": users_count,
            "subscriptions": subscriptions_count,
            "payments": payments_count,
            "tenant_records": total_records,
            "grand_total": total_records + users_count + subscriptions_count + payments_count,
        },
        "categories": categories,
        "warnings": [
            "All students, staff, parents, and user accounts will be permanently removed.",
            "Academic, financial, attendance, and operational records cannot be recovered.",
            "Active subscriptions and billing history for this school will be deleted.",
            "School branding assets (logo, banners) will be removed from storage.",
            "This action is immediate and cannot be undone.",
        ],
        "confirmation_required": tenant.name,
    }


@transaction.atomic
def delete_tenant_permanently(
    tenant: Tenant,
    *,
    actor,
    confirmation_name: str,
) -> dict[str, Any]:
    """Permanently delete a school and all associated data."""
    from apps.audit.models import AuditLog

    if confirmation_name.strip().casefold() != tenant.name.strip().casefold():
        raise ValueError("Confirmation name does not match the school name.")

    preview = get_tenant_deletion_preview(tenant)
    school_name = tenant.name
    school_id = str(tenant.id)
    school_code = tenant.code

    AuditLog.objects.create(
        tenant=None,
        user=actor,
        action="school_deleted",
        resource_type="Tenant",
        resource_id=school_id,
        description=f"Permanently deleted school: {school_name} ({school_code})",
        changes={
            "school_name": school_name,
            "school_code": school_code,
            "deleted_summary": preview["summary"],
        },
    )

    for attr in ("logo", "favicon", "banner", "login_bg"):
        field = getattr(tenant, attr, None)
        if field:
            try:
                field.delete(save=False)
            except Exception:
                pass

    tenant.delete()

    return {
        "deleted": True,
        "school_id": school_id,
        "school_name": school_name,
        "records_removed": preview["summary"]["grand_total"],
    }