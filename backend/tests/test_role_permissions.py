"""Tests for school role module permissions and plan inheritance."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.core.constants import UserRole
from apps.subscriptions.services import assign_plan_features, get_tenant_module_menu
from apps.tenants.role_permissions import (
    get_user_feature_permissions,
    get_user_module_menu,
    get_user_module_permissions,
    save_role_permissions,
)


@pytest.fixture
def premium_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Premium", slug="premium", max_students=500)
    assign_plan_features(plan, [
        "student_management", "staff_management", "classes",
        "academic_years", "student_attendance", "student_billing",
        "library_management", "hostel_management", "vehicles",
        "inventory_items", "hr_departments", "dashboard_analytics",
        "announcements", "examination_management",
    ])
    return plan


@pytest.fixture
def premium_tenant(db, premium_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Premium School",
        code="PREM",
        email="prem@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=premium_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def librarian(db, premium_tenant):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        email="lib@test.edu",
        password="TestPass@2026",
        first_name="Lib",
        last_name="Rarian",
        role=UserRole.LIBRARIAN,
        tenant=premium_tenant,
    )


@pytest.fixture
def premium_teacher(db, premium_tenant):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        email="teacher.prem@test.edu",
        password="TestPass@2026",
        first_name="Prem",
        last_name="Teacher",
        role=UserRole.TEACHER,
        tenant=premium_tenant,
        is_email_verified=True,
    )


@pytest.fixture
def parent_user(db, premium_tenant):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        email="parent@test.edu",
        password="TestPass@2026",
        first_name="Pat",
        last_name="Rent",
        role=UserRole.PARENT,
        tenant=premium_tenant,
    )


@pytest.mark.django_db
class TestRolePermissions:
    def test_librarian_default_permissions(self, premium_tenant, librarian):
        perms = get_user_module_permissions(premium_tenant, librarian)
        assert perms["library"]["can_read"] is True
        assert perms["library"]["can_write"] is True
        assert "finance" not in perms or not perms.get("finance", {}).get("can_read")

    def test_librarian_menu_filtered_by_plan_and_role(self, premium_tenant, librarian):
        plan_keys = {m["key"] for m in get_tenant_module_menu(premium_tenant)}
        menu = get_user_module_menu(premium_tenant, librarian)
        menu_keys = {m["key"] for m in menu}
        assert "library" in menu_keys
        assert menu_keys.issubset(plan_keys)
        assert "finance" not in menu_keys

    def test_parent_cannot_write_finance(self, premium_tenant, parent_user):
        perms = get_user_module_permissions(premium_tenant, parent_user)
        assert perms.get("finance", {}).get("can_read") is True
        assert perms.get("finance", {}).get("can_write") is False

    def test_school_admin_has_full_plan_access(self, premium_tenant, school_admin):
        menu = get_user_module_menu(premium_tenant, school_admin)
        plan_menu = get_tenant_module_menu(premium_tenant)
        assert len(menu) == len(plan_menu)
        assert all(m.get("can_write") for m in menu)

    def test_custom_permissions_override_defaults(self, premium_tenant, librarian):
        save_role_permissions(premium_tenant, [{
            "role": UserRole.LIBRARIAN,
            "module_key": "library",
            "can_read": True,
            "can_write": False,
        }])
        perms = get_user_module_permissions(premium_tenant, librarian)
        assert perms["library"]["can_write"] is False

    def test_context_api_for_librarian(self, premium_tenant, librarian):
        client = APIClient()
        client.force_authenticate(user=librarian)
        response = client.get("/api/v1/tenants/context/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["user_role"] == UserRole.LIBRARIAN
        assert data["is_school_admin"] is False
        module_keys = {m["key"] for m in data["module_menu"]}
        assert "library" in module_keys
        assert "finance" not in module_keys

    def test_role_permission_matrix_school_admin_only(self, premium_tenant, school_admin, librarian):
        admin_client = APIClient()
        admin_client.force_authenticate(user=school_admin)
        assert admin_client.get("/api/v1/tenants/role-permissions/").status_code == 200

        lib_client = APIClient()
        lib_client.force_authenticate(user=librarian)
        assert lib_client.get("/api/v1/tenants/role-permissions/").status_code == 403

    def test_granular_feature_write_denied_blocks_create(self, premium_tenant, premium_teacher):
        save_role_permissions(premium_tenant, [
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
        feature_perms = get_user_feature_permissions(premium_tenant, premium_teacher)
        assert feature_perms["classes"]["can_write"] is False

        from apps.academics.models import AcademicYear

        year = AcademicYear.objects.create(
            tenant=premium_tenant,
            name="2025-2026",
            start_date="2025-09-01",
            end_date="2026-06-30",
            is_current=True,
        )
        client = APIClient()
        client.force_authenticate(user=premium_teacher)
        response = client.post(
            "/api/v1/academics/classes/",
            {"name": "Grade 1", "code": "G1", "academic_year": str(year.id)},
            format="json",
        )
        assert response.status_code == 403

    def test_granular_features_hide_ungranted_submodules(self, premium_tenant, premium_teacher):
        save_role_permissions(premium_tenant, [
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
            {
                "role": UserRole.TEACHER,
                "feature_key": "academic_years",
                "can_read": True,
                "can_write": False,
            },
        ])
        menu = get_user_module_menu(premium_tenant, premium_teacher)
        academics = next((m for m in menu if m["key"] == "academics"), None)
        assert academics is not None
        child_keys = {c["feature_key"] for c in academics.get("children", [])}
        assert child_keys == {"classes", "academic_years"}
        assert "terms" not in child_keys
        assert "subjects" not in child_keys

        feature_perms = get_user_feature_permissions(premium_tenant, premium_teacher)
        assert feature_perms["classes"]["can_read"] is True
        assert feature_perms.get("terms", {}).get("can_read") in (None, False)

    def test_plan_gating_blocks_unpaid_module_even_with_permission(self, premium_tenant, librarian):
        """Support module is not on premium_plan — permission alone must not grant access."""
        save_role_permissions(premium_tenant, [{
            "role": UserRole.LIBRARIAN,
            "module_key": "support",
            "can_read": True,
            "can_write": True,
        }])
        menu = get_user_module_menu(premium_tenant, librarian)
        assert "support" not in {m["key"] for m in menu}