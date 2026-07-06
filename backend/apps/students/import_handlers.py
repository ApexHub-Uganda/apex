"""Bulk import specs and commit handlers for students and parents."""
from __future__ import annotations

from datetime import date
from typing import Any

from django.db import transaction

from apps.academics.models import Class, Stream
from apps.core.bulk_import import ImportColumn, ImportSpec
from apps.students.models import Parent, Student

# Minimal columns only — full profiles are completed later in the workspace.
STUDENT_IMPORT_SPEC = ImportSpec(
    entity_name="Students",
    description=(
        "Quick enrollment with essentials only. Class teachers complete UPI, parents, "
        "and other details in the student profile afterwards."
    ),
    columns=[
        ImportColumn("admission_number", "Admission Number", required=True, help_text="Unique per school"),
        ImportColumn("first_name", "First Name", required=True),
        ImportColumn("last_name", "Last Name", required=True),
        ImportColumn("date_of_birth", "Date of Birth", required=True, field_type="date", help_text="YYYY-MM-DD"),
        ImportColumn("gender", "Gender", required=True, choices=["male", "female", "other"]),
        ImportColumn("class_code", "Class Code", required=True, help_text="Must match an existing class e.g. G7A"),
    ],
)


PARENT_IMPORT_SPEC = ImportSpec(
    entity_name="Parents",
    description=(
        "Quick parent/guardian registration with contact essentials. "
        "M-Pesa, address, and fee settings can be added in the full profile later."
    ),
    columns=[
        ImportColumn("first_name", "First Name", required=True),
        ImportColumn("last_name", "Last Name", required=True),
        ImportColumn("phone", "Phone", required=True, field_type="phone"),
        ImportColumn("email", "Email", required=True, field_type="email"),
    ],
)


def _resolve_class(tenant, class_code: str, academic_year_name: str | None):
    from apps.academics.models import AcademicYear

    qs = Class.objects.filter(tenant=tenant, code__iexact=class_code.strip())
    if academic_year_name:
        qs = qs.filter(academic_year__name__iexact=academic_year_name.strip())
    else:
        current = AcademicYear.objects.filter(tenant=tenant, is_current=True).first()
        if current:
            qs = qs.filter(academic_year=current)
    return qs.select_related("academic_year").first()


def student_import_resolver(tenant):
    def resolver(row: dict[str, Any], row_num: int) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []
        admission = row.get("admission_number", "")
        if Student.objects.filter(tenant=tenant, admission_number__iexact=admission).exists():
            errors.append({
                "row": row_num,
                "field": "admission_number",
                "message": f"Admission number '{admission}' already exists",
            })

        class_code = row.get("class_code", "")
        school_class = _resolve_class(tenant, class_code, row.get("academic_year"))
        if not school_class:
            errors.append({
                "row": row_num,
                "field": "class_code",
                "message": f"Class code '{class_code}' not found for the current academic year",
            })
        else:
            row["_school_class_id"] = str(school_class.id)

        stream_name = row.get("stream_name")
        if stream_name and school_class:
            stream = Stream.objects.filter(
                tenant=tenant, school_class=school_class, name__iexact=stream_name.strip(),
            ).first()
            if not stream:
                errors.append({
                    "row": row_num,
                    "field": "stream_name",
                    "message": f"Stream '{stream_name}' not found in class {class_code}",
                })
            else:
                row["_stream_id"] = str(stream.id)

        return errors

    return resolver


def parent_import_resolver(tenant):
    def resolver(row: dict[str, Any], row_num: int) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []
        email = row.get("email", "")
        if Parent.objects.filter(tenant=tenant, email__iexact=email).exists():
            errors.append({
                "row": row_num,
                "field": "email",
                "message": f"Parent with email '{email}' already exists",
            })
        return errors

    return resolver


@transaction.atomic
def commit_student_rows(tenant, rows: list[dict], *, actor=None) -> dict[str, Any]:
    created = 0
    today = date.today()
    for row in rows:
        parent_id = row.pop("_parent_id", None)
        school_class_id = row.pop("_school_class_id", None)
        stream_id = row.pop("_stream_id", None)
        row.pop("_row_number", None)
        row.pop("class_code", None)
        row.pop("stream_name", None)
        row.pop("academic_year", None)

        row.setdefault("enrollment_date", today)
        row.setdefault("status", "active")
        row.setdefault("nationality", "Kenyan")
        row.setdefault("curriculum_pathway", "cbc")
        row.setdefault("boarding_status", "day")
        row.setdefault("special_needs", False)

        student = Student.objects.create(
            tenant=tenant,
            school_class_id=school_class_id,
            stream_id=stream_id,
            created_by=actor,
            updated_by=actor,
            **{k: v for k, v in row.items() if k in {
                "admission_number", "first_name", "middle_name", "last_name",
                "date_of_birth", "gender", "enrollment_date", "status",
                "upi_number", "birth_certificate_number", "email", "phone",
                "address", "city", "county", "sub_county", "ward",
                "nationality", "religion", "place_of_birth", "previous_school",
                "curriculum_pathway", "boarding_status", "special_needs",
                "special_needs_details", "emergency_contact_name",
                "emergency_contact_phone", "notes",
            }},
        )
        if parent_id:
            student.parents.add(parent_id)
        created += 1

    return {
        "created": created,
        "message": (
            f"Enrolled {created} student(s) with basic details. "
            "Open each profile to complete the full record."
        ),
    }


@transaction.atomic
def commit_parent_rows(tenant, rows: list[dict], *, actor=None) -> dict[str, Any]:
    created = 0
    for row in rows:
        row.pop("_row_number", None)
        row.setdefault("country", "Kenya")
        row.setdefault("relationship_to_student", "guardian")
        row.setdefault("preferred_contact_method", "sms")
        row.setdefault("consent_for_sms", True)
        row.setdefault("is_fee_payer", False)

        Parent.objects.create(
            tenant=tenant,
            created_by=actor,
            updated_by=actor,
            **{k: v for k, v in row.items() if k in {
                "first_name", "middle_name", "last_name", "email", "phone",
                "alternate_email", "alternate_phone", "gender", "national_id",
                "occupation", "employer", "relationship_to_student", "address",
                "city", "county", "sub_county", "country", "postal_code",
                "mpesa_phone", "is_fee_payer", "consent_for_sms",
                "preferred_contact_method", "notes",
            }},
        )
        created += 1

    return {
        "created": created,
        "message": (
            f"Imported {created} parent(s) with basic contact details. "
            "Complete profiles individually when ready."
        ),
    }