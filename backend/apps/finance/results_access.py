"""Fee-clearance gate for parent/sponsor access to learner academic results."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.academics.models import Class
from apps.academics.singleton import get_active_term
from apps.finance.models import ClassResultsAccessPolicy, ResultsAccessPolicy, StudentFeeBalance
from apps.tenants.role_permissions import user_is_school_admin

DEFAULT_CLEARED_PERCENT = Decimal("100.00")


def _clamp_percent(value) -> Decimal:
    try:
        pct = Decimal(str(value))
    except Exception as exc:
        raise ValidationError({"cleared_percent": "Enter a valid percentage."}) from exc
    if pct < 0 or pct > 100:
        raise ValidationError({"cleared_percent": "Percentage must be between 0 and 100."})
    return pct.quantize(Decimal("0.01"))


def get_or_create_results_policy(tenant) -> ResultsAccessPolicy:
    policy = (
        ResultsAccessPolicy.objects.filter(tenant=tenant, is_deleted=False)
        .order_by("-updated_at")
        .first()
    )
    if policy:
        return policy
    return ResultsAccessPolicy.objects.create(
        tenant=tenant,
        default_cleared_percent=DEFAULT_CLEARED_PERCENT,
        is_active=True,
    )


def get_required_cleared_percent(tenant, school_class=None) -> Decimal:
    """Resolve class override → school default → 100%."""
    if school_class is not None:
        override = ClassResultsAccessPolicy.objects.filter(
            tenant=tenant,
            school_class=school_class,
            is_deleted=False,
            is_active=True,
        ).first()
        if override is not None:
            return Decimal(override.cleared_percent)

    policy = (
        ResultsAccessPolicy.objects.filter(tenant=tenant, is_deleted=False, is_active=True)
        .order_by("-updated_at")
        .first()
    )
    if policy is not None:
        return Decimal(policy.default_cleared_percent)
    return DEFAULT_CLEARED_PERCENT


def compute_student_fee_clearance(*, tenant, student, term=None) -> dict[str, Any]:
    """
    Fee clearance for a learner for a single academic term only.

    No multi-term aggregate fallback:
    - Uses the provided term, or the school's active term.
    - If there is no active/selected term → results locked.
    - Only balances for that term are counted.
    - If the term has no fee balance rows (nothing billed yet) → treated as 100% cleared.
    """
    active_term = term or get_active_term(tenant)
    required = get_required_cleared_percent(tenant, getattr(student, "school_class", None))

    if active_term is None:
        return {
            "student_id": str(student.id),
            "term_id": None,
            "term_name": None,
            "total_billed": "0",
            "total_paid": "0",
            "balance": "0",
            "cleared_percent": "0.00",
            "required_percent": str(required),
            "results_allowed": False,
            "scope": "no_active_term",
            "message": (
                "Results are locked because there is no active academic term. "
                "Fee clearance is evaluated per term."
            ),
        }

    term_qs = StudentFeeBalance.objects.filter(
        tenant=tenant,
        student=student,
        term=active_term,
        is_deleted=False,
    )

    totals = term_qs.aggregate(
        billed=Sum("total_billed"),
        paid=Sum("total_paid"),
        balance=Sum("balance"),
    )
    total_billed = Decimal(totals["billed"] or 0)
    total_paid = Decimal(totals["paid"] or 0)
    balance = Decimal(totals["balance"] or 0)

    # Nothing billed for this term yet → nothing outstanding for results gate.
    if not term_qs.exists() or total_billed <= 0:
        cleared_percent = Decimal("100.00")
    else:
        cleared_percent = (total_paid / total_billed * Decimal("100")).quantize(Decimal("0.01"))
        if cleared_percent > 100:
            cleared_percent = Decimal("100.00")

    allowed = cleared_percent >= required

    return {
        "student_id": str(student.id),
        "term_id": str(active_term.id),
        "term_name": active_term.name,
        "total_billed": str(total_billed),
        "total_paid": str(total_paid),
        "balance": str(balance),
        "cleared_percent": str(cleared_percent),
        "required_percent": str(required),
        "results_allowed": allowed,
        "scope": "term",
        "message": (
            None
            if allowed
            else (
                f"Results for {active_term.name} are locked until fees are at least "
                f"{required}% cleared for this term. Current clearance: {cleared_percent}%."
            )
        ),
    }


def assert_parent_results_access(*, tenant, student) -> dict[str, Any]:
    clearance = compute_student_fee_clearance(tenant=tenant, student=student)
    if not clearance["results_allowed"]:
        raise PermissionDenied(
            clearance["message"]
            or "Results are not available until outstanding fees meet the school clearance policy.",
        )
    return clearance


def assert_can_manage_results_policy(user) -> None:
    if user_is_school_admin(user):
        return
    role = getattr(user, "role", "")
    from apps.core.constants import UserRole, normalize_role

    if normalize_role(role) in (UserRole.BURSAR, UserRole.ASSISTANT_BURSAR, UserRole.FINANCE_OFFICER):
        return
    raise PermissionDenied("Only school admins and bursary staff can adjust results access policy.")


@transaction.atomic
def update_school_results_policy(tenant, *, actor, default_cleared_percent, is_active=True, notes="") -> ResultsAccessPolicy:
    assert_can_manage_results_policy(actor)
    policy = get_or_create_results_policy(tenant)
    policy.default_cleared_percent = _clamp_percent(default_cleared_percent)
    policy.is_active = bool(is_active)
    policy.notes = notes or ""
    policy.updated_by = actor
    policy.save()
    return policy


@transaction.atomic
def upsert_class_results_policy(
    tenant,
    *,
    actor,
    school_class_id,
    cleared_percent,
    is_active=True,
    notes="",
) -> ClassResultsAccessPolicy:
    assert_can_manage_results_policy(actor)
    school_class = Class.objects.filter(tenant=tenant, pk=school_class_id, is_deleted=False).first()
    if school_class is None:
        raise ValidationError({"school_class": "Class not found."})

    policy = ClassResultsAccessPolicy.objects.filter(
        school_class=school_class, is_deleted=False,
    ).first()
    if policy is None:
        policy = ClassResultsAccessPolicy(
            tenant=tenant,
            school_class=school_class,
            created_by=actor,
        )
    policy.tenant = tenant
    policy.cleared_percent = _clamp_percent(cleared_percent)
    policy.is_active = bool(is_active)
    policy.notes = notes or ""
    policy.updated_by = actor
    policy.is_deleted = False
    policy.save()
    return policy


def serialize_school_policy(policy: ResultsAccessPolicy) -> dict[str, Any]:
    return {
        "id": str(policy.id),
        "default_cleared_percent": str(policy.default_cleared_percent),
        "is_active": policy.is_active,
        "notes": policy.notes,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }


def list_class_policies(tenant) -> list[dict[str, Any]]:
    school_default = get_required_cleared_percent(tenant, None)
    classes = Class.objects.filter(tenant=tenant, is_deleted=False).order_by("name")
    overrides = {
        str(p.school_class_id): p
        for p in ClassResultsAccessPolicy.objects.filter(tenant=tenant, is_deleted=False)
    }
    rows = []
    for school_class in classes:
        override = overrides.get(str(school_class.id))
        rows.append({
            "school_class_id": str(school_class.id),
            "school_class_name": school_class.name,
            "school_class_code": school_class.code,
            "cleared_percent": str(override.cleared_percent) if override and override.is_active else str(school_default),
            "is_override": bool(override and override.is_active),
            "is_active": bool(override.is_active) if override else False,
            "notes": override.notes if override else "",
            "policy_id": str(override.id) if override else None,
            "school_default_percent": str(school_default),
        })
    return rows
