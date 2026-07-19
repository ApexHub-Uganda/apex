"""Fee-clearance gate for parent results + parent portal scoping."""
from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class, Term
from apps.core.constants import UserRole
from apps.finance.constants import BALANCE_CLEARED, BALANCE_DEBTOR
from apps.finance.models import StudentFeeBalance
from apps.finance.results_access import compute_student_fee_clearance, update_school_results_policy
from apps.students.models import Parent, Student
from apps.subscriptions.services import assign_plan_features


@pytest.fixture
def parent_plan(db, plan):
    assign_plan_features(plan, [
        "parent_fee_statements", "student_billing", "report_cards",
        "timetables", "homework", "student_attendance", "examination_management",
        "bursar_workspace", "fee_structures",
    ])
    return plan


@pytest.fixture
def academic_setup(db, tenant):
    year = AcademicYear.objects.create(
        tenant=tenant, name="2026", start_date="2026-01-01", end_date="2026-12-31", is_current=True,
    )
    term = Term.objects.create(
        tenant=tenant, academic_year=year, name="Term 1", term_number=1,
        start_date="2026-01-10", end_date="2026-04-10", is_current=True,
    )
    school_class = Class.objects.create(
        tenant=tenant, name="Grade 5", code="G5", academic_year=year,
    )
    return {"year": year, "term": term, "class": school_class}


@pytest.fixture
def parent_user(db, tenant, parent_plan, academic_setup):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        email="parent.portal@test.edu",
        password="TestPass@2026",
        first_name="Pat",
        last_name="Parent",
        role=UserRole.PARENT,
        tenant=tenant,
    )
    parent = Parent.objects.create(
        tenant=tenant,
        user=user,
        first_name="Pat",
        last_name="Parent",
        email=user.email,
        phone="+254700000010",
        has_portal_access=True,
    )
    student = Student.objects.create(
        tenant=tenant,
        admission_number="P-001",
        first_name="Kid",
        last_name="Parent",
        date_of_birth="2014-01-01",
        gender="female",
        enrollment_date="2026-01-15",
        school_class=academic_setup["class"],
    )
    student.parents.add(parent)
    return {"user": user, "parent": parent, "student": student, "term": academic_setup["term"]}


@pytest.mark.django_db
class TestResultsAccessPolicy:
    def test_clearance_blocks_when_under_threshold(self, tenant, parent_user, school_admin):
        student = parent_user["student"]
        term = parent_user["term"]
        update_school_results_policy(
            tenant, actor=school_admin, default_cleared_percent=100, is_active=True,
        )
        StudentFeeBalance.objects.create(
            tenant=tenant,
            student=student,
            term=term,
            total_billed=Decimal("1000"),
            total_paid=Decimal("400"),
            balance=Decimal("600"),
            status=BALANCE_DEBTOR,
        )
        clearance = compute_student_fee_clearance(tenant=tenant, student=student, term=term)
        assert clearance["results_allowed"] is False
        assert Decimal(clearance["cleared_percent"]) == Decimal("40.00")

    def test_clearance_allows_when_threshold_met(self, tenant, parent_user, school_admin):
        student = parent_user["student"]
        term = parent_user["term"]
        update_school_results_policy(
            tenant, actor=school_admin, default_cleared_percent=50, is_active=True,
        )
        StudentFeeBalance.objects.create(
            tenant=tenant,
            student=student,
            term=term,
            total_billed=Decimal("1000"),
            total_paid=Decimal("600"),
            balance=Decimal("400"),
            status=BALANCE_DEBTOR,
        )
        clearance = compute_student_fee_clearance(tenant=tenant, student=student, term=term)
        assert clearance["results_allowed"] is True

    def test_bursar_can_update_policy(self, api_client, tenant, parent_plan, school_admin):
        api_client.force_authenticate(user=school_admin)
        response = api_client.put(
            "/api/v1/finance/results-access-policy/",
            {"default_cleared_percent": "75", "is_active": True, "notes": "Mid-term policy"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["data"]["default_cleared_percent"] == "75.00"

    def test_parent_portal_overview_lists_children(self, api_client, parent_user):
        api_client.force_authenticate(user=parent_user["user"])
        response = api_client.get("/api/v1/students/portal/overview/")
        assert response.status_code == 200
        children = response.data["data"]["children"]
        assert len(children) == 1
        assert children[0]["admission_number"] == "P-001"

    def test_parent_academics_locks_results_when_fees_outstanding(
        self, api_client, tenant, parent_user, school_admin,
    ):
        student = parent_user["student"]
        term = parent_user["term"]
        update_school_results_policy(
            tenant, actor=school_admin, default_cleared_percent=100, is_active=True,
        )
        StudentFeeBalance.objects.create(
            tenant=tenant,
            student=student,
            term=term,
            total_billed=Decimal("500"),
            total_paid=Decimal("0"),
            balance=Decimal("500"),
            status=BALANCE_DEBTOR,
        )
        api_client.force_authenticate(user=parent_user["user"])
        response = api_client.get("/api/v1/students/portal/academics/")
        assert response.status_code == 200
        child = response.data["data"]["children"][0]
        results = child["sections"].get("results") or {}
        assert results.get("locked") is True

    def test_clearance_is_per_term_only_no_all_terms_fallback(
        self, tenant, parent_user, school_admin, academic_setup,
    ):
        """Prior-term payments must not unlock current-term results."""
        student = parent_user["student"]
        current_term = parent_user["term"]
        year = academic_setup["year"]
        prior_term = Term.objects.create(
            tenant=tenant,
            academic_year=year,
            name="Prior Term",
            term_number=0,
            start_date="2025-09-01",
            end_date="2025-12-15",
            is_current=False,
        )
        update_school_results_policy(
            tenant, actor=school_admin, default_cleared_percent=100, is_active=True,
        )
        # Fully paid prior term — must not count toward current term.
        StudentFeeBalance.objects.create(
            tenant=tenant,
            student=student,
            term=prior_term,
            total_billed=Decimal("1000"),
            total_paid=Decimal("1000"),
            balance=Decimal("0"),
            status=BALANCE_CLEARED,
        )
        # Unpaid current term.
        StudentFeeBalance.objects.create(
            tenant=tenant,
            student=student,
            term=current_term,
            total_billed=Decimal("1000"),
            total_paid=Decimal("0"),
            balance=Decimal("1000"),
            status=BALANCE_DEBTOR,
        )
        clearance = compute_student_fee_clearance(tenant=tenant, student=student)
        assert clearance["scope"] == "term"
        assert clearance["term_id"] == str(current_term.id)
        assert clearance["results_allowed"] is False
        assert Decimal(clearance["cleared_percent"]) == Decimal("0.00")

    def test_clearance_locks_when_no_active_term(self, tenant, parent_user, school_admin):
        student = parent_user["student"]
        Term.objects.filter(tenant=tenant).update(is_current=False)
        # Also push end dates into the past so get_active_term finds nothing.
        Term.objects.filter(tenant=tenant).update(end_date="2020-01-01")
        update_school_results_policy(
            tenant, actor=school_admin, default_cleared_percent=50, is_active=True,
        )
        clearance = compute_student_fee_clearance(tenant=tenant, student=student)
        assert clearance["scope"] == "no_active_term"
        assert clearance["results_allowed"] is False
