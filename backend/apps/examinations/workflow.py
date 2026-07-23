"""Marks approval and assessment lifecycle workflow."""
from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.examinations.constants import (
    EXAM_LIFECYCLE_ARCHIVED,
    EXAM_LIFECYCLE_DRAFT,
    EXAM_LIFECYCLE_PUBLISHED,
    MARKS_EDITABLE_STATUSES,
    MARKS_STATUS_APPROVED,
    MARKS_STATUS_DRAFT,
    MARKS_STATUS_LOCKED,
    MARKS_STATUS_SUBMITTED,
)
from apps.academics.scoping import user_has_school_wide_academic_access
from apps.core.constants import UserRole, normalize_role
from apps.examinations.models import Exam, Grade


class MarksWorkflowError(Exception):
    def __init__(self, message: str, *, code: str = "workflow_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def exam_marks_are_editable(exam: Exam) -> bool:
    return exam.marks_status in MARKS_EDITABLE_STATUSES


def exam_allows_mark_entry(exam: Exam) -> bool:
    """Teachers may enter marks once an exam is scheduled (draft or published)."""
    if exam.exam_type == "assignment":
        return exam_marks_are_editable(exam)
    if exam.lifecycle_status == EXAM_LIFECYCLE_ARCHIVED:
        return False
    # Draft (just scheduled) and published both allow mark entry; archived does not.
    return exam_marks_are_editable(exam)


@transaction.atomic
def publish_exam(*, exam: Exam, user) -> Exam:
    if exam.lifecycle_status == EXAM_LIFECYCLE_ARCHIVED:
        raise MarksWorkflowError("Archived assessments cannot be published.", code="archived")
    exam.lifecycle_status = EXAM_LIFECYCLE_PUBLISHED
    exam.published_at = timezone.now()
    exam.published_by = user
    exam.updated_by = user
    exam.save(update_fields=[
        "lifecycle_status", "published_at", "published_by", "updated_by", "updated_at",
    ])
    return exam


@transaction.atomic
def archive_exam(*, exam: Exam, user) -> Exam:
    exam.lifecycle_status = EXAM_LIFECYCLE_ARCHIVED
    exam.updated_by = user
    exam.save(update_fields=["lifecycle_status", "updated_by", "updated_at"])
    return exam


@transaction.atomic
def submit_exam_marks(*, exam: Exam, user) -> Exam:
    if exam.lifecycle_status == EXAM_LIFECYCLE_ARCHIVED:
        raise MarksWorkflowError("Archived assessments cannot be submitted.", code="archived")
    # Auto-publish draft schedules so submit can proceed after teachers enter marks.
    if exam.lifecycle_status == EXAM_LIFECYCLE_DRAFT:
        exam.lifecycle_status = EXAM_LIFECYCLE_PUBLISHED
        exam.published_at = timezone.now()
        exam.published_by = user
    if exam.lifecycle_status != EXAM_LIFECYCLE_PUBLISHED:
        raise MarksWorkflowError("Only published assessments can be submitted for approval.", code="not_published")
    if exam.marks_status != MARKS_STATUS_DRAFT:
        raise MarksWorkflowError("Marks have already been submitted or finalized.", code="invalid_status")
    if not exam.grades.filter(is_deleted=False).exists():
        raise MarksWorkflowError("Enter at least one mark before submitting.", code="no_grades")

    now = timezone.now()
    exam.marks_status = MARKS_STATUS_SUBMITTED
    exam.marks_submitted_at = now
    exam.marks_submitted_by = user
    exam.updated_by = user
    exam.save(update_fields=[
        "lifecycle_status", "published_at", "published_by",
        "marks_status", "marks_submitted_at", "marks_submitted_by", "updated_by", "updated_at",
    ])
    exam.grades.filter(is_deleted=False).update(
        entry_status=MARKS_STATUS_SUBMITTED,
        updated_by=user,
    )
    return exam


@transaction.atomic
def approve_exam_marks(*, exam: Exam, user) -> Exam:
    if exam.marks_status != MARKS_STATUS_SUBMITTED:
        raise MarksWorkflowError("Only submitted marks can be approved.", code="invalid_status")

    now = timezone.now()
    exam.marks_status = MARKS_STATUS_APPROVED
    exam.marks_approved_at = now
    exam.marks_approved_by = user
    exam.updated_by = user
    exam.save(update_fields=[
        "marks_status", "marks_approved_at", "marks_approved_by", "updated_by", "updated_at",
    ])
    exam.grades.filter(is_deleted=False).update(
        entry_status=MARKS_STATUS_APPROVED,
        updated_by=user,
    )
    return exam


@transaction.atomic
def lock_exam_marks(*, exam: Exam, user) -> Exam:
    if exam.marks_status not in {MARKS_STATUS_SUBMITTED, MARKS_STATUS_APPROVED}:
        raise MarksWorkflowError("Only submitted or approved marks can be locked.", code="invalid_status")

    now = timezone.now()
    exam.marks_status = MARKS_STATUS_LOCKED
    exam.marks_locked_at = now
    exam.marks_locked_by = user
    exam.updated_by = user
    exam.save(update_fields=[
        "marks_status", "marks_locked_at", "marks_locked_by", "updated_by", "updated_at",
    ])
    exam.grades.filter(is_deleted=False).update(
        entry_status=MARKS_STATUS_LOCKED,
        updated_by=user,
    )
    return exam


def user_can_reopen_marks(user) -> bool:
    """Only Director of Studies and school admins may reopen locked marks."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user_has_school_wide_academic_access(user):
        return True
    return normalize_role(getattr(user, "role", "")) == UserRole.DIRECTOR_OF_STUDIES


@transaction.atomic
def reopen_exam_marks(*, exam: Exam, user, reason: str = "") -> Exam:
    if not user_can_reopen_marks(user):
        raise MarksWorkflowError(
            "Only the Director of Studies can reopen finalized marks.",
            code="forbidden_reopen",
        )
    if exam.marks_status not in {MARKS_STATUS_APPROVED, MARKS_STATUS_LOCKED}:
        raise MarksWorkflowError("Only approved or locked marks can be reopened.", code="invalid_status")

    now = timezone.now()
    exam.marks_status = MARKS_STATUS_DRAFT
    exam.marks_reopened_at = now
    exam.marks_reopened_by = user
    exam.marks_reopen_reason = (reason or "").strip()
    exam.marks_submitted_at = None
    exam.marks_submitted_by = None
    exam.marks_approved_at = None
    exam.marks_approved_by = None
    exam.marks_locked_at = None
    exam.marks_locked_by = None
    exam.updated_by = user
    exam.save(update_fields=[
        "marks_status",
        "marks_reopened_at", "marks_reopened_by", "marks_reopen_reason",
        "marks_submitted_at", "marks_submitted_by",
        "marks_approved_at", "marks_approved_by",
        "marks_locked_at", "marks_locked_by",
        "updated_by", "updated_at",
    ])
    exam.grades.filter(is_deleted=False).update(
        entry_status=MARKS_STATUS_DRAFT,
        updated_by=user,
    )
    return exam


@transaction.atomic
def bulk_workflow_action(*, exams, user, action: str) -> dict[str, Any]:
    """Run approve, lock, or publish across multiple exams."""
    processed: list[str] = []
    errors: list[dict[str, str]] = []

    handlers = {
        "approve": approve_exam_marks,
        "lock": lock_exam_marks,
        "publish": publish_exam,
        "archive": archive_exam,
    }
    handler = handlers.get(action)
    if handler is None:
        raise MarksWorkflowError(f"Unknown bulk action: {action}", code="invalid_action")

    for exam in exams:
        try:
            handler(exam=exam, user=user)
            processed.append(str(exam.id))
        except MarksWorkflowError as exc:
            errors.append({"exam": str(exam.id), "message": exc.message, "code": exc.code})

    return {"processed": processed, "errors": errors}


def sync_grade_entry_status(*, grade: Grade, exam: Exam) -> None:
    """Keep grade entry status aligned with the parent exam on create/update."""
    if exam.marks_status == MARKS_STATUS_LOCKED:
        grade.entry_status = MARKS_STATUS_LOCKED
    elif exam.marks_status == MARKS_STATUS_APPROVED:
        grade.entry_status = MARKS_STATUS_APPROVED
    elif exam.marks_status == MARKS_STATUS_SUBMITTED:
        grade.entry_status = MARKS_STATUS_SUBMITTED
    else:
        grade.entry_status = MARKS_STATUS_DRAFT