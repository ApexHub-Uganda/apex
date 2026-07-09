"""Library RBAC and circulation workflow tests."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class
from apps.core.constants import UserRole
from apps.library.constants import BORROW_BORROWED, BORROW_RETURNED
from apps.library.models import Book, BorrowRecord
from apps.staff.services import onboard_staff
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features
from apps.tenants.role_feature_defaults import get_default_feature_permission
from apps.tenants.role_permissions import get_user_feature_permissions


@pytest.fixture
def library_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Library RBAC Plan", slug="library-rbac", max_students=500)
    assign_plan_features(plan, [
        "librarian_workspace", "library_management", "book_categories",
        "borrowing", "returns", "reservations", "library_fines",
        "book_suppliers", "library_reports", "student_management",
        "staff_management", "dashboard_analytics",
    ])
    return plan


@pytest.fixture
def library_tenant(db, library_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Library RBAC School",
        code="LIBR",
        email="libr@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=library_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def librarian(db, library_tenant):
    return onboard_staff(
        library_tenant,
        data={
            "first_name": "Mary",
            "last_name": "Librarian",
            "email": "mary.librarian@test.edu",
            "phone": "+254700000601",
            "portal_role": UserRole.LIBRARIAN,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def teacher(db, library_tenant):
    return onboard_staff(
        library_tenant,
        data={
            "first_name": "Tim",
            "last_name": "Teacher",
            "email": "tim.teacher@test.edu",
            "phone": "+254700000602",
            "portal_role": UserRole.TEACHER,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def library_setup(db, library_tenant):
    year = AcademicYear.objects.create(
        tenant=library_tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    school_class = Class.objects.create(
        tenant=library_tenant, name="Grade 6", code="G6", academic_year=year,
    )
    student = Student.objects.create(
        tenant=library_tenant,
        admission_number="LIB-001",
        first_name="Jane",
        last_name="Okello",
        date_of_birth=date(2014, 2, 2),
        gender="female",
        school_class=school_class,
        enrollment_date=date(2026, 1, 10),
        status="active",
    )
    book = Book.objects.create(
        tenant=library_tenant,
        title="Physics Basics",
        author="John Smith",
        isbn="978-0000000001",
        total_copies=3,
        available_copies=3,
    )
    return {"student": student, "book": book}


@pytest.mark.django_db
class TestLibraryRoleDefaults:
    def test_librarian_has_full_library_write(self):
        assert get_default_feature_permission(UserRole.LIBRARIAN, "borrowing") == {
            "can_read": True, "can_write": True,
        }
        assert get_default_feature_permission(UserRole.LIBRARIAN, "library_reports") == {
            "can_read": True, "can_write": False,
        }
        assert get_default_feature_permission(UserRole.LIBRARIAN, "dashboard_analytics") == {
            "can_read": True, "can_write": False,
        }

    def test_librarian_effective_permissions(self, library_tenant, librarian):
        perms = get_user_feature_permissions(library_tenant, librarian.user)
        assert perms["borrowing"]["can_write"] is True
        assert perms["returns"]["can_write"] is True
        assert perms.get("dashboard_analytics", {}).get("can_write") in (None, False)


@pytest.mark.django_db
class TestLibraryWorkflowAPI:
    def test_issue_and_return_book(self, library_setup, librarian):
        client = APIClient()
        client.force_authenticate(user=librarian.user)
        book = library_setup["book"]
        student = library_setup["student"]
        borrowed = date.today()
        due = borrowed + timedelta(days=14)

        issue = client.post(
            "/api/v1/library/borrows/",
            {
                "book": str(book.id),
                "student": str(student.id),
                "borrower_type": "student",
                "borrowed_date": str(borrowed),
                "due_date": str(due),
            },
            format="json",
        )
        assert issue.status_code == 201
        record = BorrowRecord.objects.get(pk=issue.data["id"])
        assert record.status == BORROW_BORROWED
        book.refresh_from_db()
        assert book.available_copies == 2

        returned = client.post(f"/api/v1/library/borrows/{record.id}/return/")
        assert returned.status_code == 200
        record.refresh_from_db()
        assert record.status == BORROW_RETURNED
        book.refresh_from_db()
        assert book.available_copies == 3

    def test_renew_active_loan(self, library_setup, librarian):
        client = APIClient()
        client.force_authenticate(user=librarian.user)
        book = library_setup["book"]
        student = library_setup["student"]
        borrowed = date.today()
        due = borrowed + timedelta(days=14)

        issue = client.post(
            "/api/v1/library/borrows/",
            {
                "book": str(book.id),
                "student": str(student.id),
                "borrower_type": "student",
                "borrowed_date": str(borrowed),
                "due_date": str(due),
            },
            format="json",
        )
        record = BorrowRecord.objects.get(pk=issue.data["id"])
        original_due = record.due_date

        renew = client.post(f"/api/v1/library/borrows/{record.id}/renew/")
        assert renew.status_code == 200
        record.refresh_from_db()
        assert record.due_date == original_due + timedelta(days=14)
        assert record.renewal_count == 1

    def test_librarian_workspace_api(self, library_tenant, librarian):
        client = APIClient()
        client.force_authenticate(user=librarian.user)
        response = client.get("/api/v1/library/workspace/")
        assert response.status_code == 200
        assert response.data["data"]["role"] == UserRole.LIBRARIAN
        assert "counts" in response.data["data"]
        assert "quick_links" in response.data["data"]

    def test_teacher_cannot_access_library_borrows(self, library_setup, teacher):
        client = APIClient()
        client.force_authenticate(user=teacher.user)
        response = client.get("/api/v1/library/borrows/")
        assert response.status_code == 403

    def test_teacher_cannot_access_library_workspace(self, teacher):
        client = APIClient()
        client.force_authenticate(user=teacher.user)
        response = client.get("/api/v1/library/workspace/")
        assert response.status_code == 403

    def test_permission_matrix_includes_librarian_role(self, library_tenant, librarian):
        from django.contrib.auth import get_user_model

        admin = get_user_model().objects.create_user(
            email="lib-admin@test.edu",
            password="TestPass@2026",
            first_name="Lib",
            last_name="Admin",
            role=UserRole.SCHOOL_ADMIN,
            tenant=library_tenant,
            is_email_verified=True,
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get("/api/v1/tenants/role-permissions/")
        role_keys = {r["key"] for r in response.data["data"]["roles"]}
        assert UserRole.LIBRARIAN in role_keys