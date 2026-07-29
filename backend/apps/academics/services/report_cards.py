"""Report card generation, ranking, attendance rollup, publish with fee-gate awareness."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.academics.models import (
    AssessmentScheme,
    Class,
    DisciplineRemark,
    Stream,
    Term,
)
from apps.attendance.models import AttendanceRecord
from apps.audit.models import AuditLog
from apps.examinations.constants import MARKS_STATUS_APPROVED, MARKS_STATUS_LOCKED
from apps.examinations.grading import resolve_band
from apps.examinations.models import Exam, Grade, GradingScheme, ReportCard, ReportCardSubjectLine
from apps.students.models import Student


class ReportCardError(Exception):
    def __init__(self, message: str, *, code: str = "report_card_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def _d(v) -> Decimal:
    return Decimal(str(v or 0))


def _attendance_summary(*, tenant, student, term: Term) -> dict[str, int]:
    qs = AttendanceRecord.objects.filter(
        tenant=tenant,
        student=student,
        attendee_type="student",
        is_deleted=False,
        date__gte=term.start_date,
        date__lte=term.end_date,
    )
    counts = {"present": 0, "absent": 0, "late": 0, "excused": 0}
    for row in qs.values("status").annotate(c=Count("id")):
        st = row["status"]
        if st in counts:
            counts[st] = row["c"]
        elif st == "half_day":
            counts["present"] += row["c"]
    return counts


def _next_term_opens(term: Term):
    nxt = (
        Term.objects.filter(
            tenant=term.tenant_id,
            is_deleted=False,
            start_date__gt=term.end_date,
        )
        .order_by("start_date")
        .first()
    )
    return nxt.start_date if nxt else None


def _default_scheme(tenant) -> GradingScheme | None:
    return (
        GradingScheme.objects.filter(tenant=tenant, is_deleted=False, is_default=True)
        .prefetch_related("bands")
        .first()
        or GradingScheme.objects.filter(tenant=tenant, is_deleted=False)
        .prefetch_related("bands")
        .order_by("name")
        .first()
    )


def _assessment_scheme(tenant) -> AssessmentScheme | None:
    return (
        AssessmentScheme.objects.filter(tenant=tenant, is_deleted=False, is_default=True).first()
        or AssessmentScheme.objects.filter(tenant=tenant, is_deleted=False).order_by("name").first()
    )


def _conduct_summary(*, tenant, student, term: Term) -> dict[str, Any]:
    qs = DisciplineRemark.objects.filter(
        tenant=tenant, student=student, is_deleted=False,
    )
    if term:
        qs = qs.filter(Q(term=term) | Q(incident_date__gte=term.start_date, incident_date__lte=term.end_date))
    total_points = qs.aggregate(s=Sum("conduct_points"))["s"] or 0
    open_cases = qs.filter(status__in=["open", "in_progress"]).count()
    grade = "A"
    if total_points <= -10:
        grade = "D"
    elif total_points <= -5:
        grade = "C"
    elif total_points <= -1:
        grade = "B"
    elif total_points >= 5:
        grade = "A+"
    return {"conduct_points": int(total_points), "open_cases": open_cases, "conduct_grade": grade}


def _subject_scores_for_student(*, tenant, student, term, school_class, scheme: GradingScheme | None):
    """
    Aggregate entered marks by subject for one student in a term/class.

    A report card is a full learner performance record — every subject where the
    learner has an entered score appears (not single-subject mark sheets).
    Approved/locked marks are preferred when present; otherwise any entered score
    on a non-deleted assessment is included so drafts still generate complete results.
    """
    grades = (
        Grade.objects.filter(
            tenant=tenant,
            student=student,
            is_deleted=False,
            exam__term=term,
            exam__school_class=school_class,
            exam__is_deleted=False,
            exam__exam_type__in=["midterm", "final", "continuous", "assignment"],
            score__isnull=False,
        )
        .select_related("exam", "exam__subject", "exam__paper")
    )

    by_subject: dict[str, dict[str, Any]] = {}
    for g in grades:
        if g.exam.subject_id is None:
            continue
        sid = str(g.exam.subject_id)
        bucket = by_subject.setdefault(sid, {
            "subject": g.exam.subject,
            "papers": [],
            "scores": [],
            "ca": [],
            "exam": [],
            "has_approved": False,
        })
        score = _d(g.score)
        max_s = _d(g.exam.max_score) or Decimal("100")
        # normalize to /100
        norm = (score / max_s * Decimal("100")).quantize(Decimal("0.01")) if max_s else score
        bucket["scores"].append(norm)
        if g.exam.marks_status in (MARKS_STATUS_APPROVED, MARKS_STATUS_LOCKED):
            bucket["has_approved"] = True
        et = g.exam.exam_type
        if et in ("continuous", "assignment", "midterm"):
            bucket["ca"].append(norm)
        else:
            bucket["exam"].append(norm)
        if g.exam.paper_id:
            bucket["papers"].append({
                "paper_id": str(g.exam.paper_id),
                "code": g.exam.paper.code if g.exam.paper_id else "",
                "score": str(score),
                "max_score": str(max_s),
                "normalized": str(norm),
            })

    assess = _assessment_scheme(tenant)
    scheme_bands = list(scheme.bands.filter(is_deleted=False)) if scheme is not None else []
    lines = []
    for sid, data in by_subject.items():
        if not data["scores"]:
            continue
        subj = data["subject"]
        ca_vals = data["ca"]
        ex_vals = data["exam"]
        ca_avg = (sum(ca_vals) / len(ca_vals)).quantize(Decimal("0.01")) if ca_vals else None
        ex_avg = (sum(ex_vals) / len(ex_vals)).quantize(Decimal("0.01")) if ex_vals else None

        # Default 30/70 if assessment scheme present with 2 components, else average all
        total = Decimal("0")
        if assess and assess.components and (ca_avg is not None or ex_avg is not None):
            ca_w = Decimal("30")
            ex_w = Decimal("70")
            for comp in assess.components:
                label = (comp.get("label") or comp.get("key") or "").lower()
                w = _d(comp.get("weight_percent") or 0)
                if any(k in label for k in ("bot", "mot", "ca", "continuous", "mid")):
                    ca_w = w or ca_w
                if any(k in label for k in ("eot", "final", "exam", "end")):
                    ex_w = w or ex_w
            total_w = ca_w + ex_w
            if total_w <= 0:
                total_w = Decimal("100")
            part = Decimal("0")
            if ca_avg is not None:
                part += ca_avg * ca_w / total_w
            if ex_avg is not None:
                part += ex_avg * ex_w / total_w
            if ca_avg is None and ex_avg is not None:
                part = ex_avg
            if ex_avg is None and ca_avg is not None:
                part = ca_avg
            total = part.quantize(Decimal("0.01"))
        else:
            all_scores = data["scores"]
            total = (sum(all_scores) / len(all_scores)).quantize(Decimal("0.01")) if all_scores else Decimal("0")

        band = resolve_band(scheme_bands, score=total) if scheme_bands else None

        lines.append({
            "subject": subj,
            "subject_name": subj.name if subj else "",
            "subject_code": subj.code if subj else "",
            "paper_breakdown": data["papers"],
            "ca_score": ca_avg,
            "exam_score": ex_avg,
            "total_score": total,
            "max_score": Decimal("100"),
            "grade": band.grade if band else "",
            "grade_point": band.grade_point if band else None,
            # Per-subject remarks from grading band — not overall teacher/DoS remarks
            "remarks": (band.remarks if band else "") or "",
        })
    lines.sort(key=lambda x: (x["subject_code"] or x["subject_name"] or "").lower())
    return lines


def resolve_overall_grade(*, scheme: GradingScheme | None, average_score) -> dict[str, Any]:
    """Map average mark to overall grade + remarks using the school grading scheme."""
    if scheme is None or average_score is None:
        return {"grade": "", "grade_point": None, "remarks": ""}
    try:
        avg = Decimal(str(average_score))
    except Exception:
        return {"grade": "", "grade_point": None, "remarks": ""}
    bands = list(scheme.bands.filter(is_deleted=False))
    band = resolve_band(bands, score=avg) if bands else None
    if not band:
        return {"grade": "", "grade_point": None, "remarks": ""}
    return {
        "grade": band.grade or "",
        "grade_point": band.grade_point,
        "remarks": band.remarks or "",
    }


@transaction.atomic
def generate_class_report_cards(
    *,
    tenant,
    user,
    term_id,
    school_class_id,
    stream_id=None,
    teacher_remarks: str = "",
    principal_remarks: str = "",
    dos_remarks: str = "",
    request=None,
) -> dict[str, Any]:
    term = Term.objects.filter(tenant=tenant, pk=term_id, is_deleted=False).select_related("academic_year").first()
    if not term:
        raise ReportCardError("Term not found.", code="term_not_found")
    school_class = Class.objects.filter(tenant=tenant, pk=school_class_id, is_deleted=False).first()
    if not school_class:
        raise ReportCardError("Class not found.", code="class_not_found")

    stream = None
    if stream_id:
        stream = Stream.objects.filter(tenant=tenant, pk=stream_id, school_class=school_class, is_deleted=False).first()

    students = Student.objects.filter(
        tenant=tenant, school_class=school_class, is_deleted=False, status="active",
    ).select_related("stream").order_by("last_name", "first_name")
    if stream:
        students = students.filter(stream=stream)
    students = list(students)
    if not students:
        raise ReportCardError("No active students in this class/stream.", code="no_students")

    scheme = _default_scheme(tenant)
    next_opens = _next_term_opens(term)

    # Build per-student totals for ranking
    built = []
    for st in students:
        lines = _subject_scores_for_student(
            tenant=tenant, student=st, term=term, school_class=school_class, scheme=scheme,
        )
        totals = [l["total_score"] for l in lines]
        total = sum(totals) if totals else Decimal("0")
        avg = (total / len(totals)).quantize(Decimal("0.01")) if totals else Decimal("0")
        overall = resolve_overall_grade(scheme=scheme, average_score=avg)
        att = _attendance_summary(tenant=tenant, student=st, term=term)
        conduct = _conduct_summary(tenant=tenant, student=st, term=term)
        built.append({
            "student": st,
            "lines": lines,
            "total": total,
            "average": avg,
            "overall_grade": overall.get("grade") or "",
            "overall_grade_point": overall.get("grade_point"),
            "overall_grade_remarks": overall.get("remarks") or "",
            "attendance": att,
            "conduct": conduct,
        })

    # Class rank (all built)
    ordered = sorted(built, key=lambda x: x["average"], reverse=True)
    class_rank = {}
    for i, row in enumerate(ordered, start=1):
        class_rank[str(row["student"].id)] = i

    # Stream ranks
    stream_groups: dict[str, list] = defaultdict(list)
    for row in built:
        sid = str(row["student"].stream_id or "")
        stream_groups[sid].append(row)
    stream_rank = {}
    stream_size = {}
    for sid, rows in stream_groups.items():
        rows_sorted = sorted(rows, key=lambda x: x["average"], reverse=True)
        stream_size[sid] = len(rows_sorted)
        for i, row in enumerate(rows_sorted, start=1):
            stream_rank[str(row["student"].id)] = i

    generated = []
    for row in built:
        st = row["student"]
        # Mark previous versions not latest
        ReportCard.objects.filter(
            tenant=tenant, student=st, term=term, is_deleted=False, is_latest=True,
        ).update(is_latest=False)

        prev = (
            ReportCard.objects.filter(tenant=tenant, student=st, term=term, is_deleted=False)
            .order_by("-version")
            .first()
        )
        version = (prev.version + 1) if prev else 1

        sid = str(st.stream_id or "")
        rc = ReportCard.objects.create(
            tenant=tenant,
            student=st,
            term=term,
            school_class=school_class,
            stream=st.stream,
            academic_year=term.academic_year,
            version=version,
            is_latest=True,
            total_score=row["total"],
            average_score=row["average"],
            rank=class_rank.get(str(st.id)),
            stream_rank=stream_rank.get(str(st.id)),
            class_size=len(built),
            stream_size=stream_size.get(sid),
            remarks="",
            teacher_remarks=teacher_remarks or "",
            principal_remarks=principal_remarks or "",
            dos_remarks=dos_remarks or "",
            is_published=False,
            days_present=row["attendance"].get("present", 0),
            days_absent=row["attendance"].get("absent", 0),
            days_late=row["attendance"].get("late", 0),
            days_excused=row["attendance"].get("excused", 0),
            next_term_opens=next_opens,
            generation_meta={
                "generated_by": str(getattr(user, "id", "")),
                "scheme_id": str(scheme.id) if scheme else None,
                "conduct": row.get("conduct") or {},
                "overall_grade": row.get("overall_grade") or "",
                "overall_grade_point": (
                    str(row["overall_grade_point"])
                    if row.get("overall_grade_point") is not None
                    else None
                ),
                "overall_grade_remarks": row.get("overall_grade_remarks") or "",
            },
            created_by=user,
            updated_by=user,
        )
        # Persist overall grade on division field when free (human-readable letter)
        if row.get("overall_grade") and not rc.division:
            rc.division = str(row["overall_grade"])[:20]
            rc.save(update_fields=["division", "updated_at"])
        # Append conduct grade into remarks if empty of formal remarks
        if row.get("conduct") and not rc.remarks:
            c = row["conduct"]
            rc.remarks = f"Conduct: {c.get('conduct_grade', '—')} ({c.get('conduct_points', 0)} pts)"
            rc.save(update_fields=["remarks", "updated_at"])
        for i, line in enumerate(row["lines"], start=1):
            ReportCardSubjectLine.objects.create(
                tenant=tenant,
                report_card=rc,
                subject=line["subject"],
                subject_name=line["subject_name"],
                subject_code=line["subject_code"],
                paper_breakdown=line["paper_breakdown"],
                ca_score=line["ca_score"],
                exam_score=line["exam_score"],
                total_score=line["total_score"],
                max_score=line["max_score"],
                grade=line["grade"],
                grade_point=line["grade_point"],
                remarks=line["remarks"],
                sort_order=i,
                created_by=user,
                updated_by=user,
            )
        generated.append(rc)

    AuditLog.objects.create(
        tenant=tenant,
        user=user if getattr(user, "is_authenticated", False) else None,
        action="report_cards_generated",
        resource_type="ReportCard",
        resource_id=str(school_class.id),
        description=f"Generated {len(generated)} report cards for {school_class.name} / {term.name}",
        changes={"count": len(generated), "term_id": str(term.id), "stream_id": stream_id},
        status_code=200,
    )
    return {
        "count": len(generated),
        "term_id": str(term.id),
        "school_class_id": str(school_class.id),
        "stream_id": str(stream.id) if stream else None,
        "report_card_ids": [str(r.id) for r in generated],
    }


@transaction.atomic
def publish_report_cards(*, tenant, user, report_card_ids: list | None = None, term_id=None, school_class_id=None, stream_id=None):
    """Mark latest report cards as published so they appear on report-card surfaces.

    Unpublished cards are internal results only. Parent portal and other
    report-card lists filter is_published=True.
    """
    qs = ReportCard.objects.filter(tenant=tenant, is_deleted=False, is_latest=True, is_published=False)
    if report_card_ids:
        qs = qs.filter(pk__in=report_card_ids)
    else:
        if term_id:
            qs = qs.filter(term_id=term_id)
        if school_class_id:
            qs = qs.filter(school_class_id=school_class_id)
        if stream_id:
            qs = qs.filter(stream_id=stream_id)
    now = timezone.now()
    updated = qs.update(is_published=True, published_at=now, published_by=user, updated_by=user)
    return {"published": updated}


@transaction.atomic
def unpublish_report_cards(*, tenant, user, report_card_ids: list):
    updated = ReportCard.objects.filter(
        tenant=tenant, pk__in=report_card_ids, is_deleted=False,
    ).update(is_published=False, published_at=None, published_by=None, updated_by=user)
    return {"unpublished": updated}

