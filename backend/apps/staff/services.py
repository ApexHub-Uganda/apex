"""Staff onboarding — atomic profile + portal account provisioning."""
from __future__ import annotations

import secrets
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.core.constants import UserRole
from apps.staff.models import Staff, Teacher
from apps.staff.staff_roles import get_role_definition, role_requires_teacher_profile

User = get_user_model()


class StaffOnboardingError(Exception):
    pass


def _coerce_uuid_pk(value: Any) -> Any:
    """Normalize FK payloads that may be UUID strings, model instances, or empty."""
    if value in (None, ""):
        return None
    if hasattr(value, "pk"):
        return value.pk
    return value


def _next_employee_id(tenant) -> str:
    prefix = tenant.code or "EMP"
    count = Staff.all_objects.filter(tenant=tenant).count() + 1
    candidate = f"{prefix}-EMP{count:04d}"
    while Staff.all_objects.filter(tenant=tenant, employee_id=candidate).exists():
        count += 1
        candidate = f"{prefix}-EMP{count:04d}"
    return candidate


def _generate_temp_password() -> str:
    return secrets.token_urlsafe(12)


@transaction.atomic
def onboard_staff(
    tenant,
    *,
    actor=None,
    data: dict[str, Any],
) -> Staff:
    """Create staff record and optional linked portal user + teacher profile."""
    email = (data.get("email") or "").strip().lower()
    if not email:
        raise StaffOnboardingError("Work email is required for all staff.")

    portal_role = data.get("portal_role") or UserRole.TEACHER
    if portal_role == UserRole.SCHOOL_ADMIN:
        raise StaffOnboardingError("Use school settings to manage school administrators.")

    has_portal_access = bool(data.get("has_portal_access", True))
    employee_id = (data.get("employee_id") or "").strip() or _next_employee_id(tenant)

    if Staff.all_objects.filter(tenant=tenant, employee_id=employee_id).exists():
        raise StaffOnboardingError(f"Employee ID '{employee_id}' already exists.")

    if Staff.all_objects.filter(tenant=tenant, email__iexact=email, is_deleted=False).exists():
        raise StaffOnboardingError("A staff member with this work email already exists.")

    role_def = get_role_definition(portal_role)
    staff_category = data.get("staff_category") or role_def["category"]
    designation = data.get("designation") or role_def["default_designation"]

    user = None
    temp_password = None
    if has_portal_access:
        if User.objects.filter(email__iexact=email).exists():
            raise StaffOnboardingError(
                "This email is already registered as a portal user. Use a different work email."
            )
        admin_supplied_password = bool((data.get("password") or "").strip())
        temp_password = data.get("password") or _generate_temp_password()
        user = User.objects.create_user(
            email=email,
            password=temp_password,
            first_name=data["first_name"],
            last_name=data["last_name"],
            phone=data.get("phone", ""),
            role=portal_role,
            tenant=tenant,
            is_active=True,
            is_email_verified=bool(data.get("mark_email_verified", False)),
        )
        if not admin_supplied_password:
            user.must_change_password = True
            user.save(update_fields=["must_change_password", "updated_at"])
            from apps.staff.portal_credentials import send_staff_portal_credentials_email

            send_staff_portal_credentials_email(
                user=user,
                tenant=tenant,
                temp_password=temp_password,
            )

    staff = Staff.objects.create(
        tenant=tenant,
        user=user,
        employee_id=employee_id,
        first_name=data["first_name"],
        middle_name=data.get("middle_name", ""),
        last_name=data["last_name"],
        email=email,
        personal_email=(data.get("personal_email") or "").strip().lower(),
        phone=data.get("phone", ""),
        alternate_phone=data.get("alternate_phone", ""),
        gender=data.get("gender", ""),
        date_of_birth=data.get("date_of_birth"),
        national_id=data.get("national_id", ""),
        nationality=data.get("nationality", "Kenyan"),
        staff_category=staff_category,
        portal_role=portal_role,
        designation=designation,
        department_id=_coerce_uuid_pk(data.get("department")),
        date_joined=data.get("date_joined") or timezone.now().date(),
        employment_type=data.get("employment_type", "full_time"),
        status=data.get("status", "active"),
        address=data.get("address", ""),
        emergency_contact=data.get("emergency_contact", ""),
        emergency_phone=data.get("emergency_phone", ""),
        emergency_relationship=data.get("emergency_relationship", ""),
        has_portal_access=has_portal_access,
        qualification_summary=data.get("qualification_summary", ""),
        notes=data.get("notes", ""),
        supervisor_id=_coerce_uuid_pk(data.get("supervisor")),
        created_by=actor,
        updated_by=actor,
    )

    if role_requires_teacher_profile(portal_role) or data.get("create_teacher_profile"):
        teacher_data = data.get("teacher") or {}
        teacher = Teacher.objects.create(
            tenant=tenant,
            staff=staff,
            qualification=teacher_data.get("qualification", data.get("qualification_summary", "")),
            specialization=teacher_data.get("specialization", ""),
            years_experience=teacher_data.get("years_experience", 0),
            is_class_teacher=bool(teacher_data.get("is_class_teacher", False)),
            created_by=actor,
            updated_by=actor,
        )
        subject_ids = teacher_data.get("subject_ids") or data.get("subject_ids") or []
        if subject_ids:
            teacher.subjects.set(subject_ids)

    staff._onboarding_temp_password = temp_password  # type: ignore[attr-defined]
    return staff


@transaction.atomic
def update_staff_record(staff: Staff, *, actor=None, data: dict[str, Any]) -> Staff:
    """Update staff and sync linked user profile fields."""
    email = (data.get("email") or staff.email).strip().lower()
    if email != staff.email.lower():
        if Staff.all_objects.filter(tenant=staff.tenant, email__iexact=email, is_deleted=False).exclude(pk=staff.pk).exists():
            raise StaffOnboardingError("Another staff member already uses this work email.")
        if staff.user_id and User.objects.filter(email__iexact=email).exclude(pk=staff.user_id).exists():
            raise StaffOnboardingError("This email is already used by another portal account.")

    for field in [
        "first_name", "middle_name", "last_name", "phone", "alternate_phone",
        "personal_email", "gender", "date_of_birth", "national_id", "nationality",
        "staff_category", "portal_role", "designation", "employment_type", "status",
        "address", "emergency_contact", "emergency_phone", "emergency_relationship",
        "qualification_summary", "notes", "has_portal_access",
    ]:
        if field in data:
            setattr(staff, field, data[field])

    if "email" in data:
        staff.email = email
    if "department" in data:
        staff.department_id = _coerce_uuid_pk(data["department"])
    if "supervisor" in data:
        staff.supervisor_id = _coerce_uuid_pk(data["supervisor"])
    if "date_joined" in data:
        staff.date_joined = data["date_joined"]
    if "date_left" in data:
        staff.date_left = data["date_left"]

    staff.updated_by = actor
    staff.save()

    if staff.user_id:
        user = staff.user
        user.first_name = staff.first_name
        user.last_name = staff.last_name
        user.phone = staff.phone
        if "portal_role" in data:
            user.role = staff.portal_role
        if staff.email != user.email:
            user.email = staff.email
        user.is_active = staff.status == "active" and staff.has_portal_access
        user.save(update_fields=[
            "first_name", "last_name", "phone", "role", "email", "is_active", "updated_at",
        ])

    return staff