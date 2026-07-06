"""Shared examination reference data (subjects, classes, terms, papers)."""
from __future__ import annotations

from apps.academics.models import (
    AcademicYear,
    Assignment,
    Class,
    Homework,
    Subject,
    SubjectPaper,
    Term,
    Timetable,
)
from apps.examinations.models import Exam


def _option(value, label, **extra):
    return {"value": str(value), "label": label, **extra}


def current_academic_year(tenant):
    return AcademicYear.objects.filter(tenant=tenant, is_current=True).first()


def subject_options(tenant) -> list[dict]:
    rows = Subject.objects.filter(tenant=tenant).prefetch_related("papers").order_by("name")
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


def paper_options(tenant, subject_id) -> list[dict]:
    return [
        _option(p.id, f"{p.code}{f' — {p.name}' if p.name else ''}")
        for p in SubjectPaper.objects.filter(tenant=tenant, subject_id=subject_id).order_by("sort_order", "code")
    ]


def class_ids_for_subject(tenant, subject_id) -> set:
    linked = set(
        Timetable.objects.filter(tenant=tenant, subject_id=subject_id).values_list("school_class_id", flat=True),
    )
    linked |= set(
        Assignment.objects.filter(tenant=tenant, subject_id=subject_id).values_list("school_class_id", flat=True),
    )
    linked |= set(
        Homework.objects.filter(tenant=tenant, subject_id=subject_id).values_list("school_class_id", flat=True),
    )
    linked |= set(
        Exam.objects.filter(tenant=tenant, subject_id=subject_id).values_list("school_class_id", flat=True),
    )
    return {cid for cid in linked if cid}


def class_options(tenant, *, subject_id=None, academic_year_id=None) -> list[dict]:
    qs = Class.objects.filter(tenant=tenant).select_related("academic_year")
    year = None
    if academic_year_id:
        year = AcademicYear.objects.filter(tenant=tenant, pk=academic_year_id).first()
    if year is None:
        year = current_academic_year(tenant)
    if year:
        qs = qs.filter(academic_year=year)

    linked = class_ids_for_subject(tenant, subject_id) if subject_id else set()
    if linked:
        qs = qs.filter(id__in=linked)

    return [
        _option(
            c.id,
            f"{c.name} ({c.code})",
            academic_year_id=str(c.academic_year_id),
            academic_year_name=c.academic_year.name,
        )
        for c in qs.order_by("name")
    ]


def term_options(tenant, *, school_class_id=None, academic_year_id=None) -> list[dict]:
    qs = Term.objects.filter(tenant=tenant).select_related("academic_year")
    if school_class_id:
        school_class = Class.objects.filter(tenant=tenant, pk=school_class_id).select_related("academic_year").first()
        if school_class:
            qs = qs.filter(academic_year_id=school_class.academic_year_id)
    elif academic_year_id:
        qs = qs.filter(academic_year_id=academic_year_id)
    else:
        year = current_academic_year(tenant)
        if year:
            qs = qs.filter(academic_year=year)

    return [
        _option(
            t.id,
            f"{t.name} — {t.academic_year.name}{' (current)' if t.is_current else ''}",
            academic_year_id=str(t.academic_year_id),
            is_current=t.is_current,
        )
        for t in qs.order_by("start_date")
    ]


def academic_year_options(tenant) -> list[dict]:
    return [
        _option(y.id, f"{y.name}{' (current)' if y.is_current else ''}", is_current=y.is_current)
        for y in AcademicYear.objects.filter(tenant=tenant).order_by("-start_date")
    ]