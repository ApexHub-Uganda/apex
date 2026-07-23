"""Marks entry and grade calculation option scoping.

Write options are always limited to the caller's teaching assignments.
School admin and DoS never receive unrestricted marks-write options.
"""
from __future__ import annotations

from uuid import UUID

from django.db.models import Q

from apps.academics.models import Class, Subject, Term
from apps.academics.scoping import (
    get_academic_context,
    results_role_capabilities,
    user_is_subject_marks_teacher,
)
from apps.academics.singleton import (
    get_active_academic_year,
    get_active_examination_session,
    get_active_term,
)
from apps.examinations.constants import (
    EXAM_LIFECYCLE_ARCHIVED,
    EXAM_LIFECYCLE_PUBLISHED,
    EXAMINATION_SESSION_ACTIVE,
    MARKS_STATUS_DRAFT,
)
from apps.examinations.reference import _option


def resolve_current_term(tenant):
    """Prefer the term flagged is_current; fall back to calendar-active term."""
    current = (
        Term.objects.filter(tenant=tenant, is_deleted=False, is_current=True)
        .select_related("academic_year")
        .order_by("-start_date")
        .first()
    )
    return current or get_active_term(tenant)


def resolve_current_academic_year(tenant):
    active_term = resolve_current_term(tenant)
    if active_term is not None and active_term.academic_year_id:
        return active_term.academic_year
    return get_active_academic_year(tenant)


def resolve_active_exam_period(tenant):
    """Open exam period (ExaminationSession), if any."""
    return get_active_examination_session(tenant)


def marks_scope_meta(tenant, user) -> dict:
    active_term = resolve_current_term(tenant)
    active_year = resolve_current_academic_year(tenant)
    exam_period = resolve_active_exam_period(tenant)
    can_enter = user_is_subject_marks_teacher(user)
    caps = results_role_capabilities(user)
    period_payload = None
    if exam_period is not None:
        period_payload = {
            "id": str(exam_period.id),
            "name": exam_period.name,
            "status": exam_period.status,
            "start_date": exam_period.start_date.isoformat() if exam_period.start_date else None,
            "end_date": exam_period.end_date.isoformat() if exam_period.end_date else None,
            "term_id": str(exam_period.term_id) if exam_period.term_id else None,
            "term_name": exam_period.term.name if exam_period.term_id else None,
            "is_active": exam_period.status == EXAMINATION_SESSION_ACTIVE,
        }
    return {
        # Always assignment-scoped for marks write (admin/DoS cannot enter marks)
        "is_unrestricted": False,
        "term_locked": True,
        "current_term_id": str(active_term.id) if active_term else None,
        "current_term_name": active_term.name if active_term else None,
        "current_academic_year_id": str(active_year.id) if active_year else None,
        "current_academic_year_name": active_year.name if active_year else None,
        "active_exam_period": period_payload,
        "has_active_exam_period": period_payload is not None,
        "uses_teaching_assignments": True,
        "can_enter_marks": can_enter,
        "can_apply_grading": can_enter,
        "can_print_report_cards": caps["can_print_report_cards"],
        "can_edit_class_teacher_remarks": caps["can_edit_class_teacher_remarks"],
        "capabilities": caps,
        "message": (
            None if can_enter
            else "Marks entry is only available for classes and subjects assigned to you."
        ),
        "setup_hint": (
            None if period_payload
            else "Open an Exam Session (exam period) under Examinations → Exam Sessions so teachers can enter marks."
        ),
    }


def _normalize_uuid(value):
    if value in (None, "", "none", "null"):
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def user_teaches_pair(user, *, subject_id, school_class_id) -> bool:
    """True when the user has a teaching assignment for this subject–class pair."""
    ctx = get_academic_context(user)
    if ctx is None or not ctx.teaching_pairs:
        return False
    sid = _normalize_uuid(subject_id)
    cid = _normalize_uuid(school_class_id)
    if sid is None or cid is None:
        return False
    return (sid, cid) in ctx.teaching_pairs


def marks_subject_options(tenant, user) -> list[dict]:
    """Subjects the user may enter marks for (teaching pairs only)."""
    ctx = get_academic_context(user)
    if ctx is None or not ctx.teaching_pairs:
        return []

    subject_ids = {subject_id for subject_id, _class_id in ctx.teaching_pairs}
    if not subject_ids:
        return []

    rows = (
        Subject.objects.filter(tenant=tenant, id__in=subject_ids, is_deleted=False)
        .prefetch_related("papers")
        .order_by("name")
    )
    return [
        {
            **_option(s.id, f"{s.name} ({s.code})"),
            "has_papers": s.papers.exists(),
            "papers": [
                _option(p.id, p.code, name=p.name or "", sort_order=p.sort_order)
                for p in s.papers.all()
            ],
        }
        for s in rows
    ]


def marks_class_options(tenant, *, subject_id, academic_year_id=None, user=None) -> list[dict]:
    """
    Classes the user teaches for this subject.

    Prefer current academic year, but if that yields no classes fall back to all
    taught classes for the subject so teachers are not blocked by year mismatch.
    """
    ctx = get_academic_context(user) if user is not None else None
    if ctx is None or not subject_id or not ctx.teaching_pairs:
        return []

    normalized_subject = _normalize_uuid(subject_id)
    if normalized_subject is None:
        return []

    class_ids = {
        class_id
        for subj_id, class_id in ctx.teaching_pairs
        if subj_id == normalized_subject
    }
    if not class_ids:
        return []

    qs = (
        Class.objects.filter(tenant=tenant, id__in=class_ids, is_deleted=False)
        .select_related("academic_year")
        .order_by("name")
    )
    preferred_year = _normalize_uuid(academic_year_id)
    if preferred_year is None:
        year = resolve_current_academic_year(tenant)
        preferred_year = year.id if year else None

    if preferred_year is not None:
        year_qs = qs.filter(academic_year_id=preferred_year)
        if year_qs.exists():
            qs = year_qs

    return [
        _option(
            c.id,
            f"{c.name} ({c.code})",
            academic_year_id=str(c.academic_year_id) if c.academic_year_id else None,
            academic_year_name=c.academic_year.name if c.academic_year_id else "",
        )
        for c in qs
    ]


def marks_term_options(tenant, *, school_class_id=None, academic_year_id=None, user=None) -> list[dict]:
    """Current term only (used for meta/display; wizard no longer asks teachers)."""
    del academic_year_id
    del user
    active_term = resolve_current_term(tenant)
    if active_term is None:
        return []

    if school_class_id:
        school_class = (
            Class.objects.filter(tenant=tenant, pk=school_class_id, is_deleted=False)
            .select_related("academic_year")
            .first()
        )
        # Do not hard-block when class year differs — still expose current term for exams
        # that were scheduled under the current term.
        if school_class is None:
            return []

    return [
        _option(
            active_term.id,
            f"{active_term.name} — {active_term.academic_year.name} (current)",
            academic_year_id=str(active_term.academic_year_id),
            is_current=True,
        )
    ]


def marks_exam_queryset(
    tenant,
    user,
    *,
    subject_id,
    school_class_id,
    term_id=None,
    paper_id=None,
):
    """
    Exams a subject teacher may enter marks for.

    - Scoped to taught subject–class pair
    - Current term OR term-less OR linked to the active exam period
    - Does NOT hide papered exams when no paper is selected
    - Excludes archived assessments only
    """
    from apps.examinations.models import Exam

    if not user_teaches_pair(user, subject_id=subject_id, school_class_id=school_class_id):
        return Exam.objects.none()

    active_term = resolve_current_term(tenant)
    active_period = resolve_active_exam_period(tenant)
    resolved_term_id = _normalize_uuid(term_id) or (active_term.id if active_term else None)

    qs = (
        Exam.objects.filter(
            tenant=tenant,
            subject_id=subject_id,
            school_class_id=school_class_id,
            is_deleted=False,
        )
        .exclude(exam_type="assignment")
        .exclude(lifecycle_status=EXAM_LIFECYCLE_ARCHIVED)
        .select_related("subject", "paper", "school_class", "term", "examination_session")
    )

    scope_q = Q()
    if resolved_term_id is not None:
        scope_q |= Q(term_id=resolved_term_id)
    scope_q |= Q(term_id__isnull=True)
    if active_period is not None:
        scope_q |= Q(examination_session_id=active_period.id)
        if active_period.term_id:
            scope_q |= Q(term_id=active_period.term_id)
    qs = qs.filter(scope_q)

    paper_uuid = _normalize_uuid(paper_id)
    if paper_uuid is not None:
        qs = qs.filter(paper_id=paper_uuid)
    # When paper is not selected: return ALL papers for this subject/class so
    # scheduled multi-paper exams are not hidden.

    return qs.order_by("-exam_date", "name")


def ensure_marks_sheet_for_pair(
    tenant,
    user,
    *,
    subject_id,
    school_class_id,
    paper_id=None,
):
    """
    Guarantee a mark sheet exists for this teacher pair under the active exam period.

    Exam Sessions are calendar windows only — they do not create per-subject mark
    sheets. When a teacher opens marks entry for a taught subject/class during an
    open exam period, we get-or-create a ready-to-use Exam linked to that period.
    """
    from django.utils import timezone

    from apps.examinations.models import Exam

    if not user_teaches_pair(user, subject_id=subject_id, school_class_id=school_class_id):
        return None

    period = resolve_active_exam_period(tenant)
    if period is None:
        return None

    paper_uuid = _normalize_uuid(paper_id)
    active_term = resolve_current_term(tenant)
    term = period.term or active_term

    base = Exam.objects.filter(
        tenant=tenant,
        subject_id=subject_id,
        school_class_id=school_class_id,
        is_deleted=False,
    ).exclude(exam_type="assignment").exclude(lifecycle_status=EXAM_LIFECYCLE_ARCHIVED)

    if paper_uuid is not None:
        base = base.filter(paper_id=paper_uuid)
    else:
        # Prefer whole-subject sheet when no paper chosen; fall back to any paper.
        whole = base.filter(paper__isnull=True).first()
        if whole is not None:
            base_match = whole
        else:
            base_match = base.first()
        if base_match is not None:
            _link_exam_to_period(base_match, period=period, term=term, user=user)
            return base_match
        base = base.filter(paper__isnull=True)

    existing = (
        base.filter(examination_session_id=period.id).first()
        or (base.filter(term_id=term.id).first() if term is not None else None)
        or base.first()
    )
    if existing is not None:
        _link_exam_to_period(existing, period=period, term=term, user=user)
        return existing

    subject = Subject.objects.filter(tenant=tenant, pk=subject_id, is_deleted=False).first()
    school_class = Class.objects.filter(tenant=tenant, pk=school_class_id, is_deleted=False).first()
    if subject is None or school_class is None:
        return None

    paper_label = ""
    if paper_uuid is not None:
        from apps.academics.models import SubjectPaper
        paper = SubjectPaper.objects.filter(tenant=tenant, pk=paper_uuid, subject_id=subject_id).first()
        if paper is not None:
            paper_label = f" ({paper.code})"

    name = f"{period.name} — {subject.name}{paper_label}"
    if len(name) > 255:
        name = name[:252] + "…"

    exam_date = period.start_date or timezone.now().date()
    exam = Exam.objects.create(
        tenant=tenant,
        name=name,
        subject_id=subject_id,
        school_class_id=school_class_id,
        paper_id=paper_uuid,
        term=term,
        examination_session=period,
        exam_date=exam_date,
        max_score=100,
        weight=100,
        exam_type="final",
        lifecycle_status=EXAM_LIFECYCLE_PUBLISHED,
        published_at=timezone.now(),
        published_by=user,
        marks_status=MARKS_STATUS_DRAFT,
        created_by=user,
        updated_by=user,
    )
    return exam


def _link_exam_to_period(exam, *, period, term, user) -> None:
    """Attach an existing mark sheet to the open exam period when missing links."""
    update_fields: list[str] = []
    if exam.examination_session_id is None and period is not None:
        exam.examination_session = period
        update_fields.append("examination_session")
    if exam.term_id is None and term is not None:
        exam.term = term
        update_fields.append("term")
    if exam.lifecycle_status == "draft":
        from django.utils import timezone

        exam.lifecycle_status = EXAM_LIFECYCLE_PUBLISHED
        exam.published_at = timezone.now()
        exam.published_by = user
        update_fields.extend(["lifecycle_status", "published_at", "published_by"])
    if update_fields:
        exam.updated_by = user
        update_fields.extend(["updated_by", "updated_at"])
        exam.save(update_fields=list(dict.fromkeys(update_fields)))


def exam_option_row(exam) -> dict:
    paper_bit = f" · {exam.paper.code}" if exam.paper_id else ""
    status_bit = ""
    if exam.lifecycle_status != "published":
        status_bit = f" [{exam.lifecycle_status}]"
    return _option(
        exam.id,
        f"{exam.name} — {exam.exam_date}{paper_bit} ({exam.get_exam_type_display()}){status_bit}",
        max_score=str(exam.max_score),
        paper_code=exam.paper.code if exam.paper_id else "",
        paper_id=str(exam.paper_id) if exam.paper_id else None,
        lifecycle_status=exam.lifecycle_status,
        marks_status=exam.marks_status,
        has_marks=exam.grades.filter(is_deleted=False).exists(),
        term_id=str(exam.term_id) if exam.term_id else None,
        examination_session_id=str(exam.examination_session_id) if exam.examination_session_id else None,
    )
