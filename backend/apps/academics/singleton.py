"""Single active academic year / term enforcement per school."""
from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.academics.models import AcademicYear, Term


def _today():
    return timezone.now().date()


def record_is_active(*, end_date, is_current: bool = False) -> bool:
    """True while the period has not ended or is explicitly marked current."""
    if is_current:
        return True
    return bool(end_date and end_date >= _today())


def get_active_academic_year(tenant):
    if tenant is None:
        return None
    today = _today()
    return (
        AcademicYear.objects.filter(tenant=tenant, is_deleted=False)
        .filter(Q(is_current=True) | Q(end_date__gte=today))
        .order_by("-is_current", "-start_date")
        .first()
    )


def get_active_term(tenant, *, academic_year=None):
    if tenant is None:
        return None
    today = _today()
    qs = Term.objects.filter(tenant=tenant, is_deleted=False).select_related("academic_year")
    if academic_year is not None:
        qs = qs.filter(academic_year=academic_year)
    return (
        qs.filter(Q(is_current=True) | Q(end_date__gte=today))
        .order_by("-is_current", "-start_date")
        .first()
    )


def academic_year_creation_blocked(tenant) -> tuple[bool, AcademicYear | None]:
    active = get_active_academic_year(tenant)
    if active is None:
        return False, None
    return True, active


def term_creation_blocked(tenant) -> tuple[bool, Term | None]:
    active = get_active_term(tenant)
    if active is None:
        return False, None
    return True, active


def assert_can_create_academic_year(tenant) -> None:
    blocked, active = academic_year_creation_blocked(tenant)
    if not blocked:
        return
    raise ValidationError({
        "non_field_errors": [
            f"Academic year “{active.name}” is still active "
            f"(until {active.end_date:%d %b %Y}). "
            "Close or end the current year before creating a new one.",
        ],
        "active_record_id": str(active.id),
    })


def assert_can_create_term(tenant) -> None:
    blocked, active = term_creation_blocked(tenant)
    if not blocked:
        return
    year_label = active.academic_year.name if active.academic_year_id else "the current year"
    raise ValidationError({
        "non_field_errors": [
            f"Term “{active.name}” ({year_label}) is still active "
            f"(until {active.end_date:%d %b %Y}). "
            "Close the current term before creating a new one.",
        ],
        "active_record_id": str(active.id),
    })


def assert_active_term_for_timetable(tenant) -> Term:
    active = get_active_term(tenant)
    if active is None:
        raise ValidationError({
            "non_field_errors": [
                "No active academic term. Create or activate a term before adding timetable entries.",
            ],
        })
    return active


def build_singleton_list_meta(*, tenant, kind: str) -> dict:
    if kind == "academic_year":
        active = get_active_academic_year(tenant)
        blocked, _ = academic_year_creation_blocked(tenant)
        label = "academic year"
    elif kind == "term":
        active = get_active_term(tenant)
        blocked, _ = term_creation_blocked(tenant)
        label = "term"
    else:
        return {}

    if active is None:
        return {
            "active_record": None,
            "creation_locked": False,
            "lock_reason": "",
            "singleton_type": kind,
        }

    if kind == "term":
        active_payload = {
            "id": str(active.id),
            "name": active.name,
            "academic_year": str(active.academic_year_id),
            "academic_year_name": active.academic_year.name,
            "term_number": active.term_number,
            "start_date": active.start_date.isoformat(),
            "end_date": active.end_date.isoformat(),
            "is_current": active.is_current,
        }
    else:
        active_payload = {
            "id": str(active.id),
            "name": active.name,
            "start_date": active.start_date.isoformat(),
            "end_date": active.end_date.isoformat(),
            "is_current": active.is_current,
        }

    lock_reason = ""
    if blocked:
        lock_reason = (
            f"The current {label} “{active.name}” is still in progress. "
            f"A new {label} can be created after {active.end_date:%d %b %Y}."
        )

    return {
        "active_record": active_payload,
        "creation_locked": blocked,
        "lock_reason": lock_reason,
        "singleton_type": kind,
    }