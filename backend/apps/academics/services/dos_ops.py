"""DoS operational suite: performance, completeness, teacher load, UNEB export."""
from __future__ import annotations

import csv
import io
from collections import defaultdict
from decimal import Decimal
from typing import Any

from django.db.models import Avg, Count, Q

from apps.academics.models import Class, Stream, TeachingAssignment, Term, Timetable
from apps.academics.singleton import get_active_term
from apps.examinations.constants import MARKS_STATUS_APPROVED, MARKS_STATUS_LOCKED, MARKS_STATUS_DRAFT, MARKS_STATUS_SUBMITTED
from apps.examinations.models import Exam, Grade, ReportCard
from apps.students.models import Student


def _d(v) -> Decimal:
    return Decimal(str(v or 0))


def class_performance_analysis(
    *,
    tenant,
    term_id=None,
    school_class_id=None,
    stream_id=None,
) -> dict[str, Any]:
    term = None
    if term_id:
        term = Term.objects.filter(tenant=tenant, pk=term_id, is_deleted=False).first()
    if term is None:
        term = get_active_term(tenant)
    if term is None:
        return {"error": "No active term.", "subjects": [], "students": []}

    exam_qs = Exam.objects.filter(
        tenant=tenant, term=term, is_deleted=False,
        marks_status__in=[MARKS_STATUS_APPROVED, MARKS_STATUS_LOCKED],
    )
    if school_class_id:
        exam_qs = exam_qs.filter(school_class_id=school_class_id)

    subject_means = []
    for row in (
        Grade.objects.filter(tenant=tenant, is_deleted=False, exam__in=exam_qs)
        .values("exam__subject_id", "exam__subject__name", "exam__subject__code")
        .annotate(mean=Avg("score"), count=Count("id"))
        .order_by("exam__subject__name")
    ):
        subject_means.append({
            "subject_id": str(row["exam__subject_id"]) if row["exam__subject_id"] else None,
            "subject_name": row["exam__subject__name"] or "",
            "subject_code": row["exam__subject__code"] or "",
            "mean": str(round(float(row["mean"] or 0), 2)),
            "entries": row["count"],
        })

    students_qs = Student.objects.filter(tenant=tenant, is_deleted=False, status="active")
    if school_class_id:
        students_qs = students_qs.filter(school_class_id=school_class_id)
    if stream_id:
        students_qs = students_qs.filter(stream_id=stream_id)

    student_rows = []
    failure_list = []
    for st in students_qs.select_related("school_class", "stream")[:500]:
        grades = Grade.objects.filter(
            tenant=tenant, student=st, is_deleted=False, exam__in=exam_qs,
        )
        avg = grades.aggregate(a=Avg("score"))["a"]
        avg_d = float(avg or 0)
        fails = grades.filter(score__lt=50).count()
        row = {
            "student_id": str(st.id),
            "admission_number": st.admission_number,
            "full_name": st.full_name,
            "class_name": st.school_class.name if st.school_class_id else "",
            "stream_name": st.stream.name if st.stream_id else "",
            "average": round(avg_d, 2),
            "fail_count": fails,
        }
        student_rows.append(row)
        if fails > 0 or (avg is not None and avg_d < 50):
            failure_list.append(row)

    student_rows.sort(key=lambda x: x["average"], reverse=True)
    return {
        "term_id": str(term.id),
        "term_name": term.name,
        "subjects": subject_means,
        "students": student_rows[:200],
        "failure_list": failure_list[:100],
        "counts": {
            "students": students_qs.count(),
            "failures": len(failure_list),
            "subjects": len(subject_means),
        },
    }


def marks_completeness_dashboard(*, tenant, term_id=None) -> dict[str, Any]:
    term = Term.objects.filter(tenant=tenant, pk=term_id, is_deleted=False).first() if term_id else get_active_term(tenant)
    if term is None:
        return {"error": "No active term.", "rows": []}

    exams = Exam.objects.filter(tenant=tenant, term=term, is_deleted=False, lifecycle_status="published").select_related(
        "subject", "school_class",
    )
    rows = []
    for exam in exams[:300]:
        expected = Student.objects.filter(
            tenant=tenant, school_class_id=exam.school_class_id, is_deleted=False, status="active",
        )
        expected_n = expected.count()
        entered = Grade.objects.filter(tenant=tenant, exam=exam, is_deleted=False).count()
        rows.append({
            "exam_id": str(exam.id),
            "name": exam.name,
            "subject": exam.subject.name if exam.subject_id else "",
            "class_name": exam.school_class.name if exam.school_class_id else "",
            "stream_name": "",
            "marks_status": exam.marks_status,
            "expected": expected_n,
            "entered": entered,
            "missing": max(0, expected_n - entered),
            "complete": expected_n > 0 and entered >= expected_n,
        })
    incomplete = [r for r in rows if not r["complete"]]
    by_status = defaultdict(int)
    for r in rows:
        by_status[r["marks_status"]] += 1
    return {
        "term_id": str(term.id),
        "term_name": term.name,
        "rows": rows,
        "incomplete": incomplete,
        "summary": {
            "total_exams": len(rows),
            "complete": sum(1 for r in rows if r["complete"]),
            "incomplete": len(incomplete),
            "by_status": dict(by_status),
            "draft": by_status.get(MARKS_STATUS_DRAFT, 0),
            "submitted": by_status.get(MARKS_STATUS_SUBMITTED, 0),
            "approved": by_status.get(MARKS_STATUS_APPROVED, 0) + by_status.get(MARKS_STATUS_LOCKED, 0),
        },
    }


def teacher_load_report(*, tenant) -> dict[str, Any]:
    """Lessons/week derived from active published timetable slots."""
    slots = (
        Timetable.objects.filter(tenant=tenant, is_deleted=False)
        .exclude(teacher__isnull=True)
        .select_related("teacher__staff", "subject", "school_class")
    )
    by_teacher: dict[str, dict] = {}
    for slot in slots:
        tid = str(slot.teacher_id)
        bucket = by_teacher.setdefault(tid, {
            "teacher_id": tid,
            "teacher_name": (
                slot.teacher.staff.full_name
                if slot.teacher_id and getattr(slot.teacher, "staff_id", None)
                else str(slot.teacher_id)
            ),
            "lessons_per_week": 0,
            "subjects": set(),
            "classes": set(),
        })
        bucket["lessons_per_week"] += 1
        if slot.subject_id:
            bucket["subjects"].add(slot.subject.name)
        if slot.school_class_id:
            bucket["classes"].add(slot.school_class.name)

    # Also include teaching assignments with zero timetable slots
    for ta in TeachingAssignment.objects.filter(tenant=tenant, is_deleted=False, is_active=True).select_related(
        "teacher__staff", "subject", "school_class",
    ):
        tid = str(ta.teacher_id)
        if tid not in by_teacher:
            by_teacher[tid] = {
                "teacher_id": tid,
                "teacher_name": (
                    ta.teacher.staff.full_name
                    if ta.teacher_id and getattr(ta.teacher, "staff_id", None)
                    else str(ta.teacher_id)
                ),
                "lessons_per_week": 0,
                "subjects": set(),
                "classes": set(),
            }
        by_teacher[tid]["subjects"].add(ta.subject.name if ta.subject_id else "")
        by_teacher[tid]["classes"].add(ta.school_class.name if ta.school_class_id else "")

    rows = []
    for b in by_teacher.values():
        rows.append({
            "teacher_id": b["teacher_id"],
            "teacher_name": b["teacher_name"],
            "lessons_per_week": b["lessons_per_week"],
            "subjects": sorted(s for s in b["subjects"] if s),
            "classes": sorted(c for c in b["classes"] if c),
            "subject_count": len([s for s in b["subjects"] if s]),
            "class_count": len([c for c in b["classes"] if c]),
        })
    rows.sort(key=lambda x: (-x["lessons_per_week"], x["teacher_name"]))
    return {"rows": rows, "count": len(rows)}


def uneb_candidate_export(
    *,
    tenant,
    school_class_id=None,
    level_hint: str = "",
    exam_year: str = "",
) -> tuple[str, str]:
    """
    Return (filename, csv_text) for UNEB-style candidate registration list.
    Schools create classes/streams; we export active students with index fields.
    """
    qs = Student.objects.filter(tenant=tenant, is_deleted=False, status="active").select_related(
        "school_class", "stream",
    ).order_by("school_class__name", "stream__name", "last_name", "first_name")
    if school_class_id:
        qs = qs.filter(school_class_id=school_class_id)
    # Prefer S4 / S6 naming heuristics when level_hint given
    if level_hint:
        lh = level_hint.lower()
        if lh in ("uce", "o", "o_level", "s4"):
            qs = qs.filter(Q(school_class__name__icontains="S4") | Q(school_class__code__icontains="S4"))
        elif lh in ("uace", "a", "a_level", "s6"):
            qs = qs.filter(Q(school_class__name__icontains="S6") | Q(school_class__code__icontains="S6"))
        elif lh in ("ple", "p7"):
            qs = qs.filter(Q(school_class__name__icontains="P7") | Q(school_class__code__icontains="P7"))

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "index_number",
        "admission_number",
        "registration_number",
        "surname",
        "other_names",
        "gender",
        "date_of_birth",
        "class",
        "stream",
        "district",
        "nationality",
        "exam_year",
        "school_code",
    ])
    school_code = getattr(tenant, "code", "") or ""
    for st in qs:
        writer.writerow([
            st.registration_number or st.upi_number or "",
            st.admission_number,
            st.registration_number or "",
            st.last_name,
            " ".join(p for p in [st.first_name, st.middle_name] if p),
            st.gender,
            str(st.date_of_birth) if st.date_of_birth else "",
            st.school_class.name if st.school_class_id else "",
            st.stream.name if st.stream_id else "",
            st.district or st.county or "",
            st.nationality or "Ugandan",
            exam_year or "",
            school_code,
        ])
    year_bit = exam_year or "export"
    fname = f"uneb-candidates-{year_bit}.csv".replace(" ", "-")
    return fname, buf.getvalue()


def report_generation_status(*, tenant, term_id=None) -> dict[str, Any]:
    term = Term.objects.filter(tenant=tenant, pk=term_id, is_deleted=False).first() if term_id else get_active_term(tenant)
    if term is None:
        return {"rows": [], "term": None}
    classes = Class.objects.filter(tenant=tenant, is_deleted=False).order_by("name")
    rows = []
    for c in classes:
        active = Student.objects.filter(
            tenant=tenant, school_class=c, is_deleted=False, status="active",
        ).count()
        if active == 0:
            continue
        cards = ReportCard.objects.filter(
            tenant=tenant, term=term, school_class=c, is_deleted=False, is_latest=True,
        )
        gen = cards.count()
        pub = cards.filter(is_published=True).count()
        status = "not_generated"
        if gen >= active and pub >= active:
            status = "published"
        elif gen >= active:
            status = "ready"
        elif gen > 0:
            status = "partial"
        rows.append({
            "school_class_id": str(c.id),
            "class_name": c.name,
            "active_students": active,
            "generated": gen,
            "published": pub,
            "status": status,
        })
    return {
        "term_id": str(term.id),
        "term_name": term.name,
        "rows": rows,
        "summary": {
            "not_generated": sum(1 for r in rows if r["status"] == "not_generated"),
            "partial": sum(1 for r in rows if r["status"] == "partial"),
            "ready": sum(1 for r in rows if r["status"] == "ready"),
            "published": sum(1 for r in rows if r["status"] == "published"),
        },
    }
