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
    TEACHER = "teacher"
    PARENT = "parent"
    STUDENT = "student"
    FINANCE_OFFICER = "finance_officer"
    LIBRARIAN = "librarian"
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
        (TEACHER, "Teacher"),
        (PARENT, "Parent"),
        (STUDENT, "Student"),
        (FINANCE_OFFICER, "Finance Officer"),
        (LIBRARIAN, "Librarian"),
        (HR_OFFICER, "HR Officer"),
        (TRANSPORT_OFFICER, "Transport Officer"),
        (HOSTEL_WARDEN, "Hostel Warden"),
        (INVENTORY_OFFICER, "Inventory Officer"),
        (RECEPTIONIST, "Receptionist"),
        (NURSE, "Nurse"),
        (COUNSELOR, "Counselor"),
    ]

    SCHOOL_ROLES = [
        SCHOOL_ADMIN, HEAD_TEACHER, TEACHER, PARENT, STUDENT,
        FINANCE_OFFICER, LIBRARIAN, HR_OFFICER, TRANSPORT_OFFICER,
        HOSTEL_WARDEN, INVENTORY_OFFICER, RECEPTIONIST, NURSE, COUNSELOR,
    ]

    STAFF_ROLES = [
        SCHOOL_ADMIN, HEAD_TEACHER, TEACHER, FINANCE_OFFICER,
        LIBRARIAN, HR_OFFICER, TRANSPORT_OFFICER, HOSTEL_WARDEN,
        INVENTORY_OFFICER, RECEPTIONIST, NURSE, COUNSELOR,
    ]


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


