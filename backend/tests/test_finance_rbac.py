"""Finance RBAC and approval workflow tests."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class, Term
from apps.core.constants import UserRole
from apps.finance.constants import APPROVAL_APPROVED, APPROVAL_PENDING
from apps.finance.models import FeePayment, FeeStructure
from apps.staff.services import onboard_staff
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features
from apps.tenants.role_feature_defaults import get_default_feature_permission
from apps.tenants.role_permissions import get_user_feature_permissions


@pytest.fixture
def finance_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Finance RBAC Plan", slug="finance-rbac", max_students=500)
    assign_plan_features(plan, [
        "bursar_workspace", "assistant_bursar_workspace",
        "fee_structures", "fee_categories", "discounts", "student_billing",
        "invoice_generation", "payment_recording", "misc_income", "refunds",
        "debtor_management", "finance_notes", "expenses", "financial_reports",
        "transaction_approval", "budget_management", "financial_accounts",
        "accounting_periods", "finance_analytics", "classes", "student_management",
    ])
    return plan


@pytest.fixture
def finance_tenant(db, finance_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Finance RBAC School",
        code="FINR",
        email="finr@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=finance_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def assistant_bursar(db, finance_tenant):
    return onboard_staff(
        finance_tenant,
        data={
            "first_name": "Assist",
            "last_name": "Bursar",
            "email": "assist.bursar@test.edu",
            "phone": "+254700000501",
            "portal_role": UserRole.ASSISTANT_BURSAR,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def bursar(db, finance_tenant):
    return onboard_staff(
        finance_tenant,
        data={
            "first_name": "Head",
            "last_name": "Bursar",
            "email": "head.bursar@test.edu",
            "phone": "+254700000502",
            "portal_role": UserRole.BURSAR,
            "date_joined": "2026-01-01",
        },
    )


@pytest.fixture
def finance_setup(db, finance_tenant):
    year = AcademicYear.objects.create(
        tenant=finance_tenant,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    term = Term.objects.create(
        tenant=finance_tenant,
        academic_year=year,
        name="Term 1",
        term_number=1,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 4, 10),
        is_current=True,
    )
    school_class = Class.objects.create(
        tenant=finance_tenant, name="Grade 6", code="G6", academic_year=year,
    )
    student = Student.objects.create(
        tenant=finance_tenant,
        admission_number="FIN-001",
        first_name="Peter",
        last_name="Okello",
        date_of_birth=date(2014, 2, 2),
        gender="male",
        school_class=school_class,
        enrollment_date=date(2026, 1, 10),
        status="active",
    )
    structure = FeeStructure.objects.create(
        tenant=finance_tenant,
        name="Tuition Term 1",
        school_class=school_class,
        term=term,
        amount=Decimal("500000"),
        due_date=date(2026, 2, 1),
    )
    return {"student": student, "structure": structure, "term": term}


@pytest.mark.django_db
class TestFinanceRoleDefaults:
    def test_assistant_bursar_can_record_payments_not_approve(self):
        assert get_default_feature_permission(UserRole.ASSISTANT_BURSAR, "payment_recording") == {
            "can_read": True, "can_write": True,
        }
        assert get_default_feature_permission(UserRole.ASSISTANT_BURSAR, "transaction_approval") == {
            "can_read": False, "can_write": False,
        }
        assert get_default_feature_permission(UserRole.ASSISTANT_BURSAR, "fee_structures") == {
            "can_read": True, "can_write": False,
        }

    def test_bursar_has_full_finance_write(self):
        assert get_default_feature_permission(UserRole.BURSAR, "transaction_approval") == {
            "can_read": True, "can_write": True,
        }
        assert get_default_feature_permission(UserRole.BURSAR, "fee_structures") == {
            "can_read": True, "can_write": True,
        }
        assert get_default_feature_permission(UserRole.BURSAR, "budget_management") == {
            "can_read": True, "can_write": True,
        }

    def test_assistant_bursar_effective_permissions(self, finance_tenant, assistant_bursar):
        perms = get_user_feature_permissions(finance_tenant, assistant_bursar.user)
        assert perms["payment_recording"]["can_write"] is True
        assert perms.get("transaction_approval", {}).get("can_write") in (None, False)


@pytest.mark.django_db
class TestFinanceWorkflowAPI:
    def test_assistant_payment_requires_approval(self, finance_setup, assistant_bursar, bursar):
        client = APIClient()
        client.force_authenticate(user=assistant_bursar.user)
        response = client.post(
            "/api/v1/finance/payments/",
            {
                "student": str(finance_setup["student"].id),
                "fee_structure": str(finance_setup["structure"].id),
                "amount_paid": "100000",
                "payment_date": "2026-03-01",
                "payment_method": "cash",
            },
            format="json",
        )
        assert response.status_code == 201
        payment = FeePayment.objects.get(pk=response.data["id"])
        assert payment.approval_status == APPROVAL_PENDING

        bursar_client = APIClient()
        bursar_client.force_authenticate(user=bursar.user)
        approve = bursar_client.post(f"/api/v1/finance/payments/{payment.id}/approve/")
        assert approve.status_code == 200
        payment.refresh_from_db()
        assert payment.approval_status == APPROVAL_APPROVED

    def test_assistant_cannot_approve_payment(self, finance_setup, assistant_bursar):
        payment = FeePayment.objects.create(
            tenant=finance_setup["structure"].tenant,
            student=finance_setup["student"],
            fee_structure=finance_setup["structure"],
            amount_paid=Decimal("50000"),
            payment_date=date(2026, 3, 2),
            approval_status=APPROVAL_PENDING,
            status="pending",
            received_by=assistant_bursar.user,
        )
        client = APIClient()
        client.force_authenticate(user=assistant_bursar.user)
        response = client.post(f"/api/v1/finance/payments/{payment.id}/approve/")
        assert response.status_code == 403

    def test_bursar_workspace_api(self, finance_tenant, bursar):
        client = APIClient()
        client.force_authenticate(user=bursar.user)
        response = client.get("/api/v1/finance/workspace/")
        assert response.status_code == 200
        assert response.data["data"]["role"] == UserRole.BURSAR

    def test_assistant_cannot_access_approval_queue(self, assistant_bursar):
        client = APIClient()
        client.force_authenticate(user=assistant_bursar.user)
        response = client.get("/api/v1/finance/approval-queue/")
        assert response.status_code == 403

    def test_permission_matrix_includes_finance_roles(self, finance_tenant, bursar):
        from django.contrib.auth import get_user_model

        admin = get_user_model().objects.create_user(
            email="fin-admin@test.edu",
            password="TestPass@2026",
            first_name="Fin",
            last_name="Admin",
            role=UserRole.SCHOOL_ADMIN,
            tenant=finance_tenant,
            is_email_verified=True,
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.get("/api/v1/tenants/role-permissions/")
        role_keys = {r["key"] for r in response.data["data"]["roles"]}
        assert UserRole.ASSISTANT_BURSAR in role_keys
        assert UserRole.BURSAR in role_keys