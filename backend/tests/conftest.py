"""Pytest fixtures for Apex Hub tests."""
from __future__ import annotations

import os

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.core.constants import PlanSlug, UserRole
from apps.subscriptions.models import Plan, Subscription
from apps.subscriptions.seed_features import seed_feature_catalog
from apps.subscriptions.services import assign_plan_features
from apps.tenants.models import Tenant

User = get_user_model()


@pytest.fixture(autouse=True)
def _require_isolated_test_database():
    """Never allow pytest to mutate the developer/production Postgres database."""
    if os.environ.get("APEX_USE_DEV_DATABASE") == "1":
        return

    engine = settings.DATABASES["default"]["ENGINE"]
    db_name = str(settings.DATABASES["default"]["NAME"]).lower()
    if "sqlite" in engine and ("test" in db_name or "memory" in db_name):
        return

    pytest.fail(
        "Tests must run against the isolated SQLite test database. "
        "Use `python -m pytest` (not manage.py test on Postgres). "
        "Set APEX_USE_DEV_DATABASE=1 only if you intentionally accept DB mutation.",
    )


BASIC_FEATURE_KEYS = [
    "student_management", "staff_management", "classes",
    "academic_years", "dashboard_analytics",
]

PREMIUM_FEATURE_KEYS = BASIC_FEATURE_KEYS + [
    "student_attendance", "student_billing", "parent_fee_statements",
    "library_management", "hostel_management", "vehicles",
    "inventory_items", "hr_departments", "announcements",
    "examination_management",
]


def _ensure_plan(slug: str, name: str, **defaults) -> Plan:
    seed_feature_catalog()
    plan, _ = Plan.objects.get_or_create(
        slug=slug,
        defaults={
            "name": name,
            "max_students": defaults.get("max_students", 500),
            "max_staff": defaults.get("max_staff", 50),
            "max_parents": defaults.get("max_parents", 500),
            "is_active": True,
            "is_public": True,
            **defaults,
        },
    )
    return plan


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def plan(db):
    p = _ensure_plan(PlanSlug.BASIC, "Basic", max_students=100, max_staff=20)
    assign_plan_features(p, BASIC_FEATURE_KEYS)
    return p


@pytest.fixture
def premium_plan(db):
    p = _ensure_plan(PlanSlug.PREMIUM, "Premium")
    assign_plan_features(p, PREMIUM_FEATURE_KEYS)
    return p


@pytest.fixture
def tenant(db, plan):
    t = Tenant.objects.create(
        name="Test School",
        code="TEST",
        email="school@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=t, plan=plan, status="active")
    sub.activate(period_days=30)
    return t


@pytest.fixture
def super_admin(db):
    return User.objects.create_superuser(
        email="super@test.io",
        password="TestPass@2026",
        first_name="Super",
        last_name="Admin",
    )


@pytest.fixture
def school_admin(db, tenant):
    return User.objects.create_user(
        email="admin@test.edu",
        password="TestPass@2026",
        first_name="School",
        last_name="Admin",
        role=UserRole.SCHOOL_ADMIN,
        tenant=tenant,
        is_email_verified=True,
    )


@pytest.fixture
def teacher_user(db, tenant):
    return User.objects.create_user(
        email="teacher@test.edu",
        password="TestPass@2026",
        first_name="Test",
        last_name="Teacher",
        role="teacher",
        tenant=tenant,
    )


@pytest.fixture
def other_tenant(db, plan):
    t = Tenant.objects.create(
        name="Other School",
        code="OTHER",
        email="other@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=t, plan=plan, status="active")
    sub.activate(period_days=30)
    return t