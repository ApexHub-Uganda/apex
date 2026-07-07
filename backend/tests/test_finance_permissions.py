"""Finance endpoint permission enforcement — every use case gated by Permission Settings."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class, Term
from apps.core.constants import UserRole
from apps.finance.models import FeePayment, FeeStructure
from apps.staff.services import onboard_staff
from apps.students.models import Parent, Student
from apps.subscriptions.services import assign_plan_features
from apps.tenants.role_permissions import (
    get_user_feature_permissions,
    reset_role_permissions,
    save_role_permissions,
    user_can_access_feature,
)


FINANCE_FEATURES = [
    "bursar_workspace", "assistant_bursar_workspace",
    "fee_structures", "fee_categories", "discounts", "student_billing",
    "invoice_generation", "payment_recording", "misc_income", "refunds",
    "debtor_management", "finance_notes", "expenses", "financial_reports",
    "transaction_approval", "budget_management", "financial_accounts",
    "accounting_periods", "finance_analytics", "parent_fee_statements",
    "classes", "student_management",
]


@pytest.fixture
def finance_plan(db):
    from apps.subscriptions.models import Plan
    from apps.subscriptions.seed_features import seed_feature_catalog

    seed_feature_catalog()
    plan = Plan.objects.create(name="Finance Perm Plan", slug="finance-perm", max_students=500)
    assign_plan_features(plan, FINANCE_FEATURES)
    return plan


@pytest.fixture
def finance_tenant(db, finance_plan):
    from apps.subscriptions.models import Subscription
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.create(
        name="Finance Perm School",
        code="FPER",
        email="fperm@test.edu",
        status="active",
        is_verified=True,
    )
    sub = Subscription.objects.create(tenant=tenant, plan=finance_plan, status="active")
    sub.activate(period_days=30)
    return tenant


@pytest.fixture
def teacher_no_finance(db, finance_tenant):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        email="teacher.nofin@test.edu",
        password="TestPass@2026",
        first_name="No",
        last_name="Finance",
        role=UserRole.TEACHER,
        tenant=finance_tenant,
        is_email_verified=True,
    )


@pytest.fixture
def assistant_bursar(db, finance_tenant):
    return onboard_staff(
        finance_tenant,
        data={
            "first_name": "Assist",
            "last_name": "Bursar",
            "email": "assist.perm@test.edu",
            "phone": "+254700000601",
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
            "email": "bursar.perm@test.edu",
            "phone": "+254700000602",
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
        admission_number="FPER-001",
        first_name="Jane",
        last_name="Nakato",
        date_of_birth=date(2014, 2, 2),
        gender="female",
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


@pytest.fixture
def parent_user(db, finance_tenant, finance_setup):
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_user(
        email="parent.perm@test.edu",
        password="TestPass@2026",
        first_name="Parent",
        last_name="User",
        role=UserRole.PARENT,
        tenant=finance_tenant,
        is_email_verified=True,
    )
    parent = Parent.objects.create(
        tenant=finance_tenant,
        user=user,
        first_name="Parent",
        last_name="User",
        email="parent.perm@test.edu",
        phone="+254700000603",
    )
    parent.children.add(finance_setup["student"])
    return user


def _deny_all_finance(tenant, role: str):
    save_role_permissions(tenant, [{
        "role": role,
        "module_key": "finance",
        "can_read": False,
        "can_write": False,
    }])


@pytest.mark.django_db
class TestFinanceEndpointPermissions:
    ENDPOINTS = [
        ("GET", "/api/v1/finance/payments/", "payment_recording"),
        ("GET", "/api/v1/finance/invoices/", "invoice_generation"),
        ("GET", "/api/v1/finance/discounts/", "discounts"),
        ("GET", "/api/v1/finance/refunds/", "refunds"),
        ("GET", "/api/v1/finance/balances/", "debtor_management"),
        ("GET", "/api/v1/finance/misc-income/", "misc_income"),
        ("GET", "/api/v1/finance/notes/", "finance_notes"),
        ("GET", "/api/v1/finance/accounts/", "financial_accounts"),
        ("GET", "/api/v1/finance/budgets/", "budget_management"),
        ("GET", "/api/v1/finance/periods/", "accounting_periods"),
        ("GET", "/api/v1/finance/accounting/", "expenses"),
        ("GET", "/api/v1/finance/fee-structures/", "fee_structures"),
        ("GET", "/api/v1/finance/fee-categories/", "fee_categories"),
        ("GET", "/api/v1/finance/workspace/", "bursar_workspace"),
        ("GET", "/api/v1/finance/approval-queue/", "transaction_approval"),
        ("GET", "/api/v1/finance/analytics/", "finance_analytics"),
        ("GET", "/api/v1/finance/reports/", "financial_reports"),
    ]

    @pytest.mark.parametrize("method,url,feature", ENDPOINTS)
    def test_teacher_denied_without_feature_grant(self, finance_tenant, teacher_no_finance, method, url, feature):
        _deny_all_finance(finance_tenant, UserRole.TEACHER)
        client = APIClient()
        client.force_authenticate(user=teacher_no_finance)
        response = client.generic(method, url)
        assert response.status_code == 403, f"{method} {url} should be 403 without {feature}"

    def test_assistant_cannot_access_analytics_without_grant(self, finance_tenant, assistant_bursar):
        save_role_permissions(finance_tenant, [
            {"role": UserRole.ASSISTANT_BURSAR, "feature_key": "finance_analytics", "can_read": False, "can_write": False},
        ])
        client = APIClient()
        client.force_authenticate(user=assistant_bursar.user)
        assert client.get("/api/v1/finance/analytics/").status_code == 403

    def test_bursar_can_access_analytics_with_default_grant(self, bursar):
        client = APIClient()
        client.force_authenticate(user=bursar.user)
        response = client.get("/api/v1/finance/analytics/")
        assert response.status_code == 200
        assert "summary" in response.data["data"]

    def test_bursar_can_export_reports(self, bursar):
        client = APIClient()
        client.force_authenticate(user=bursar.user)
        response = client.get("/api/v1/finance/reports/?type=collections")
        assert response.status_code == 200
        assert "rows" in response.data["data"]

    def test_payment_receipt_requires_feature(self, finance_setup, assistant_bursar, bursar):
        payment = FeePayment.objects.create(
            tenant=finance_setup["structure"].tenant,
            student=finance_setup["student"],
            fee_structure=finance_setup["structure"],
            amount_paid=Decimal("50000"),
            payment_date=date(2026, 3, 2),
            approval_status="approved",
            status="completed",
            received_by=assistant_bursar.user,
            receipt_number="RCP-TEST-001",
        )
        client = APIClient()
        client.force_authenticate(user=assistant_bursar.user)
        assert client.get(f"/api/v1/finance/payments/{payment.id}/receipt/").status_code == 200

        _deny_all_finance(finance_setup["structure"].tenant, UserRole.ASSISTANT_BURSAR)
        denied = APIClient()
        denied.force_authenticate(user=assistant_bursar.user)
        assert denied.get(f"/api/v1/finance/payments/{payment.id}/receipt/").status_code == 403

    def test_parent_statements_scoped_to_linked_child(self, finance_tenant, parent_user, finance_setup):
        client = APIClient()
        client.force_authenticate(user=parent_user)
        response = client.get("/api/v1/finance/parent-statements/")
        assert response.status_code == 200
        children = response.data["data"]["children"]
        assert len(children) == 1
        assert children[0]["student"]["admission_number"] == "FPER-001"

    def test_parent_denied_without_feature_grant(self, finance_tenant, parent_user):
        _deny_all_finance(finance_tenant, UserRole.PARENT)
        client = APIClient()
        client.force_authenticate(user=parent_user)
        assert client.get("/api/v1/finance/parent-statements/").status_code == 403

    def test_parent_cannot_access_staff_finance_endpoints(self, parent_user):
        client = APIClient()
        client.force_authenticate(user=parent_user)
        assert client.get("/api/v1/finance/payments/").status_code == 403
        assert client.get("/api/v1/finance/analytics/").status_code == 403

    def test_assistant_granted_approval_can_approve(self, finance_setup, assistant_bursar, finance_tenant):
        save_role_permissions(finance_tenant, [
            {"role": UserRole.ASSISTANT_BURSAR, "feature_key": "transaction_approval", "can_read": True, "can_write": True},
        ])
        payment = FeePayment.objects.create(
            tenant=finance_tenant,
            student=finance_setup["student"],
            fee_structure=finance_setup["structure"],
            amount_paid=Decimal("25000"),
            payment_date=date(2026, 3, 5),
            approval_status="pending",
            status="pending",
            received_by=assistant_bursar.user,
        )
        client = APIClient()
        client.force_authenticate(user=assistant_bursar.user)
        response = client.post(f"/api/v1/finance/payments/{payment.id}/approve/")
        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.approval_status == "approved"
        assert payment.receipt_number.startswith("RCP-")


STAFF_FINANCE_ENDPOINTS = [
    ("GET", "/api/v1/finance/payments/"),
    ("GET", "/api/v1/finance/invoices/"),
    ("GET", "/api/v1/finance/discounts/"),
    ("GET", "/api/v1/finance/refunds/"),
    ("GET", "/api/v1/finance/balances/"),
    ("GET", "/api/v1/finance/misc-income/"),
    ("GET", "/api/v1/finance/notes/"),
    ("GET", "/api/v1/finance/accounts/"),
    ("GET", "/api/v1/finance/budgets/"),
    ("GET", "/api/v1/finance/periods/"),
    ("GET", "/api/v1/finance/accounting/"),
    ("GET", "/api/v1/finance/fee-structures/"),
    ("GET", "/api/v1/finance/fee-categories/"),
    ("GET", "/api/v1/finance/workspace/"),
    ("GET", "/api/v1/finance/approval-queue/"),
    ("GET", "/api/v1/finance/analytics/"),
    ("GET", "/api/v1/finance/reports/"),
    ("POST", "/api/v1/finance/payments/"),
]


@pytest.mark.django_db
class TestFinanceWithoutAdminGrants:
    """No access when School Admin has not granted finance (module or feature)."""

    @pytest.mark.parametrize("method,url", STAFF_FINANCE_ENDPOINTS)
    def test_teacher_blocked_with_no_permission_settings(self, finance_tenant, teacher_no_finance, method, url):
        reset_role_permissions(finance_tenant, UserRole.TEACHER)
        assert not user_can_access_feature(finance_tenant, teacher_no_finance, "payment_recording")
        client = APIClient()
        client.force_authenticate(user=teacher_no_finance)
        response = client.generic(method, url, data={} if method == "POST" else None, format="json")
        assert response.status_code == 403, f"{method} {url} must be 403 for teacher without admin grants"

    @pytest.mark.parametrize("method,url", STAFF_FINANCE_ENDPOINTS)
    def test_bursar_blocked_when_admin_denies_finance_module(self, finance_tenant, bursar, method, url):
        _deny_all_finance(finance_tenant, UserRole.BURSAR)
        perms = get_user_feature_permissions(finance_tenant, bursar.user)
        assert not perms.get("payment_recording", {}).get("can_read")
        assert not perms.get("finance_analytics", {}).get("can_read")
        client = APIClient()
        client.force_authenticate(user=bursar.user)
        response = client.generic(method, url, data={} if method == "POST" else None, format="json")
        assert response.status_code == 403, f"{method} {url} must be 403 when admin denies finance"

    @pytest.mark.parametrize("method,url", STAFF_FINANCE_ENDPOINTS)
    def test_assistant_blocked_when_admin_denies_finance_module(
        self, finance_tenant, assistant_bursar, method, url,
    ):
        _deny_all_finance(finance_tenant, UserRole.ASSISTANT_BURSAR)
        perms = get_user_feature_permissions(finance_tenant, assistant_bursar.user)
        assert not perms.get("payment_recording", {}).get("can_read")
        assert not perms.get("transaction_approval", {}).get("can_read")
        client = APIClient()
        client.force_authenticate(user=assistant_bursar.user)
        response = client.generic(method, url, data={} if method == "POST" else None, format="json")
        assert response.status_code == 403, f"{method} {url} must be 403 when admin denies finance"

    def test_assistant_cannot_approve_without_transaction_approval_grant(
        self, finance_setup, assistant_bursar, finance_tenant,
    ):
        reset_role_permissions(finance_tenant, UserRole.ASSISTANT_BURSAR)
        assert not user_can_access_feature(
            finance_tenant, assistant_bursar.user, "transaction_approval", require_write=True,
        )
        payment = FeePayment.objects.create(
            tenant=finance_tenant,
            student=finance_setup["student"],
            fee_structure=finance_setup["structure"],
            amount_paid=Decimal("30000"),
            payment_date=date(2026, 3, 8),
            approval_status="pending",
            status="pending",
            received_by=assistant_bursar.user,
        )
        client = APIClient()
        client.force_authenticate(user=assistant_bursar.user)
        assert client.post(f"/api/v1/finance/payments/{payment.id}/approve/").status_code == 403
        assert client.get("/api/v1/finance/approval-queue/").status_code == 403

    def test_parent_statements_blocked_without_admin_grant(self, finance_tenant, parent_user):
        _deny_all_finance(finance_tenant, UserRole.PARENT)
        assert not user_can_access_feature(finance_tenant, parent_user, "parent_fee_statements")
        client = APIClient()
        client.force_authenticate(user=parent_user)
        assert client.get("/api/v1/finance/parent-statements/").status_code == 403

    def test_granular_deny_blocks_single_feature_while_others_remain(
        self, finance_tenant, bursar,
    ):
        save_role_permissions(finance_tenant, [
            {"role": UserRole.BURSAR, "feature_key": "finance_analytics", "can_read": False, "can_write": False},
        ])
        assert not user_can_access_feature(finance_tenant, bursar.user, "finance_analytics")
        assert user_can_access_feature(finance_tenant, bursar.user, "payment_recording")
        client = APIClient()
        client.force_authenticate(user=bursar.user)
        assert client.get("/api/v1/finance/analytics/").status_code == 403
        assert client.get("/api/v1/finance/payments/").status_code == 200