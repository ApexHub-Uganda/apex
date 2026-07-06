"""Profile completion and self-service field rules."""
from __future__ import annotations

from typing import Any

from apps.accounts.avatar_service import user_has_avatar
from apps.core.constants import UserRole

# Fields staff may update on their own profile (not employment-critical).
STAFF_SELF_EDITABLE = {
    "middle_name", "phone", "alternate_phone", "personal_email", "address",
    "emergency_contact", "emergency_phone", "emergency_relationship", "gender",
}

# Fields only school admin / HR managers may change on staff records.
STAFF_ADMIN_ONLY = {
    "employee_id", "first_name", "last_name", "email", "portal_role", "staff_category",
    "designation", "department", "supervisor", "date_joined", "date_left",
    "employment_type", "status", "national_id", "nationality", "has_portal_access",
    "qualification_summary", "notes",
}

PARENT_SELF_EDITABLE = {
    "phone", "alternate_phone", "alternate_email", "address", "city",
    "occupation", "employer", "preferred_contact_method",
}

PARENT_ADMIN_ONLY = {
    "first_name", "last_name", "email", "national_id", "relationship_to_student",
    "has_portal_access", "is_emergency_contact", "gender", "notes",
}

USER_SELF_EDITABLE = {"first_name", "last_name", "phone"}


def _missing(fields: dict[str, Any], required: list[str]) -> list[str]:
    missing = []
    for key in required:
        value = fields.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(key)
    return missing


def build_profile_completion(user) -> dict[str, Any]:
    """Compute profile completion for dashboard nudges."""
    user_fields = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "email": user.email,
    }
    required_user = ["first_name", "last_name", "phone"]
    missing = _missing(user_fields, required_user)
    if not user_has_avatar(user):
        missing.append("avatar")

    try:
        staff = user.staff_profile
    except Exception:
        staff = None
    try:
        parent = user.parent_profile
    except Exception:
        parent = None
    sections: list[dict[str, Any]] = []

    if staff:
        staff_fields = {
            "phone": staff.phone,
            "personal_email": staff.personal_email,
            "address": staff.address,
            "emergency_contact": staff.emergency_contact,
            "emergency_phone": staff.emergency_phone,
        }
        staff_missing = _missing(staff_fields, ["phone", "address", "emergency_contact", "emergency_phone"])
        missing.extend([f"staff.{m}" for m in staff_missing])
        sections.append({
            "key": "staff",
            "label": "Staff profile",
            "complete": len(staff_missing) == 0,
            "missing_fields": staff_missing,
        })

    if parent:
        parent_fields = {
            "phone": parent.phone,
            "email": parent.email,
            "address": parent.address,
        }
        parent_missing = _missing(parent_fields, ["phone", "email", "address"])
        missing.extend([f"parent.{m}" for m in parent_missing])
        sections.append({
            "key": "parent",
            "label": "Parent profile",
            "complete": len(parent_missing) == 0,
            "missing_fields": parent_missing,
        })

    total_checks = len(required_user) + 1 + sum(len(s.get("missing_fields", [])) for s in sections)
    completed = total_checks - len(missing)
    percent = int((completed / total_checks) * 100) if total_checks else 100

    return {
        "percent": min(100, max(0, percent)),
        "is_complete": len(missing) == 0,
        "missing_fields": missing,
        "sections": sections,
    }


def user_is_profile_admin(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.role in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN):
        return True
    if not user.tenant_id:
        return False
    from apps.tenants.role_permissions import user_can_access_module

    return user_can_access_module(user.tenant, user, "human_resource", require_write=True)