"""Safe plan deletion with subscription reassignment."""
from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.subscriptions.models import Plan, Subscription
from apps.subscriptions.services import invalidate_plan_cache, invalidate_tenant_cache
from apps.tenants.services import ACTIVE_SUBSCRIPTION_STATUSES


class PlanDeletionError(Exception):
    """Raised when a plan cannot be deleted safely."""

    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def get_reassign_plan_candidates(exclude_plan_id) -> list[Plan]:
    return list(
        Plan.objects.filter(is_active=True)
        .exclude(pk=exclude_plan_id)
        .order_by("sort_order", "price_monthly", "name"),
    )


def get_plan_deletion_preview(plan: Plan) -> dict[str, Any]:
    subscriptions = plan.subscriptions.select_related("tenant").order_by("-updated_at")
    subscription_count = subscriptions.count()
    active_count = subscriptions.filter(status__in=ACTIVE_SUBSCRIPTION_STATUSES).count()
    candidates = get_reassign_plan_candidates(plan.id)

    schools: list[dict[str, str]] = []
    seen_tenant_ids: set[str] = set()
    for sub in subscriptions[:12]:
        tenant_id = str(sub.tenant_id)
        if tenant_id in seen_tenant_ids:
            continue
        seen_tenant_ids.add(tenant_id)
        schools.append({
            "tenant_id": tenant_id,
            "school": sub.tenant.name,
            "status": sub.status,
        })
        if len(schools) >= 8:
            break

    return {
        "plan_id": str(plan.id),
        "plan_name": plan.name,
        "plan_slug": plan.slug,
        "subscription_count": subscription_count,
        "active_subscription_count": active_count,
        "can_delete_immediately": subscription_count == 0,
        "requires_reassign": subscription_count > 0,
        "reassign_options": [
            {
                "id": str(candidate.id),
                "name": candidate.name,
                "slug": candidate.slug,
                "subscriber_count": candidate.subscriptions.filter(
                    status__in=ACTIVE_SUBSCRIPTION_STATUSES,
                ).count(),
            }
            for candidate in candidates
        ],
        "schools": schools,
        "suggested_reassign_plan_id": str(candidates[0].id) if candidates else None,
    }


@transaction.atomic
def delete_plan_safely(
    plan: Plan,
    *,
    reassign_to: Plan | None = None,
    actor=None,
) -> dict[str, Any]:
    subscription_qs = plan.subscriptions.select_related("tenant")
    subscription_count = subscription_qs.count()

    if subscription_count:
        if reassign_to is None:
            preview = get_plan_deletion_preview(plan)
            raise PlanDeletionError(
                "reassign_required",
                (
                    f'"{plan.name}" is used by {subscription_count} subscription(s). '
                    "Choose another plan to move those schools to before deleting."
                ),
                details={
                    "subscription_count": subscription_count,
                    "reassign_options": preview["reassign_options"],
                    "suggested_reassign_plan_id": preview["suggested_reassign_plan_id"],
                },
            )

        if reassign_to.pk == plan.pk:
            raise PlanDeletionError(
                "invalid_reassign_target",
                "Choose a different plan to move schools to.",
            )

        if not reassign_to.is_active:
            raise PlanDeletionError(
                "inactive_reassign_target",
                f'"{reassign_to.name}" is inactive. Select an active replacement plan.',
            )

        affected_subscriptions = list(subscription_qs)
        tenant_ids = {str(sub.tenant_id) for sub in affected_subscriptions}
        previous_plan_name = plan.name

        subscription_qs.update(plan=reassign_to, updated_at=timezone.now())

        for tenant_id in tenant_ids:
            invalidate_tenant_cache(tenant_id)

        invalidate_plan_cache(str(plan.id))
        invalidate_plan_cache(str(reassign_to.id))

        from apps.subscriptions.services import notify_tenant_subscription_update

        notified_tenants: set[str] = set()
        for sub in affected_subscriptions:
            sub.plan = reassign_to
            tenant_id = str(sub.tenant_id)
            if tenant_id in notified_tenants:
                continue
            if sub.status in ACTIVE_SUBSCRIPTION_STATUSES:
                notify_tenant_subscription_update(
                    sub,
                    event="plan_changed",
                    previous_plan_name=previous_plan_name,
                )
                notified_tenants.add(tenant_id)
    else:
        reassign_to = None
        tenant_ids = set()

    deleted_plan_id = str(plan.id)
    deleted_plan_name = plan.name
    deleted_plan_slug = plan.slug
    reassign_name = reassign_to.name if reassign_to else None
    reassign_id = str(reassign_to.id) if reassign_to else None

    plan.delete()

    if actor:
        from apps.audit.models import AuditLog

        AuditLog.objects.create(
            tenant=None,
            user=actor,
            action="plan_deleted",
            resource_type="Plan",
            resource_id=deleted_plan_id,
            description=(
                f'Deleted plan "{deleted_plan_name}"'
                + (
                    f' and moved {subscription_count} subscription(s) to "{reassign_name}"'
                    if subscription_count
                    else ""
                )
            ),
            changes={
                "deleted_plan": deleted_plan_name,
                "deleted_plan_slug": deleted_plan_slug,
                "subscriptions_reassigned": subscription_count,
                "reassigned_to_plan": reassign_name,
                "reassigned_to_plan_id": reassign_id,
                "affected_tenant_count": len(tenant_ids),
            },
        )

    return {
        "deleted_plan_id": deleted_plan_id,
        "deleted_plan_name": deleted_plan_name,
        "subscriptions_reassigned": subscription_count,
        "reassigned_to_plan_id": reassign_id,
        "reassigned_to_plan_name": reassign_name,
        "affected_tenant_count": len(tenant_ids),
    }