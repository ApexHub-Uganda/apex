"""Bulk import specs and commit handlers for students and parents."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from django.db import transaction

from apps.academics.models import Class, Stream
from apps.academics.class_hub import user_can_enroll_students
from apps.academics.scoping import get_academic_context, user_can_access_class, user_has_school_wide_academic_access
from apps.core.bulk_import import ImportColumn, ImportSpec
from apps.students.models import Parent, Student
from apps.students.profile import IMPORT_PLACEHOLDER_DOB, generate_admission_number


STUDENT_IMPORT_SPEC = ImportSpec(
    entity_name="Students",
    description=(
        "Quick class or stream enrollment with student name and sex (M or F). "
        "Choose the class and stream before uploading — every row is assigned to that group. "
        "Complete email, phone, UPI, date of birth, parents, and other details in each profile later."
    ),
    columns=[
        ImportColumn("first_name", "First Name", required=True),
        ImportColumn("last_name", "Last Name", required=True),
        ImportColumn("gender", "Sex", required=True, help_text="M = Male, F = Female"),
    ],
)


PARENT_IMPORT_SPEC = ImportSpec(
    entity_name="Parents",
    description=(
        "Quick parent/guardian registration with name, email, and phone. "
        "Address, M-Pesa, relationship, and fee settings can be completed in the parent profile later."
    ),
    columns=[
        ImportColumn("first_name", "First Name", required=True),
        ImportColumn("last_name", "Last Name", required=True),
        ImportColumn("email", "Email", required=True, field_type="email"),
        ImportColumn("phone", "Phone", required=True, field_type="phone"),
    ],
)


@dataclass
class StudentImportContext:
    school_class_id: str | None = None
    stream_id: str | None = None

    def validate_access(self, tenant, user) -> tuple[Class | None, Stream | None, list[dict[str, Any]]]:
        errors: list[dict[str, Any]] = []
        if not self.school_class_id:
            errors.append({"row": 0, "field": "school_class", "message": "Select a class before importing."})
            return None, None, errors

        if not user_can_access_class(user, self.school_class_id):
            errors.append({"row": 0, "field": "school_class", "message": "You do not have access to this class."})
            return None, None, errors
        if not user_can_enroll_students(user, school_class_id=self.school_class_id):
            errors.append({
                "row": 0,
                "field": "school_class",
                "message": "You do not have permission to enroll students into this class.",
            })
            return None, None, errors

        school_class = Class.objects.filter(tenant=tenant, pk=self.school_class_id, is_deleted=False).first()
        if school_class is None:
            errors.append({"row": 0, "field": "school_class", "message": "Class not found."})
            return None, None, errors

        stream = None
        streams_exist = Stream.objects.filter(
            tenant=tenant,
            school_class_id=school_class.id,
            is_deleted=False,
        ).exists()

        if streams_exist and not self.stream_id:
            errors.append({
                "row": 0,
                "field": "stream",
                "message": "This class has streams. Select a stream before importing.",
            })
            return school_class, None, errors

        if self.stream_id:
            stream = Stream.objects.filter(
                tenant=tenant,
                pk=self.stream_id,
                school_class_id=school_class.id,
                is_deleted=False,
            ).first()
            if stream is None:
                errors.append({
                    "row": 0,
                    "field": "stream",
                    "message": "Stream not found in the selected class.",
                })

        return school_class, stream, errors


def get_student_import_context(user) -> dict[str, Any]:
    """Classes and defaults for the bulk import wizard."""
    ctx = get_academic_context(user)
    if ctx is None or ctx.tenant is None:
        return {"classes": [], "default_class_id": None, "default_stream_id": None, "is_class_teacher": False}

    from apps.academics.scoping import filter_queryset_for_user

    classes_qs = filter_queryset_for_user(
        Class.objects.filter(tenant=ctx.tenant, is_deleted=False).select_related("academic_year"),
        user,
    ).order_by("name")

    class_teacher_ids = list(ctx.class_teacher_class_ids)
    classes = []
    for school_class in classes_qs:
        streams = list(
            Stream.objects.filter(
                tenant=ctx.tenant,
                school_class_id=school_class.id,
                is_deleted=False,
            ).order_by("name").values("id", "name"),
        )
        classes.append({
            "id": str(school_class.id),
            "name": school_class.name,
            "code": school_class.code,
            "is_class_teacher": school_class.id in class_teacher_ids,
            "can_enroll": user_can_enroll_students(user, school_class_id=str(school_class.id)),
            "has_streams": len(streams) > 0,
            "streams": [{"id": str(s["id"]), "name": s["name"]} for s in streams],
        })

    default_class_id = None
    default_stream_id = None
    is_class_teacher = bool(class_teacher_ids)

    if is_class_teacher and len(class_teacher_ids) == 1:
        default_class_id = str(class_teacher_ids[0])
        default_class = next((row for row in classes if row["id"] == default_class_id), None)
        if default_class and len(default_class["streams"]) == 1:
            default_stream_id = default_class["streams"][0]["id"]

    return {
        "classes": classes,
        "default_class_id": default_class_id,
        "default_stream_id": default_stream_id,
        "is_class_teacher": is_class_teacher,
        "is_unrestricted": user_has_school_wide_academic_access(user),
        "can_enroll_students": user_can_enroll_students(user),
        "can_enroll_in_default_class": (
            user_can_enroll_students(user, school_class_id=default_class_id)
            if default_class_id else False
        ),
    }


def student_import_resolver(tenant, *, context: StudentImportContext, user):
    school_class, stream, context_errors = context.validate_access(tenant, user)

    def resolver(row: dict[str, Any], row_num: int) -> list[dict[str, Any]]:
        errors = list(context_errors)
        if errors:
            return errors

        gender = row.get("gender")
        if gender in ("male", "female"):
            row["gender"] = gender
        elif gender:
            row["gender"] = str(gender).lower()

        if school_class is not None:
            row["_school_class_id"] = str(school_class.id)
        if stream is not None:
            row["_stream_id"] = str(stream.id)

        row.setdefault("date_of_birth", IMPORT_PLACEHOLDER_DOB)
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
        row.setdefault("date_of_birth", IMPORT_PLACEHOLDER_DOB)
        row.setdefault("gender", "other")

        if not row.get("admission_number") and school_class_id:
            school_class = Class.objects.filter(tenant=tenant, pk=school_class_id).first()
            if school_class is not None:
                row["admission_number"] = generate_admission_number(tenant, school_class=school_class)

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
            "Open each profile to add date of birth, UPI, parents, and other information."
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