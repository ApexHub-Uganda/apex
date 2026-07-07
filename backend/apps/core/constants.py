"""Platform-wide constants."""
from __future__ import annotations

from typing import Final

class RegistrationType:
    """How a school completed public registration onboarding."""

    TRIAL_EMAIL = "trial_email"
    TRIAL_PLAN = "trial_plan"
    PAID = "paid"
    PENDING = "pending"

    CHOICES = [
        (PENDING, "Onboarding Pending"),
        (TRIAL_EMAIL, "Trial via Email"),
        (TRIAL_PLAN, "Trial Plan Selected"),
        (PAID, "Paid Registration"),
    ]


# Brand colors
COLOR_PRIMARY: Final[str] = "#0F766E"
COLOR_SECONDARY: Final[str] = "#FF7F50"
COLOR_ACCENT: Final[str] = "#F5E6CA"

# User roles
class UserRole:
    SUPER_ADMIN = "super_admin"
    SCHOOL_ADMIN = "school_admin"
    HEAD_TEACHER = "head_teacher"
    DEPUTY_HEAD_TEACHER = "deputy_head_teacher"
    DIRECTOR_OF_STUDIES = "director_of_studies"
    HEAD_OF_DEPARTMENT = "head_of_department"
    TEACHER = "teacher"
    CLASS_TEACHER = "class_teacher"
    PARENT = "parent"
    STUDENT = "student"
    BURSAR = "bursar"
    ASSISTANT_BURSAR = "assistant_bursar"
    LIBRARIAN = "librarian"
    HR_MANAGER = "hr_manager"
    TRANSPORT_MANAGER = "transport_manager"
    HOSTEL_MANAGER = "hostel_manager"
    INVENTORY_MANAGER = "inventory_manager"
    # Legacy aliases (still valid in stored user.role values)
    FINANCE_OFFICER = "finance_officer"
    HR_OFFICER = "hr_officer"
    TRANSPORT_OFFICER = "transport_officer"
    HOSTEL_WARDEN = "hostel_warden"
    INVENTORY_OFFICER = "inventory_officer"
    RECEPTIONIST = "receptionist"
    NURSE = "nurse"
    COUNSELOR = "counselor"

    CHOICES = [
        (SUPER_ADMIN, "Super Admin"),
        (SCHOOL_ADMIN, "School Admin"),
        (HEAD_TEACHER, "Head Teacher"),
        (DEPUTY_HEAD_TEACHER, "Deputy Head Teacher"),
        (DIRECTOR_OF_STUDIES, "Director of Studies"),
        (HEAD_OF_DEPARTMENT, "Head of Department"),
        (TEACHER, "Teacher"),
        (CLASS_TEACHER, "Class Teacher"),
        (PARENT, "Parent"),
        (STUDENT, "Student"),
        (BURSAR, "Bursar / Accountant"),
        (ASSISTANT_BURSAR, "Assistant Bursar"),
        (LIBRARIAN, "Librarian"),
        (HR_MANAGER, "Human Resource Manager"),
        (TRANSPORT_MANAGER, "Transport Manager"),
        (HOSTEL_MANAGER, "Hostel Manager"),
        (INVENTORY_MANAGER, "Inventory Manager / Store Keeper"),
        (FINANCE_OFFICER, "Finance Officer (Legacy)"),
        (HR_OFFICER, "HR Officer (Legacy)"),
        (TRANSPORT_OFFICER, "Transport Officer (Legacy)"),
        (HOSTEL_WARDEN, "Hostel Warden (Legacy)"),
        (INVENTORY_OFFICER, "Inventory Officer (Legacy)"),
        (RECEPTIONIST, "Receptionist"),
        (NURSE, "Nurse"),
        (COUNSELOR, "Counselor"),
    ]

    LEGACY_ROLE_ALIASES: dict[str, str] = {
        FINANCE_OFFICER: BURSAR,
        HR_OFFICER: HR_MANAGER,
        TRANSPORT_OFFICER: TRANSPORT_MANAGER,
        HOSTEL_WARDEN: HOSTEL_MANAGER,
        INVENTORY_OFFICER: INVENTORY_MANAGER,
    }

    CONFIGURABLE_ROLES: list[str] = [
        HEAD_TEACHER,
        DEPUTY_HEAD_TEACHER,
        DIRECTOR_OF_STUDIES,
        HEAD_OF_DEPARTMENT,
        TEACHER,
        CLASS_TEACHER,
        PARENT,
        BURSAR,
        ASSISTANT_BURSAR,
        LIBRARIAN,
        HR_MANAGER,
        TRANSPORT_MANAGER,
        HOSTEL_MANAGER,
        INVENTORY_MANAGER,
        FINANCE_OFFICER,
        HR_OFFICER,
        TRANSPORT_OFFICER,
        HOSTEL_WARDEN,
        INVENTORY_OFFICER,
    ]

    SCHOOL_PORTAL_ROLES: list[str] = [SCHOOL_ADMIN, *CONFIGURABLE_ROLES]

    SCHOOL_ROLES: list[str] = [
        SCHOOL_ADMIN,
        HEAD_TEACHER,
        DEPUTY_HEAD_TEACHER,
        DIRECTOR_OF_STUDIES,
        HEAD_OF_DEPARTMENT,
        TEACHER,
        CLASS_TEACHER,
        PARENT,
        STUDENT,
        BURSAR,
        ASSISTANT_BURSAR,
        LIBRARIAN,
        HR_MANAGER,
        TRANSPORT_MANAGER,
        HOSTEL_MANAGER,
        INVENTORY_MANAGER,
        FINANCE_OFFICER,
        HR_OFFICER,
        TRANSPORT_OFFICER,
        HOSTEL_WARDEN,
        INVENTORY_OFFICER,
        RECEPTIONIST,
        NURSE,
        COUNSELOR,
    ]

    STAFF_ROLES: list[str] = [
        SCHOOL_ADMIN,
        HEAD_TEACHER,
        DEPUTY_HEAD_TEACHER,
        DIRECTOR_OF_STUDIES,
        HEAD_OF_DEPARTMENT,
        TEACHER,
        CLASS_TEACHER,
        BURSAR,
        ASSISTANT_BURSAR,
        LIBRARIAN,
        HR_MANAGER,
        TRANSPORT_MANAGER,
        HOSTEL_MANAGER,
        INVENTORY_MANAGER,
        FINANCE_OFFICER,
        HR_OFFICER,
        TRANSPORT_OFFICER,
        HOSTEL_WARDEN,
        INVENTORY_OFFICER,
        RECEPTIONIST,
        NURSE,
        COUNSELOR,
    ]


def normalize_role(role: str | None) -> str:
    """Map legacy role slugs to canonical portal roles."""
    if not role:
        return UserRole.TEACHER
    return UserRole.LEGACY_ROLE_ALIASES.get(role, role)


def is_school_portal_role(role: str | None) -> bool:
    return normalize_role(role or "") in UserRole.SCHOOL_PORTAL_ROLES or role == UserRole.SCHOOL_ADMIN


class PaymentMethodType:
    """Checkout payment instrument selected by the payer."""

    CARD = "card"
    MOBILE_MONEY = "mobile_money"

    CHOICES = [
        (CARD, "Credit or Debit Card"),
        (MOBILE_MONEY, "Mobile Money"),
    ]


# Subscription plan slugs
class PlanSlug:
    FREE_TRIAL = "free_trial"
    BASIC = "basic"
    PREMIUM = "premium"
    PREMIUM_PLUS = "premium_plus"


# Tenant status
class TenantStatus:
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"

    CHOICES = [
        (PENDING, "Pending Verification"),
        (ACTIVE, "Active"),
        (SUSPENDED, "Suspended"),
        (EXPIRED, "Expired"),
    ]


# Subscription status
class SubscriptionStatus:
    TRIAL = "trial"
    ACTIVE = "active"
    GRACE_PERIOD = "grace_period"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"

    CHOICES = [
        (TRIAL, "Trial"),
        (ACTIVE, "Active"),
        (GRACE_PERIOD, "Grace Period"),
        (EXPIRED, "Expired"),
        (SUSPENDED, "Suspended"),
        (CANCELLED, "Cancelled"),
    ]