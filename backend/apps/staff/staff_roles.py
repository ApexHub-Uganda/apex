"""Staff role metadata — maps portal roles to categories and onboarding rules."""
from __future__ import annotations

from typing import Any

from apps.core.constants import UserRole, normalize_role

STAFF_CATEGORY_CHOICES: list[tuple[str, str]] = [
    ("management", "Management"),
    ("teaching", "Teaching"),
    ("administrative", "Administrative"),
    ("support", "Support"),
    ("finance", "Finance"),
]

PORTAL_STAFF_ROLES: list[str] = [
    UserRole.HEAD_TEACHER,
    UserRole.DEPUTY_HEAD_TEACHER,
    UserRole.DIRECTOR_OF_STUDIES,
    UserRole.HEAD_OF_DEPARTMENT,
    UserRole.TEACHER,
    UserRole.CLASS_TEACHER,
    UserRole.BURSAR,
    UserRole.ASSISTANT_BURSAR,
    UserRole.LIBRARIAN,
    UserRole.HR_MANAGER,
    UserRole.TRANSPORT_MANAGER,
    UserRole.HOSTEL_MANAGER,
    UserRole.INVENTORY_MANAGER,
]

ROLE_LABELS = dict(UserRole.CHOICES)

STAFF_ROLE_DEFINITIONS: dict[str, dict[str, Any]] = {
    UserRole.HEAD_TEACHER: {
        "category": "management",
        "default_designation": "Head Teacher",
        "requires_teacher_profile": False,
        "portal_access_default": True,
        "description": "School-wide academic and operational leadership.",
    },
    UserRole.DEPUTY_HEAD_TEACHER: {
        "category": "management",
        "default_designation": "Deputy Head Teacher",
        "requires_teacher_profile": False,
        "portal_access_default": True,
        "description": "Assists head teacher with daily academic coordination.",
    },
    UserRole.DIRECTOR_OF_STUDIES: {
        "category": "management",
        "default_designation": "Director of Studies",
        "requires_teacher_profile": False,
        "portal_access_default": True,
        "description": "Oversees curriculum, examinations, and academic standards.",
    },
    UserRole.HEAD_OF_DEPARTMENT: {
        "category": "teaching",
        "default_designation": "Head of Department",
        "requires_teacher_profile": True,
        "portal_access_default": True,
        "description": "Leads an academic department and teaching staff.",
    },
    UserRole.TEACHER: {
        "category": "teaching",
        "default_designation": "Teacher",
        "requires_teacher_profile": True,
        "portal_access_default": True,
        "description": "Classroom instruction, attendance, and academics.",
    },
    UserRole.CLASS_TEACHER: {
        "category": "teaching",
        "default_designation": "Class Teacher",
        "requires_teacher_profile": True,
        "portal_access_default": True,
        "description": "Class welfare, notices, discipline, and report cards for an assigned class.",
    },
    UserRole.BURSAR: {
        "category": "finance",
        "default_designation": "Bursar / Accountant",
        "requires_teacher_profile": False,
        "portal_access_default": True,
        "description": "Fees, billing, payroll, and financial reporting.",
    },
    UserRole.ASSISTANT_BURSAR: {
        "category": "finance",
        "default_designation": "Assistant Bursar",
        "requires_teacher_profile": False,
        "portal_access_default": True,
        "description": "Day-to-day fee collection, invoicing, and financial records.",
    },
    UserRole.LIBRARIAN: {
        "category": "support",
        "default_designation": "Librarian",
        "requires_teacher_profile": False,
        "portal_access_default": True,
        "description": "Library catalog, borrowing, and returns.",
    },
    UserRole.HR_MANAGER: {
        "category": "administrative",
        "default_designation": "Human Resource Manager",
        "requires_teacher_profile": False,
        "portal_access_default": True,
        "description": "Staff records, leave, and performance management.",
    },
    UserRole.TRANSPORT_MANAGER: {
        "category": "support",
        "default_designation": "Transport Manager",
        "requires_teacher_profile": False,
        "portal_access_default": True,
        "description": "Fleet, routes, and student transport.",
    },
    UserRole.HOSTEL_MANAGER: {
        "category": "support",
        "default_designation": "Hostel Manager",
        "requires_teacher_profile": False,
        "portal_access_default": True,
        "description": "Boarding, rooms, and allocations.",
    },
    UserRole.INVENTORY_MANAGER: {
        "category": "support",
        "default_designation": "Inventory Manager",
        "requires_teacher_profile": False,
        "portal_access_default": True,
        "description": "Stock, suppliers, and purchase orders.",
    },
}


def get_role_definition(role: str) -> dict[str, Any]:
    canonical = normalize_role(role)
    base = STAFF_ROLE_DEFINITIONS.get(canonical, {
        "category": "administrative",
        "default_designation": ROLE_LABELS.get(canonical, "Staff Member"),
        "requires_teacher_profile": False,
        "portal_access_default": True,
        "description": "School staff member.",
    })
    return {
        "role": canonical,
        "label": ROLE_LABELS.get(canonical, canonical.replace("_", " ").title()),
        **base,
    }


def list_staff_role_options() -> list[dict[str, Any]]:
    return [get_role_definition(role) for role in PORTAL_STAFF_ROLES]


def role_requires_teacher_profile(role: str) -> bool:
    return bool(get_role_definition(role).get("requires_teacher_profile"))