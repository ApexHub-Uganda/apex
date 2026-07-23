"""Class assignment marks — term-free progress assessments under Academics → Assignments."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.academics.models import Class, Subject
from apps.academics.scoping import (
    filter_queryset_for_user,
    get_academic_context,
    results_role_capabilities,
    user_can_write_assignment_marks,
    user_is_subject_marks_teacher,
)
from apps.examinations.constants import EXAM_LIFECYCLE_PUBLISHED, MARKS_STATUS_DRAFT
from apps.examinations.marks_scoping import marks_class_options, marks_subject_options
from apps.examinations.models import Exam
from apps.examinations.reference import _option, paper_options


class AssignmentMarksError(Exception):
    def __init__(self, message: str, *, code: str = "assignment_marks_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def assignment_scope_meta(tenant, user) -> dict:
    can_enter = user_is_subject_marks_teacher(user)
    caps = results_role_capabilities(user)
    return {
        "is_unrestricted": False,
        "term_locked": False,
        "uses_teaching_assignments": True,
        "is_assignment_flow": True,
        "can_enter_marks": can_enter,
        "can_apply_grading": can_enter,
        "can_print_report_cards": caps["can_print_report_cards"],
        "capabilities": caps,
        "message": (
            None if can_enter
            else "Assignment marks entry is only available for classes and subjects assigned to you."
        ),
    }


def _assignment_exam_queryset(tenant, user):
    qs = Exam.objects.filter(
        tenant=tenant,
        exam_type="assignment",
        is_deleted=False,
    ).select_related("subject", "paper", "school_class")
    return filter_queryset_for_user(qs, user)


def _normalize_paper_filter(paper_id):
    if not paper_id or str(paper_id).lower() in {"", "none"}:
        return None
    try:
        return UUID(str(paper_id))
    except (TypeError, ValueError):
        return "invalid"


def assignment_assessment_options(
    tenant,
    *,
    subject_id,
    school_class_id,
    paper_id=None,
    user=None,
) -> list[dict]:
    if not subject_id or not school_class_id:
        return []

    qs = _assignment_exam_queryset(tenant, user).filter(
        subject_id=subject_id,
        school_class_id=school_class_id,
    )
    normalized_paper = _normalize_paper_filter(paper_id)
    if normalized_paper == "invalid":
        return []
    if normalized_paper:
        qs = qs.filter(paper_id=normalized_paper)
    else:
        qs = qs.filter(paper__isnull=True)

    return [
        _option(
            exam.id,
            exam.name,
            max_score=str(exam.max_score),
            marks_count=exam.grades.filter(is_deleted=False).count(),
            exam_date=str(exam.exam_date) if exam.exam_date else "",
        )
        for exam in qs.order_by("-exam_date", "name")
    ]


def user_can_create_assignment(user, *, subject_id, school_class_id) -> bool:
    """Only the subject teacher for the pair may create assignment assessments."""
    ctx = get_academic_context(user)
    if ctx is None or ctx.teacher is None:
        return False
    try:
        pair = (UUID(str(subject_id)), UUID(str(school_class_id)))
    except (TypeError, ValueError):
        return False
    return pair in ctx.teaching_pairs


@transaction.atomic
def get_or_create_assignment_assessment(
    *,
    tenant,
    user,
    name: str,
    subject_id,
    school_class_id,
    paper_id=None,
    max_score: Decimal | float | int | str = 100,
) -> Exam:
    clean_name = (name or "").strip()
    if not clean_name:
        raise AssignmentMarksError("Enter a name for this assignment, e.g. Assignment 1.", code="name_required")
    if len(clean_name) > 255:
        raise AssignmentMarksError("Assignment name is too long.", code="name_too_long")

    if not user_can_create_assignment(user, subject_id=subject_id, school_class_id=school_class_id):
        raise AssignmentMarksError(
            "You may only create assignments for your assigned subjects and classes.",
            code="forbidden",
        )

    subject = Subject.objects.filter(tenant=tenant, pk=subject_id, is_deleted=False).first()
    if subject is None:
        raise AssignmentMarksError("Subject not found.", code="subject_not_found")

    school_class = Class.objects.filter(tenant=tenant, pk=school_class_id, is_deleted=False).first()
    if school_class is None:
        raise AssignmentMarksError("Class not found.", code="class_not_found")

    normalized_paper = _normalize_paper_filter(paper_id)
    if normalized_paper == "invalid":
        raise AssignmentMarksError("Invalid paper selection.", code="invalid_paper")

    lookup = {
        "tenant": tenant,
        "name": clean_name,
        "subject_id": subject_id,
        "school_class_id": school_class_id,
        "exam_type": "assignment",
        "is_deleted": False,
    }
    if normalized_paper:
        lookup["paper_id"] = normalized_paper
    else:
        lookup["paper__isnull"] = True

    existing = (
        Exam.objects.filter(**lookup)
        .select_related("subject", "paper", "school_class")
        .first()
    )
    if existing is not None:
        return existing

    try:
        score_cap = Decimal(str(max_score))
    except Exception as exc:
        raise AssignmentMarksError("Invalid max score.", code="invalid_max_score") from exc

    if score_cap <= 0:
        raise AssignmentMarksError("Max score must be greater than zero.", code="invalid_max_score")

    now = timezone.now()
    return Exam.objects.create(
        tenant=tenant,
        name=clean_name,
        subject_id=subject_id,
        school_class_id=school_class_id,
        paper_id=normalized_paper,
        term=None,
        exam_date=date.today(),
        max_score=score_cap,
        weight=score_cap,
        exam_type="assignment",
        lifecycle_status=EXAM_LIFECYCLE_PUBLISHED,
        published_at=now,
        published_by=user,
        marks_status=MARKS_STATUS_DRAFT,
        created_by=user,
        updated_by=user,
    )


def assignment_options_payload(
    tenant,
    user,
    *,
    subject_id=None,
    paper_id=None,
    school_class_id=None,
    assessment_id=None,
) -> dict[str, Any]:
    from apps.examinations.reference import academic_year_options, current_academic_year

    year = current_academic_year(tenant)
    data: dict[str, Any] = {
        "scope_meta": assignment_scope_meta(tenant, user),
        "subjects": marks_subject_options(tenant, user),
        "academic_years": academic_year_options(tenant),
        "current_academic_year": str(year.id) if year else None,
        "papers": [],
        "requires_paper": False,
        "classes": [],
        "assessments": [],
        "students": [],
        "grades": {},
        "exam_detail": None,
    }

    if not subject_id:
        return data

    papers = paper_options(tenant, subject_id)
    data["papers"] = papers
    data["requires_paper"] = len(papers) > 0

    if not school_class_id:
        data["classes"] = marks_class_options(
            tenant,
            subject_id=subject_id,
            academic_year_id=str(year.id) if year else None,
            user=user,
        )
        return data

    data["assessments"] = assignment_assessment_options(
        tenant,
        subject_id=subject_id,
        school_class_id=school_class_id,
        paper_id=paper_id,
        user=user,
    )

    if not assessment_id:
        return data

    try:
        exam = _assignment_exam_queryset(tenant, user).get(pk=assessment_id)
    except Exam.DoesNotExist as exc:
        raise AssignmentMarksError("Assignment not found for the selected filters.", code="not_found") from exc

    if not user_can_write_assignment_marks(user, exam):
        raise AssignmentMarksError(
            "You may only enter marks for your assigned subjects and classes.",
            code="forbidden",
        )

    normalized_paper = _normalize_paper_filter(paper_id)
    if normalized_paper == "invalid":
        raise AssignmentMarksError("Invalid paper selection.", code="invalid_paper")
    if normalized_paper and exam.paper_id != normalized_paper:
        raise AssignmentMarksError("Assignment does not match the selected paper.", code="paper_mismatch")
    if not normalized_paper and exam.paper_id is not None:
        raise AssignmentMarksError("Assignment does not match the selected paper.", code="paper_mismatch")

    from apps.examinations.models import Grade
    from apps.examinations.serializers import ExamSerializer
    from apps.students.models import Student
    from apps.students.serializers import StudentListSerializer

    students = Student.objects.filter(
        tenant=tenant,
        school_class_id=exam.school_class_id,
        status="active",
    ).order_by("last_name", "first_name")

    grade_rows = Grade.objects.filter(tenant=tenant, exam=exam, is_deleted=False).select_related("student")
    data["exam_detail"] = ExamSerializer(exam).data
    data["students"] = StudentListSerializer(students, many=True).data
    data["grades"] = {
        str(g.student_id): {
            "id": str(g.id),
            "score": str(g.score),
            "grade": g.grade,
            "remarks": g.remarks,
        }
        for g in grade_rows
    }
    data["marks_count"] = grade_rows.count()
    return data