"""Single active academic year / term / exam session enforcement per school."""
from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.academics.models import AcademicYear, Term
from apps.examinations.constants import EXAMINATION_SESSION_ACTIVE, EXAMINATION_SESSION_CLOSED


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


def get_active_examination_session(tenant):
    """Return the school's open exam period (active status, or planned/active not yet ended)."""
    if tenant is None:
        return None
    from apps.examinations.models import ExaminationSession

    today = _today()
    return (
        ExaminationSession.objects.filter(tenant=tenant, is_deleted=False)
        .exclude(status=EXAMINATION_SESSION_CLOSED)
        .filter(Q(status=EXAMINATION_SESSION_ACTIVE) | Q(end_date__gte=today))
        .select_related("academic_year", "term")
        .order_by(
            # Prefer explicitly active sessions, then latest start.
            models_order_active_first(),
            "-start_date",
        )
        .first()
    )


def models_order_active_first():
    from django.db.models import Case, IntegerField, Value, When

    return Case(
        When(status=EXAMINATION_SESSION_ACTIVE, then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
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


def examination_session_creation_blocked(tenant) -> tuple[bool, object | None]:
    active = get_active_examination_session(tenant)
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
            "Close or end the current year before creating a new one. "
            "School admins can edit the current year to close it early.",
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
            "Close the current term before creating a new one. "
            "School admins can edit the current term to close it early.",
        ],
        "active_record_id": str(active.id),
    })


def assert_can_create_examination_session(tenant) -> None:
    blocked, active = examination_session_creation_blocked(tenant)
    if not blocked:
        return
    raise ValidationError({
        "non_field_errors": [
            f"Exam period “{active.name}” is still active "
            f"(until {active.end_date:%d %b %Y}, status: {active.status}). "
            "Close or end the current exam period before creating a new one. "
            "School admins can edit the current exam period to close it early.",
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
    elif kind in ("examination_session", "exam_period", "exam_session"):
        kind = "examination_session"
        active = get_active_examination_session(tenant)
        blocked, _ = examination_session_creation_blocked(tenant)
        label = "exam period"
    else:
        return {}

    if active is None:
        return {
            "active_record": None,
            "creation_locked": False,
            "lock_reason": "",
            "singleton_type": kind,
            "school_admin_can_manage": True,
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
    elif kind == "examination_session":
        active_payload = {
            "id": str(active.id),
            "name": active.name,
            "academic_year": str(active.academic_year_id) if active.academic_year_id else None,
            "academic_year_name": active.academic_year.name if active.academic_year_id else "",
            "term": str(active.term_id) if active.term_id else None,
            "term_name": active.term.name if active.term_id else "",
            "start_date": active.start_date.isoformat(),
            "end_date": active.end_date.isoformat(),
            "status": active.status,
            "is_current": active.status == EXAMINATION_SESSION_ACTIVE,
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
            f"A new {label} can be created after {active.end_date:%d %b %Y}, "
            "or a school admin can edit/close the current record."
        )

    return {
        "active_record": active_payload,
        "creation_locked": blocked,
        "lock_reason": lock_reason,
        "singleton_type": kind,
        "school_admin_can_manage": True,
    }
