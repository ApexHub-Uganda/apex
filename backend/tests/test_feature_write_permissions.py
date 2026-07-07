"""API enforcement of sub-module write permissions."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.core.constants import UserRole
from apps.subscriptions.services import assign_plan_features
from apps.tenants.role_permissions import (
    get_user_feature_permissions,
    save_role_permissions,
    user_can_access_feature,
)


@pytest.fixture
def academics_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Academics Plan", slug="academics-plan", max_students=500)
    assign_plan_features(plan, [
        "student_management", "staff_management", "classes",
        "academic_years", "terms", "subjects", "dashboard_analytics",
    ])
    return plan


@pytest.fixture
def academics_tenant(db, academics_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Academics School",
        code="ACAD",
        email="acad@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=academics_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def teacher(db, academics_tenant):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        email="teacher.acad@test.edu",
        password="TestPass@2026",
        first_name="Write",
        last_name="Test",
        role=UserRole.TEACHER,
        tenant=academics_tenant,
        is_email_verified=True,
    )


@pytest.fixture
def academic_year(db, academics_tenant):
    from apps.academics.models import AcademicYear

    return AcademicYear.objects.create(
        tenant=academics_tenant,
        name="2025-2026",
        start_date="2025-09-01",
        end_date="2026-06-30",
        is_current=True,
    )


@pytest.mark.django_db
class TestFeatureWritePermissions:
    def test_teacher_default_cannot_write_classes(self, academics_tenant, teacher):
        assert not user_can_access_feature(academics_tenant, teacher, "classes", require_write=True)
        perms = get_user_feature_permissions(academics_tenant, teacher)
        assert perms["classes"]["can_read"] is True
        assert perms["classes"]["can_write"] is False

    def test_module_write_denied_blocks_feature_write(self, academics_tenant, teacher):
        save_role_permissions(academics_tenant, [{
            "role": UserRole.TEACHER,
            "module_key": "academics",
            "can_read": True,
            "can_write": False,
        }])
        perms = get_user_feature_permissions(academics_tenant, teacher)
        assert perms["classes"]["can_read"] is True
        assert perms["classes"]["can_write"] is False
        assert user_can_access_feature(academics_tenant, teacher, "classes", require_write=False)
        assert not user_can_access_feature(academics_tenant, teacher, "classes", require_write=True)

    def test_granular_feature_write_denied(self, academics_tenant, teacher):
        save_role_permissions(academics_tenant, [
            {
                "role": UserRole.TEACHER,
                "module_key": "academics",
                "can_read": True,
                "can_write": True,
            },
            {
                "role": UserRole.TEACHER,
                "feature_key": "classes",
                "can_read": True,
                "can_write": False,
            },
        ])
        perms = get_user_feature_permissions(academics_tenant, teacher)
        assert perms["classes"]["can_write"] is False
        assert not user_can_access_feature(academics_tenant, teacher, "classes", require_write=True)

    def test_post_classes_blocked_when_write_denied(
        self, academics_tenant, teacher, academic_year,
    ):
        save_role_permissions(academics_tenant, [{
            "role": UserRole.TEACHER,
            "module_key": "academics",
            "can_read": True,
            "can_write": False,
        }])
        client = APIClient()
        client.force_authenticate(user=teacher)
        response = client.post(
            "/api/v1/academics/classes/",
            {
                "name": "Grade 10-A",
                "code": "G10A",
                "academic_year": str(academic_year.id),
            },
            format="json",
        )
        assert response.status_code == 403

    def test_post_classes_blocked_by_default_teacher_defaults(
        self, academics_tenant, teacher, academic_year,
    ):
        client = APIClient()
        client.force_authenticate(user=teacher)
        response = client.post(
            "/api/v1/academics/classes/",
            {
                "name": "Grade 10-B",
                "code": "G10B",
                "academic_year": str(academic_year.id),
            },
            format="json",
        )
        assert response.status_code == 403

    def test_save_caps_feature_write_when_module_write_denied(self, academics_tenant, teacher):
        save_role_permissions(academics_tenant, [
            {
                "role": UserRole.TEACHER,
                "module_key": "academics",
                "can_read": True,
                "can_write": False,
            },
            {
                "role": UserRole.TEACHER,
                "feature_key": "classes",
                "can_read": True,
                "can_write": True,
            },
        ])
        perms = get_user_feature_permissions(academics_tenant, teacher)
        assert perms["classes"]["can_write"] is False

    def test_context_api_reflects_write_denial(self, academics_tenant, teacher):
        save_role_permissions(academics_tenant, [{
            "role": UserRole.TEACHER,
            "module_key": "academics",
            "can_read": True,
            "can_write": False,
        }])
        client = APIClient()
        client.force_authenticate(user=teacher)
        response = client.get("/api/v1/tenants/context/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["feature_permissions"]["classes"]["can_write"] is False