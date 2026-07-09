"""Phase 3–5 library workflow API tests."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class
from apps.core.constants import UserRole
from apps.library.constants import BORROW_BORROWED, RESERVATION_PENDING
from apps.library.models import Book, BookReservation, BorrowRecord, LibraryFine
from apps.staff.services import onboard_staff
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def library_workflow_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Library Workflow Plan", slug="lib-workflow", max_students=500)
    assign_plan_features(plan, [
        "librarian_workspace", "library_management", "borrowing", "returns",
        "reservations", "library_fines", "library_reports", "student_management",
    ])
    return plan


@pytest.fixture
def library_workflow_tenant(db, library_workflow_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Library Workflow School",
        code="LIBW",
        email="libw@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=library_workflow_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def lib_user(db, library_workflow_tenant):
    return onboard_staff(
        library_workflow_tenant,
        data={
            "first_name": "Lib",
            "last_name": "Workflow",
            "email": "lib.workflow@test.edu",
            "phone": "+254700000801",
            "portal_role": UserRole.LIBRARIAN,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def lib_setup(db, library_workflow_tenant):
    year = AcademicYear.objects.create(
        tenant=library_workflow_tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    school_class = Class.objects.create(
        tenant=library_workflow_tenant, name="Grade 5", code="G5", academic_year=year,
    )
    student = Student.objects.create(
        tenant=library_workflow_tenant,
        admission_number="LIBW-001",
        first_name="Alex",
        last_name="Mukasa",
        date_of_birth=date(2015, 1, 1),
        gender="male",
        school_class=school_class,
        enrollment_date=date(2026, 1, 10),
        status="active",
    )
    book = Book.objects.create(
        tenant=library_workflow_tenant,
        title="Chemistry 101",
        author="Dr. Kim",
        isbn="978-0000000099",
        total_copies=2,
        available_copies=2,
    )
    return {"student": student, "book": book}


@pytest.mark.django_db
class TestLibraryWorkflowAPI:
    def test_fulfill_reservation(self, lib_setup, lib_user):
        reservation = BookReservation.objects.create(
            tenant=lib_setup["book"].tenant,
            book=lib_setup["book"],
            student=lib_setup["student"],
            borrower_type="student",
            reserved_date=date.today(),
            expires_date=date.today() + timedelta(days=7),
            status=RESERVATION_PENDING,
        )
        client = APIClient()
        client.force_authenticate(user=lib_user.user)
        response = client.post(f"/api/v1/library/reservations/{reservation.id}/fulfill/")
        assert response.status_code == 200
        reservation.refresh_from_db()
        assert reservation.status == "fulfilled"
        assert BorrowRecord.objects.filter(book=lib_setup["book"], student=lib_setup["student"]).exists()

    def test_mark_fine_paid(self, lib_setup, lib_user):
        record = BorrowRecord.objects.create(
            tenant=lib_setup["book"].tenant,
            book=lib_setup["book"],
            student=lib_setup["student"],
            borrower_type="student",
            borrowed_date=date.today() - timedelta(days=20),
            due_date=date.today() - timedelta(days=5),
            status=BORROW_BORROWED,
        )
        fine = LibraryFine.objects.create(
            tenant=lib_setup["book"].tenant,
            borrow_record=record,
            student=lib_setup["student"],
            amount="2500.00",
            status="pending",
        )
        client = APIClient()
        client.force_authenticate(user=lib_user.user)
        response = client.post(f"/api/v1/library/library-fines/{fine.id}/mark-paid/")
        assert response.status_code == 200
        fine.refresh_from_db()
        assert fine.status == "paid"

    def test_library_reports_api(self, lib_user):
        client = APIClient()
        client.force_authenticate(user=lib_user.user)
        response = client.get("/api/v1/library/reports/?type=inventory")
        assert response.status_code == 200
        assert "rows" in response.data["data"]

    def test_workspace_active_loan_keys(self, lib_setup, lib_user):
        BorrowRecord.objects.create(
            tenant=lib_setup["book"].tenant,
            book=lib_setup["book"],
            student=lib_setup["student"],
            borrower_type="student",
            borrowed_date=date.today(),
            due_date=date.today() + timedelta(days=14),
            status=BORROW_BORROWED,
        )
        client = APIClient()
        client.force_authenticate(user=lib_user.user)
        response = client.get("/api/v1/library/workspace/")
        assert response.status_code == 200
        counts = response.data["data"]["counts"]
        assert counts["active_loans"] == counts["active_borrows"]