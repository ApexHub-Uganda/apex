"""Finance analytics and report builders."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.finance.constants import APPROVAL_APPROVED, BALANCE_DEBTOR
from apps.finance.models import (
    AccountingEntry,
    FeePayment,
    Invoice,
    MiscIncome,
    StudentFeeBalance,
)


def _decimal_str(value) -> str:
    return str(value or Decimal("0"))


def build_finance_analytics(*, tenant) -> dict[str, Any]:
    today = timezone.localdate()
    month_start = today.replace(day=1)

    payments_qs = FeePayment.objects.filter(
        tenant=tenant, is_deleted=False, approval_status=APPROVAL_APPROVED, status="completed",
    )
    total_collected = payments_qs.aggregate(total=Sum("amount_paid"))["total"] or Decimal("0")
    collected_today = payments_qs.filter(payment_date=today).aggregate(
        total=Sum("amount_paid"),
    )["total"] or Decimal("0")
    collected_this_month = payments_qs.filter(payment_date__gte=month_start).aggregate(
        total=Sum("amount_paid"),
    )["total"] or Decimal("0")

    outstanding = StudentFeeBalance.objects.filter(
        tenant=tenant, is_deleted=False, status=BALANCE_DEBTOR, balance__gt=0,
    ).aggregate(total=Sum("balance"), count=Count("id"))
    open_invoices = Invoice.objects.filter(
        tenant=tenant, is_deleted=False, status__in=["draft", "sent", "overdue"],
    ).count()
    expense_total = AccountingEntry.objects.filter(
        tenant=tenant, is_deleted=False, entry_type="expense",
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    misc_income_total = MiscIncome.objects.filter(
        tenant=tenant, is_deleted=False,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    by_method = list(
        payments_qs.values("payment_method")
        .annotate(total=Sum("amount_paid"), count=Count("id"))
        .order_by("-total")
    )
    monthly_trend = list(
        payments_qs.filter(payment_date__gte=today - timedelta(days=365))
        .annotate(month=TruncMonth("payment_date"))
        .values("month")
        .annotate(total=Sum("amount_paid"), count=Count("id"))
        .order_by("month")
    )
    for row in monthly_trend:
        row["month"] = row["month"].strftime("%Y-%m") if row.get("month") else ""

    return {
        "generated_at": timezone.now().isoformat(),
        "summary": {
            "total_collected": _decimal_str(total_collected),
            "collected_today": _decimal_str(collected_today),
            "collected_this_month": _decimal_str(collected_this_month),
            "outstanding_balance": _decimal_str(outstanding["total"]),
            "debtor_count": outstanding["count"] or 0,
            "open_invoices": open_invoices,
            "expense_total": _decimal_str(expense_total),
            "misc_income_total": _decimal_str(misc_income_total),
        },
        "collections_by_method": [
            {
                "payment_method": row["payment_method"],
                "total": _decimal_str(row["total"]),
                "count": row["count"],
            }
            for row in by_method
        ],
        "monthly_collections": [
            {
                "month": row["month"],
                "total": _decimal_str(row["total"]),
                "count": row["count"],
            }
            for row in monthly_trend
        ],
    }


def build_finance_reports(*, tenant, report_type: str = "collections", start_date: date | None = None, end_date: date | None = None) -> dict[str, Any]:
    today = timezone.localdate()
    start = start_date or (today - timedelta(days=30))
    end = end_date or today

    payload: dict[str, Any] = {
        "report_type": report_type,
        "period": {"start": str(start), "end": str(end)},
        "generated_at": timezone.now().isoformat(),
        "rows": [],
        "totals": {},
    }

    if report_type == "collections":
        payments = FeePayment.objects.filter(
            tenant=tenant,
            is_deleted=False,
            approval_status=APPROVAL_APPROVED,
            status="completed",
            payment_date__gte=start,
            payment_date__lte=end,
        ).select_related("student", "fee_structure").order_by("-payment_date")
        total = payments.aggregate(total=Sum("amount_paid"))["total"] or Decimal("0")
        payload["rows"] = [
            {
                "payment_date": str(p.payment_date),
                "student": p.student.full_name if p.student_id else "",
                "admission_number": p.student.admission_number if p.student_id else "",
                "fee_item": p.fee_structure.name if p.fee_structure_id else "",
                "amount": _decimal_str(p.amount_paid),
                "payment_method": p.payment_method,
                "receipt_number": p.receipt_number,
            }
            for p in payments
        ]
        payload["totals"] = {"amount": _decimal_str(total), "count": payments.count()}

    elif report_type == "debtors":
        balances = StudentFeeBalance.objects.filter(
            tenant=tenant, is_deleted=False, status=BALANCE_DEBTOR, balance__gt=0,
        ).select_related("student", "student__school_class", "term").order_by("-balance")
        total = balances.aggregate(total=Sum("balance"))["total"] or Decimal("0")
        payload["rows"] = [
            {
                "student": b.student.full_name if b.student_id else "",
                "admission_number": b.student.admission_number if b.student_id else "",
                "class_name": b.student.school_class.name if b.student_id and b.student.school_class_id else "",
                "term": b.term.name if b.term_id else "",
                "total_billed": _decimal_str(b.total_billed),
                "total_paid": _decimal_str(b.total_paid),
                "balance": _decimal_str(b.balance),
            }
            for b in balances
        ]
        payload["totals"] = {"balance": _decimal_str(total), "count": balances.count()}

    elif report_type == "expenses":
        entries = AccountingEntry.objects.filter(
            tenant=tenant,
            is_deleted=False,
            entry_type="expense",
            entry_date__gte=start,
            entry_date__lte=end,
        ).order_by("-entry_date")
        total = entries.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        payload["rows"] = [
            {
                "entry_date": str(e.entry_date),
                "description": e.description,
                "amount": _decimal_str(e.amount),
                "debit_account": e.debit_account,
                "credit_account": e.credit_account,
                "reference": e.reference,
            }
            for e in entries
        ]
        payload["totals"] = {"amount": _decimal_str(total), "count": entries.count()}

    else:
        payload["rows"] = []
        payload["totals"] = {}

    return payload


def build_parent_fee_statement(*, tenant, student) -> dict[str, Any]:
    from apps.finance.models import FeeDiscount

    invoices = Invoice.objects.filter(
        tenant=tenant, student=student, is_deleted=False,
    ).exclude(status="cancelled").order_by("-issue_date")
    payments = FeePayment.objects.filter(
        tenant=tenant, student=student, is_deleted=False,
        approval_status=APPROVAL_APPROVED, status="completed",
    ).select_related("fee_structure").order_by("-payment_date")
    balances = StudentFeeBalance.objects.filter(
        tenant=tenant, student=student, is_deleted=False,
    ).select_related("term").order_by("-term__start_date")
    discounts = FeeDiscount.objects.filter(
        tenant=tenant, student=student, is_deleted=False, status="approved",
    ).order_by("-created_at")

    total_billed = invoices.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")
    total_paid = payments.aggregate(total=Sum("amount_paid"))["total"] or Decimal("0")
    balance = total_billed - total_paid

    return {
        "student": {
            "id": str(student.id),
            "full_name": student.full_name,
            "admission_number": student.admission_number,
            "class_name": student.school_class.name if student.school_class_id else None,
        },
        "summary": {
            "total_billed": _decimal_str(total_billed),
            "total_paid": _decimal_str(total_paid),
            "balance": _decimal_str(balance),
        },
        "invoices": [
            {
                "invoice_number": inv.invoice_number,
                "issue_date": str(inv.issue_date),
                "due_date": str(inv.due_date),
                "total_amount": _decimal_str(inv.total_amount),
                "amount_paid": _decimal_str(inv.amount_paid),
                "status": inv.status,
            }
            for inv in invoices
        ],
        "payments": [
            {
                "payment_date": str(p.payment_date),
                "fee_item": p.fee_structure.name if p.fee_structure_id else "",
                "amount_paid": _decimal_str(p.amount_paid),
                "payment_method": p.payment_method,
                "receipt_number": p.receipt_number,
            }
            for p in payments
        ],
        "balances": [
            {
                "term": b.term.name if b.term_id else "",
                "total_billed": _decimal_str(b.total_billed),
                "total_paid": _decimal_str(b.total_paid),
                "balance": _decimal_str(b.balance),
                "status": b.status,
            }
            for b in balances
        ],
        "discounts": [
            {
                "discount_type": d.discount_type,
                "amount": _decimal_str(d.amount),
                "reason": d.reason,
                "status": d.status,
            }
            for d in discounts
        ],
    }