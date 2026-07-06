"""Global portal search tests."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.core.constants import UserRole
from apps.staff.services import onboard_staff
from apps.students.models import Student
from apps.subscriptions.models import Plan
from apps.subscriptions.seed_features import seed_feature_catalog
from apps.subscriptions.services import assign_plan_features
from apps.tenants.models import Tenant

@pytest.fixture
def search_tenant(db):
    seed_feature_catalog()
    plan = Plan.objects.create(name="Search Plan", slug="search-plan", max_students=500)
    assign_plan_features(plan, [
        "student_management", "staff_management", "classes",
        "library_management", "dashboard_analytics", "announcements",
        "hr_departments",
    ])
    tenant = Tenant.objects.create(
        name="Search School",
        code="SRCH",
        email="search@test.edu",
        status="active",
        is_verified=True,
    )
    from apps.subscriptions.models import Subscription

    sub = Subscription.objects.create(tenant=tenant, plan=plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def search_school_admin(db, search_tenant):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        email="admin.search@test.edu",
        password="TestPass@2026",
        first_name="Search",
        last_name="Admin",
        role=UserRole.SCHOOL_ADMIN,
        tenant=search_tenant,
        is_email_verified=True,
    )


@pytest.fixture
def librarian(db, search_tenant):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        email="lib.search@test.edu",
        password="TestPass@2026",
        first_name="Libby",
        last_name="Rarian",
        role=UserRole.LIBRARIAN,
        tenant=search_tenant,
        is_email_verified=True,
    )


@pytest.mark.django_db
class TestPortalSearch:
    def test_super_admin_can_search_platform_pages(self, super_admin):
        client = APIClient()
        client.force_authenticate(user=super_admin)

        response = client.get("/api/v1/search/", {"q": "schools"})
        assert response.status_code == 200
        results = response.json()["data"]["results"]
        paths = {item["path"] for item in results}
        assert "/super-admin/schools" in paths

    def test_librarian_sees_library_not_finance(self, search_tenant, librarian):
        client = APIClient()
        client.force_authenticate(user=librarian)

        response = client.get("/api/v1/search/", {"q": "library"})
        assert response.status_code == 200
        titles = {item["title"].lower() for item in response.json()["data"]["results"]}
        assert any("library" in title for title in titles)

        finance = client.get("/api/v1/search/", {"q": "finance"})
        finance_titles = [item["title"].lower() for item in finance.json()["data"]["results"]]
        assert not any("finance" in title for title in finance_titles)

    def test_hr_can_search_staff_records(self, search_tenant):
        staff = onboard_staff(
            search_tenant,
            data={
                "first_name": "Unique",
                "last_name": "Staffmember",
                "email": "unique.staff@test.edu",
                "phone": "+254700000077",
                "portal_role": UserRole.HR_MANAGER,
                "date_joined": "2025-01-01",
            },
        )
        client = APIClient()
        client.force_authenticate(user=staff.user)

        response = client.get("/api/v1/search/", {"q": "unique"})
        assert response.status_code == 200
        types = {item["type"] for item in response.json()["data"]["results"]}
        assert "staff" in types

    def test_teacher_cannot_search_staff_without_permission(self, search_tenant, teacher_user):
        onboard_staff(
            search_tenant,
            data={
                "first_name": "Hidden",
                "last_name": "Staffmember",
                "email": "hidden.staff@test.edu",
                "phone": "+254700000066",
                "portal_role": UserRole.TEACHER,
                "date_joined": "2025-01-01",
            },
        )
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        response = client.get("/api/v1/search/", {"q": "hidden"})
        types = {item["type"] for item in response.json()["data"]["results"]}
        assert "staff" not in types

    def test_school_admin_can_search_students(self, search_tenant, search_school_admin):
        Student.objects.create(
            tenant=search_tenant,
            admission_number="ADM-9001",
            first_name="Searchable",
            last_name="Student",
            date_of_birth="2012-05-01",
            enrollment_date="2024-01-15",
            gender="male",
        )
        client = APIClient()
        client.force_authenticate(user=search_school_admin)

        response = client.get("/api/v1/search/", {"q": "searchable"})
        assert response.status_code == 200
        assert any(item["type"] == "student" for item in response.json()["data"]["results"])

    def test_short_query_returns_empty(self, search_school_admin):
        client = APIClient()
        client.force_authenticate(user=search_school_admin)

        response = client.get("/api/v1/search/", {"q": "a"})
        assert response.status_code == 200
        assert response.json()["data"]["results"] == []