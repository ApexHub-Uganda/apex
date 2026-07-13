"""Grading scheme helpers — band resolution and mark-sheet application."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.examinations.models import Exam, Grade, GradingScheme, GradingSchemeBand


class GradingSchemeError(Exception):
    def __init__(self, message: str, *, code: str = "grading_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def normalize_score(score: Decimal, *, max_score: Decimal | None = None) -> Decimal:
    if max_score and max_score > 0:
        return (score / max_score) * Decimal("100")
    return score


def resolve_band(
    bands: list[GradingSchemeBand],
    score: Decimal,
    *,
    max_score: Decimal | None = None,
) -> GradingSchemeBand | None:
    normalized = normalize_score(score, max_score=max_score)
    for band in bands:
        if band.min_score <= normalized <= band.max_score:
            return band
    return None


def resolve_letter_grade_from_scheme(
    scheme: GradingScheme,
    score: Decimal,
    *,
    max_score: Decimal | None = None,
) -> tuple[str, str]:
    bands = list(
        scheme.bands.filter(is_deleted=False).order_by("-min_score"),
    )
    band = resolve_band(bands, score, max_score=max_score)
    if band is None:
        return "", ""
    return band.grade, band.remarks or ""


@transaction.atomic
def sync_scheme_bands(
    *,
    tenant,
    scheme: GradingScheme,
    bands: list[dict[str, Any]],
    user,
) -> GradingScheme:
    """Replace all bands on a grading scheme."""
    if not bands:
        raise GradingSchemeError("Add at least one grade band.", code="bands_required")

    seen: set[tuple[str, str, str]] = set()
    for row in bands:
        grade = str(row.get("grade", "")).strip()
        if not grade:
            raise GradingSchemeError("Each band needs a letter grade.", code="invalid_band")
        key = (grade, str(row.get("min_score")), str(row.get("max_score")))
        if key in seen:
            raise GradingSchemeError("Duplicate grade bands are not allowed.", code="duplicate_band")
        seen.add(key)

    target_grades = {str(row["grade"]).strip() for row in bands}
    existing = GradingSchemeBand.objects.filter(tenant=tenant, scheme=scheme, is_deleted=False)
    for row in existing:
        if row.grade not in target_grades:
            row.soft_delete(user=user)

    for row in bands:
        band, _created = GradingSchemeBand.all_objects.get_or_create(
            tenant=tenant,
            scheme=scheme,
            grade=str(row["grade"]).strip(),
            defaults={
                "min_score": row["min_score"],
                "max_score": row["max_score"],
                "grade_point": row.get("grade_point"),
                "remarks": row.get("remarks", ""),
                "created_by": user,
                "updated_by": user,
                "is_deleted": False,
            },
        )
        band.is_deleted = False
        band.min_score = row["min_score"]
        band.max_score = row["max_score"]
        band.grade_point = row.get("grade_point")
        band.remarks = row.get("remarks", "")
        band.updated_by = user
        band.save(update_fields=[
            "is_deleted", "min_score", "max_score", "grade_point", "remarks", "updated_by", "updated_at",
        ])

    return scheme


@transaction.atomic
def apply_grading_scheme(
    *,
    tenant,
    exam: Exam,
    scheme: GradingScheme,
    user,
) -> dict[str, Any]:
    """Apply a grading scheme to all entered marks for an exam."""
    bands = list(scheme.bands.filter(is_deleted=False).order_by("-min_score"))
    if not bands:
        raise GradingSchemeError("This grading scheme has no bands configured.", code="empty_scheme")

    grades = Grade.objects.filter(tenant=tenant, exam=exam, is_deleted=False).select_related("student")
    if not grades.exists():
        raise GradingSchemeError(
            "No marks have been entered for this assessment yet. Enter marks first.",
            code="no_marks",
        )

    updated = 0
    unmapped = 0
    rows: list[dict[str, Any]] = []
    for grade_row in grades.order_by("student__last_name", "student__first_name"):
        band = resolve_band(bands, grade_row.score, max_score=exam.max_score)
        if band is None:
            unmapped += 1
            letter = ""
            band_remarks = ""
        else:
            letter = band.grade
            band_remarks = band.remarks or ""
            updated += 1

        grade_row.grade = letter
        if band_remarks and not grade_row.remarks:
            grade_row.remarks = band_remarks
        grade_row.updated_by = user
        grade_row.save(update_fields=["grade", "remarks", "updated_by", "updated_at"])

        rows.append({
            "student_id": str(grade_row.student_id),
            "student_name": grade_row.student.full_name,
            "admission_number": grade_row.student.admission_number,
            "score": str(grade_row.score),
            "grade": letter,
            "remarks": grade_row.remarks,
            "max_score": str(exam.max_score),
        })

    return {
        "updated_count": updated,
        "unmapped_count": unmapped,
        "total_count": len(rows),
        "rows": rows,
        "scheme_name": scheme.name,
        "exam_name": exam.name,
    }