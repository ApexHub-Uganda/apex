"""Pytest fixtures for Apex Hub tests."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.core.constants import PlanSlug, UserRole
from apps.subscriptions.models import Plan, Subscription
from apps.subscriptions.seed_features import seed_feature_catalog
from apps.subscriptions.services import assign_plan_features
from apps.tenants.models import Tenant

User = get_user_model()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def plan(db):
    seed_feature_catalog()
    p = Plan.objects.create(
        name="Test Plan",
        slug=PlanSlug.BASIC,
        max_students=100,
    )
    assign_plan_features(p, ["student_management", "staff_management", "classes", "dashboard_analytics"])
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