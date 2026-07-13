"""Shared validation for legitimate school registration and admin provisioning."""
from __future__ import annotations

import re

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.core.management.commands.seed_platform import UGANDAN_SCHOOLS

_MIN_SCHOOL_NAME_LENGTH = 3
_MIN_SCHOOL_CODE_LENGTH = 3
_MIN_EMAIL_LOCAL_PART = 3

_JUNK_NAME_RE = re.compile(r"^t\d*$", re.IGNORECASE)
_EMAIL_LOCAL_RE = re.compile(r"^[^@]+")

SEED_SCHOOL_CODES = frozenset(school["code"].upper() for school in UGANDAN_SCHOOLS)

TEST_SCHOOL_CODES = frozenset({
    "TEST", "OTHER", "SCOPE", "ASGN", "WAPI", "SING", "DASH", "ATTN", "ACAD",
    "FLOW", "HSTR", "FINR", "GRDSCH", "FPER", "HRWF", "HSTW", "HRRB", "LIBW",
    "LIBR", "SRCH", "TASCH", "PREM", "AROLE",
})

TEST_SCHOOL_NAMES = frozenset({
    "Test School",
    "Other School",
    "Scoping School",
    "Assignment School",
    "Workflow API School",
    "Singleton School",
    "Dash School",
    "Attendance School",
    "Academics School",
    "Workflow School",
    "Hostel RBAC School",
    "Finance RBAC School",
    "Grading School",
    "Finance Perm School",
    "HR Workflow School",
    "Hostel Workflow School",
    "HR RBAC School",
    "Library Workflow School",
    "Library RBAC School",
    "Search School",
    "TA School",
    "Premium School",
    "Academic Roles School",
})

TEST_EMAIL_DOMAINS = frozenset({
    "test.edu",
    "test.io",
    "t.edu",
})


def normalize_school_code(code: str | None) -> str:
    return str(code or "").strip().upper()


def validate_school_name(value: str) -> str:
    name = str(value or "").strip()
    if len(name) < _MIN_SCHOOL_NAME_LENGTH:
        raise serializers.ValidationError(
            f"School name must be at least {_MIN_SCHOOL_NAME_LENGTH} characters.",
        )
    if not re.search(r"[A-Za-z]{2,}", name):
        raise serializers.ValidationError(
            "School name must include at least two letters.",
        )
    if _JUNK_NAME_RE.fullmatch(name):
        raise serializers.ValidationError(
            "Enter the full official school name, not a placeholder like \"T\" or \"T2\".",
        )
    return name


def validate_school_code(value: str) -> str:
    code = normalize_school_code(value)
    if len(code) < _MIN_SCHOOL_CODE_LENGTH:
        raise serializers.ValidationError(
            f"School code must be at least {_MIN_SCHOOL_CODE_LENGTH} characters.",
        )
    if code in TEST_SCHOOL_CODES:
        raise serializers.ValidationError(
            "This school code is reserved for automated testing and cannot be used.",
        )
    return code


def validate_school_contact_email(value: str) -> str:
    email = str(value or "").strip().lower()
    if "@" not in email:
        raise serializers.ValidationError("Enter a valid school email address.")

    local, domain = email.split("@", 1)
    host = domain.split(".", 1)[0]
    if len(local) < _MIN_EMAIL_LOCAL_PART:
        raise serializers.ValidationError(
            "Use a real school contact email address (not a placeholder like t@t.edu).",
        )
    if len(host) < 3:
        raise serializers.ValidationError(
            "Use a valid school email domain (for example name@schoolname.edu).",
        )
    if domain in TEST_EMAIL_DOMAINS:
        raise serializers.ValidationError(
            "Use your school's real email domain, not a test placeholder domain.",
        )
    return email


def is_probable_test_or_junk_school(*, name: str, code: str, email: str) -> bool:
    normalized_name = str(name or "").strip()
    normalized_code = normalize_school_code(code)
    normalized_email = str(email or "").strip().lower()

    if normalized_code in TEST_SCHOOL_CODES:
        return True
    if normalized_name in TEST_SCHOOL_NAMES:
        return True
    if _JUNK_NAME_RE.fullmatch(normalized_name):
        return True
    if normalized_name.lower() in {"hr school", "full school"}:
        return True

    if normalized_email.endswith("@test.edu") or normalized_email.endswith("@test.io"):
        return True
    if normalized_email.endswith("@t.edu"):
        return True

    try:
        validate_school_name(normalized_name)
        validate_school_code(normalized_code)
        validate_school_contact_email(normalized_email)
    except serializers.ValidationError:
        return True

    return False