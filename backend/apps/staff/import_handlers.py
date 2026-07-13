"""Bulk import for staff records (no portal access by default)."""
from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.academics.models import Department
from apps.core.bulk_import import ImportColumn, ImportSpec
from apps.core.constants import UserRole
from apps.staff.models import Staff
from apps.staff.services import StaffOnboardingError, onboard_staff

# Minimal columns — HR completes full profiles in the staff workspace afterwards.
STAFF_IMPORT_SPEC = ImportSpec(
    entity_name="Staff",
    description=(
        "Quick staff list with name, work email, and phone. HR completes role, department, "
        "and portal access in each staff profile later; staff complete personal details in My Profile."
    ),
    columns=[
        ImportColumn("first_name", "First Name", required=True),
        ImportColumn("last_name", "Last Name", required=True),
        ImportColumn("email", "Email", required=True, field_type="email"),
        ImportColumn("phone", "Phone", required=True, field_type="phone"),
    ],
)


def staff_import_resolver(tenant):
    def resolver(row: dict[str, Any], row_num: int) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []
        email = row.get("email", "")
        if Staff.objects.filter(tenant=tenant, email__iexact=email, is_deleted=False).exists():
            errors.append({
                "row": row_num,
                "field": "email",
                "message": f"Staff with email '{email}' already exists",
            })

        emp_id = row.get("employee_id")
        if emp_id and Staff.objects.filter(tenant=tenant, employee_id__iexact=emp_id).exists():
            errors.append({
                "row": row_num,
                "field": "employee_id",
                "message": f"Employee ID '{emp_id}' already exists",
            })

        dept_code = row.get("department_code")
        if dept_code:
            dept = Department.objects.filter(tenant=tenant, code__iexact=dept_code.strip()).first()
            if not dept:
                errors.append({
                    "row": row_num,
                    "field": "department_code",
                    "message": f"Department code '{dept_code}' not found",
                })
            else:
                row["_department_id"] = str(dept.id)

        return errors

    return resolver


@transaction.atomic
def commit_staff_rows(tenant, rows: list[dict], *, actor=None) -> dict[str, Any]:
    created = 0
    errors: list[dict[str, Any]] = []

    for row in rows:
        row_num = row.get("_row_number", 0)
        department_id = row.pop("_department_id", None)
        row.pop("_row_number", None)
        row.pop("department_code", None)

        data = {
            "employee_id": row.get("employee_id") or "",
            "first_name": row["first_name"],
            "middle_name": row.get("middle_name", ""),
            "last_name": row["last_name"],
            "email": row["email"],
            "phone": row["phone"],
            "personal_email": row.get("personal_email", ""),
            "alternate_phone": row.get("alternate_phone", ""),
            "gender": row.get("gender", ""),
            "date_of_birth": row.get("date_of_birth"),
            "national_id": row.get("national_id", ""),
            "nationality": row.get("nationality", "Kenyan"),
            "portal_role": row.get("portal_role", UserRole.TEACHER),
            "staff_category": row.get("staff_category", ""),
            "designation": row.get("designation", ""),
            "department": department_id,
            "date_joined": row.get("date_joined"),
            "employment_type": row.get("employment_type", "full_time"),
            "status": row.get("status", "active"),
            "address": row.get("address", ""),
            "emergency_contact": row.get("emergency_contact", ""),
            "emergency_phone": row.get("emergency_phone", ""),
            "has_portal_access": row.get("has_portal_access", False),
            "qualification_summary": row.get("qualification_summary", ""),
            "notes": row.get("notes", ""),
        }

        try:
            onboard_staff(tenant, actor=actor, data=data)
            created += 1
        except StaffOnboardingError as exc:
            errors.append({"row": row_num, "field": "", "message": str(exc)})

    message = (
        f"Imported {created} staff member(s) with basic details. "
        "Open each profile to assign roles, departments, and portal access."
    )
    if errors:
        message += f" {len(errors)} row(s) failed."

    return {"created": created, "errors": errors, "message": message}