"""Examination workflow helpers."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction

from apps.examinations.models import Exam, Grade, GradingScale
from apps.examinations.workflow import MarksWorkflowError, exam_allows_mark_entry, sync_grade_entry_status


def resolve_letter_grade(tenant, score: Decimal, *, max_score: Decimal | None = None) -> str:
    """Map a numeric score to a letter grade using tenant grading scales."""
    if score is None:
        return ""
    scales = GradingScale.objects.filter(tenant=tenant).order_by("-min_score")
    if not scales.exists():
        return ""

    if max_score and max_score > 0:
        normalized = (score / max_score) * Decimal("100")
    else:
        normalized = score

    for entry in scales:
        if entry.min_score <= normalized <= entry.max_score:
            return entry.grade
    return ""


@transaction.atomic
def bulk_upsert_grades(
    *,
    tenant,
    exam: Exam,
    entries: list[dict[str, Any]],
    user,
) -> dict[str, Any]:
    if not exam_allows_mark_entry(exam):
        raise MarksWorkflowError(
            "Marks cannot be edited for this assessment in its current status.",
            code="marks_locked",
        )

    saved = 0
    skipped = 0
    errors: list[dict[str, str]] = []

    for row in entries:
        student_id = row.get("student")
        if not student_id:
            skipped += 1
            continue

        raw_score = row.get("score")
        if raw_score in (None, ""):
            existing = Grade.objects.filter(tenant=tenant, exam=exam, student_id=student_id).first()
            if existing:
                existing.soft_delete(user=user)
                saved += 1
            else:
                skipped += 1
            continue

        try:
            score = Decimal(str(raw_score))
        except (InvalidOperation, TypeError, ValueError):
            errors.append({"student": str(student_id), "message": "Invalid score value."})
            continue

        if score < 0 or score > exam.max_score:
            errors.append({
                "student": str(student_id),
                "message": f"Score must be between 0 and {exam.max_score}.",
            })
            continue

        remarks = (row.get("remarks") or "").strip()

        grade, _created = Grade.objects.update_or_create(
            tenant=tenant,
            exam=exam,
            student_id=student_id,
            defaults={
                "score": score,
                "grade": "",
                "remarks": remarks,
                "updated_by": user,
            },
        )
        sync_grade_entry_status(grade=grade, exam=exam)
        if _created:
            grade.created_by = user
            grade.save(update_fields=["created_by", "entry_status"])
        else:
            grade.save(update_fields=["entry_status"])
        saved += 1

    return {"saved": saved, "skipped": skipped, "errors": errors}