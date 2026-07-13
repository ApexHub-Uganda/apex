"""Student profile completeness helpers."""
from __future__ import annotations

from datetime import date

from apps.students.models import Student

# Placeholder DOB for bulk-imported students — replaced when profile is completed.
IMPORT_PLACEHOLDER_DOB = date(1900, 1, 1)


def is_profile_incomplete(student: Student) -> bool:
    """True when essential profile fields beyond import minimum are still missing."""
    if student.date_of_birth == IMPORT_PLACEHOLDER_DOB:
        return True
    if not (student.upi_number or "").strip():
        return True
    if not student.parents.filter(is_deleted=False).exists():
        return True
    if not (student.county or "").strip():
        return True
    return False


def count_incomplete_students(queryset_or_list) -> int:
    if hasattr(queryset_or_list, "prefetch_related"):
        students = queryset_or_list.prefetch_related("parents")
    else:
        students = queryset_or_list
    total = 0
    for student in students:
        if is_profile_incomplete(student):
            total += 1
    return total


def generate_admission_number(tenant, *, school_class) -> str:
    """Generate a unique admission number for quick-enrollment imports."""
    year = date.today().year
    code = (school_class.code or "CLS").upper().replace(" ", "")
    prefix = f"{code}-{year}-"
    existing = Student.objects.filter(
        tenant=tenant,
        admission_number__istartswith=prefix,
    ).count()
    candidate = f"{prefix}{existing + 1:04d}"
    while Student.objects.filter(tenant=tenant, admission_number=candidate).exists():
        existing += 1
        candidate = f"{prefix}{existing + 1:04d}"
    return candidate