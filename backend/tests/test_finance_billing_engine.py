"""Billing engine, balance sync, receipts, gateway stub tests."""
from __future__ import annotations

from decimal import Decimal
from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, Class, Term
from apps.core.constants import UserRole
from apps.finance.models import FeePayment, FeeStructure, Invoice, StudentFeeBalance
from apps.finance.services.billing import bill_class_for_term, bill_student_for_term
from apps.finance.services.balances import sync_student_fee_balance
from apps.finance.services.documents import build_receipt_pdf
from apps.finance.services.gateway import get_gateway
from apps.finance.services.payments_core import record_fee_payment
from apps.students.models import Student
from apps.subscriptions.services import assign_plan_features
from apps.staff.services import onboard_staff


@pytest.fixture
def finance_full_plan(db, plan):
    assign_plan_features(plan, [
        "bursar_workspace", "assistant_bursar_workspace",
        "fee_structures", "fee_categories", "discounts", "student_billing",
        "invoice_generation", "payment_recording", "misc_income", "refunds",
        "debtor_management", "finance_notes", "expenses", "financial_reports",
        "transaction_approval", "budget_management", "financial_accounts",
        "accounting_periods", "finance_analytics", "parent_fee_statements",
        "classes", "student_management",
    ])
    return plan


@pytest.fixture
def school_setup(db, tenant, finance_full_plan):
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
    fs = FeeStructure.objects.create(
        tenant=tenant, name="Tuition", school_class=school_class, term=term,
        amount=Decimal("100000"), due_date=date(2026, 2, 1), fee_category="tuition",
    )
    student = Student.objects.create(
        tenant=tenant, admission_number="FIN-001", first_name="Ada", last_name="Lovelace",
        date_of_birth="2014-01-01", gender="female", enrollment_date="2026-01-15",
        school_class=school_class, status="active",
    )
    return {
        "year": year, "term": term, "class": school_class, "structure": fs, "student": student,
    }


@pytest.fixture
def bursar_user(db, tenant, finance_full_plan):
    staff = onboard_staff(
        tenant,
        data={
            "first_name": "Bee", "last_name": "Ursar",
            "email": "bursar.fin@test.edu", "phone": "+254700000777",
            "portal_role": UserRole.BURSAR, "date_joined": "2026-01-01",
        },
    )
    return staff.user


@pytest.mark.django_db
class TestBillingAndBalances:
    def test_bill_student_creates_invoice_and_balance(self, tenant, school_setup, school_admin):
        inv = bill_student_for_term(
            tenant=tenant,
            student=school_setup["student"],
            term=school_setup["term"],
            actor=school_admin,
        )
        assert inv is not None
        assert inv.invoice_number.startswith("INV-")
        assert Decimal(inv.total_amount) == Decimal("100000")
        assert len(inv.line_items) == 1
        bal = StudentFeeBalance.objects.get(
            tenant=tenant, student=school_setup["student"], term=school_setup["term"],
        )
        assert Decimal(bal.total_billed) == Decimal("100000")
        assert Decimal(bal.balance) == Decimal("100000")
        assert bal.status == "debtor"

    def test_payment_reduces_balance_and_receipt_pdf(self, tenant, school_setup, school_admin):
        bill_student_for_term(
            tenant=tenant, student=school_setup["student"], term=school_setup["term"], actor=school_admin,
        )
        payment = record_fee_payment(
            tenant=tenant,
            user=school_admin,
            data={
                "student": str(school_setup["student"].id),
                "fee_structure": str(school_setup["structure"].id),
                "amount_paid": "40000",
                "payment_date": "2026-02-01",
                "payment_method": "cash",
            },
        )
        assert payment.receipt_number.startswith("RCP-")
        bal = StudentFeeBalance.objects.get(
            tenant=tenant, student=school_setup["student"], term=school_setup["term"],
        )
        assert Decimal(bal.total_paid) == Decimal("40000")
        assert Decimal(bal.balance) == Decimal("60000")
        inv = Invoice.objects.get(tenant=tenant, student=school_setup["student"], term=school_setup["term"])
        assert Decimal(inv.amount_paid) == Decimal("40000")
        pdf = build_receipt_pdf(tenant=tenant, payment=payment)
        assert pdf.startswith(b"%PDF")

    def test_term_isolation_prior_payments(self, tenant, school_setup, school_admin):
        year = school_setup["year"]
        term2 = Term.objects.create(
            tenant=tenant, academic_year=year, name="Term 2", term_number=2,
            start_date="2026-05-01", end_date="2026-08-01", is_current=False,
        )
        FeeStructure.objects.create(
            tenant=tenant, name="Tuition T2", school_class=school_setup["class"], term=term2,
            amount=Decimal("100000"), due_date=date(2026, 5, 15),
        )
        bill_student_for_term(
            tenant=tenant, student=school_setup["student"], term=school_setup["term"], actor=school_admin,
        )
        bill_student_for_term(
            tenant=tenant, student=school_setup["student"], term=term2, actor=school_admin,
        )
        record_fee_payment(
            tenant=tenant, user=school_admin,
            data={
                "student": str(school_setup["student"].id),
                "fee_structure": str(school_setup["structure"].id),
                "amount_paid": "100000",
                "payment_date": "2026-02-01",
                "payment_method": "cash",
            },
        )
        b1 = StudentFeeBalance.objects.get(student=school_setup["student"], term=school_setup["term"])
        b2 = StudentFeeBalance.objects.get(student=school_setup["student"], term=term2)
        assert Decimal(b1.balance) == Decimal("0")
        assert Decimal(b2.balance) == Decimal("100000")

    def test_bill_class_api(self, api_client, tenant, school_setup, school_admin):
        api_client.force_authenticate(user=school_admin)
        resp = api_client.post("/api/v1/finance/billing/bill-class/", {
            "school_class": str(school_setup["class"].id),
            "term": str(school_setup["term"].id),
        }, format="json")
        assert resp.status_code == 200, resp.data
        assert resp.data["data"]["created_count"] >= 1

    def test_gateway_not_configured(self, api_client, school_admin, school_setup):
        api_client.force_authenticate(user=school_admin)
        resp = api_client.post("/api/v1/finance/online-payments/", {
            "amount": "5000",
            "student": str(school_setup["student"].id),
            "gateway": "mpesa",
        }, format="json")
        assert resp.status_code == 503
        assert "future release" in (resp.data.get("message") or "").lower() or "not" in str(resp.data).lower()

    def test_receipt_pdf_endpoint(self, api_client, tenant, school_setup, school_admin):
        bill_student_for_term(
            tenant=tenant, student=school_setup["student"], term=school_setup["term"], actor=school_admin,
        )
        payment = record_fee_payment(
            tenant=tenant, user=school_admin,
            data={
                "student": str(school_setup["student"].id),
                "fee_structure": str(school_setup["structure"].id),
                "amount_paid": "1000",
                "payment_date": "2026-02-01",
                "payment_method": "cash",
            },
        )
        api_client.force_authenticate(user=school_admin)
        resp = api_client.get(f"/api/v1/finance/payments/{payment.id}/receipt.pdf")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"
        body = b"".join(resp.streaming_content) if hasattr(resp, "streaming_content") else resp.content
        assert body.startswith(b"%PDF")
