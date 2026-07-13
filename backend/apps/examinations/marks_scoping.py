"""Marks entry and grade calculation option scoping."""
from __future__ import annotations

from uuid import UUID

from apps.academics.models import Class, Subject, Term
from apps.academics.scoping import get_academic_context, user_has_unrestricted_marks_access
from apps.academics.singleton import get_active_term
from apps.examinations.reference import (
    _option,
    class_options,
    subject_options,
    term_options,
)


def resolve_current_term(tenant):
    """Prefer the term flagged is_current; fall back to calendar-active term."""
    current = (
        Term.objects.filter(tenant=tenant, is_deleted=False, is_current=True)
        .select_related("academic_year")
        .order_by("-start_date")
        .first()
    )
    return current or get_active_term(tenant)


def marks_scope_meta(tenant, user) -> dict:
    unrestricted = user_has_unrestricted_marks_access(user)
    active_term = resolve_current_term(tenant)
    return {
        "is_unrestricted": unrestricted,
        "term_locked": not unrestricted,
        "current_term_id": str(active_term.id) if active_term else None,
        "current_term_name": active_term.name if active_term else None,
        "uses_teaching_assignments": not unrestricted,
    }


def marks_subject_options(tenant, user) -> list[dict]:
    if user_has_unrestricted_marks_access(user):
        return subject_options(tenant, user=None)

    ctx = get_academic_context(user)
    if ctx is None:
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
    if user is not None and user_has_unrestricted_marks_access(user):
        return class_options(
            tenant,
            subject_id=subject_id,
            academic_year_id=academic_year_id,
            user=None,
        )

    ctx = get_academic_context(user) if user is not None else None
    if ctx is None or not subject_id:
        return []

    try:
        normalized_subject = UUID(str(subject_id))
    except (TypeError, ValueError):
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
    return [
        _option(
            c.id,
            f"{c.name} ({c.code})",
            academic_year_id=str(c.academic_year_id),
            academic_year_name=c.academic_year.name,
        )
        for c in qs
    ]


def marks_term_options(tenant, *, school_class_id=None, academic_year_id=None, user=None) -> list[dict]:
    if user is not None and user_has_unrestricted_marks_access(user):
        return term_options(
            tenant,
            school_class_id=school_class_id,
            academic_year_id=academic_year_id,
        )

    active_term = resolve_current_term(tenant)
    if active_term is None:
        return []

    if school_class_id:
        school_class = (
            Class.objects.filter(tenant=tenant, pk=school_class_id, is_deleted=False)
            .select_related("academic_year")
            .first()
        )
        if school_class is None or school_class.academic_year_id != active_term.academic_year_id:
            return []

    return [
        _option(
            active_term.id,
            f"{active_term.name} — {active_term.academic_year.name} (current)",
            academic_year_id=str(active_term.academic_year_id),
            is_current=True,
        )
    ]