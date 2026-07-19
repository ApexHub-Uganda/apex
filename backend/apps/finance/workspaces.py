"""Finance role workspace summaries."""
from __future__ import annotations

from typing import Any

from django.db.models import Sum
from django.utils import timezone

from apps.core.constants import UserRole, normalize_role
from apps.finance.scoping import user_has_school_wide_finance_access
from apps.finance.constants import APPROVAL_PENDING, BALANCE_DEBTOR, DISCOUNT_PENDING, REFUND_PENDING
from apps.finance.models import (
    AccountingEntry,
    FeeDiscount,
    FeePayment,
    Invoice,
    Refund,
    StudentFeeBalance,
)
from apps.tenants.role_permissions import get_user_feature_permissions, user_is_school_admin


def _enabled(perms: dict, key: str) -> bool:
    return bool(perms.get(key, {}).get("can_read"))


def build_finance_workspace(*, tenant, user) -> dict[str, Any]:
    role = normalize_role(getattr(user, "role", ""))
    perms = get_user_feature_permissions(tenant, user)
    is_school_wide = user_has_school_wide_finance_access(user, tenant)

    payload: dict[str, Any] = {
        "role": role,
        "is_school_wide": is_school_wide,
        "features": {
            key: perms.get(key, {"can_read": False, "can_write": False})
            for key in (
                "bursar_workspace", "assistant_bursar_workspace",
                "payment_recording", "invoice_generation", "student_billing",
                "fee_structures", "expenses", "financial_reports", "transaction_approval",
                "debtor_management", "finance_analytics",
            )
        },
        "counts": {},
        "queues": {},
        "quick_links": [],
    }

    if not is_school_wide:
        return payload

    if _enabled(perms, "payment_recording"):
        payload["counts"]["payments_today"] = FeePayment.objects.filter(
            tenant=tenant, is_deleted=False, payment_date=timezone.localdate(),
        ).count()

    if _enabled(perms, "student_billing") or _enabled(perms, "debtor_management"):
        payload["counts"]["outstanding_debtors"] = StudentFeeBalance.objects.filter(
            tenant=tenant, is_deleted=False, status=BALANCE_DEBTOR, balance__gt=0,
        ).count()

    if _enabled(perms, "transaction_approval"):
        pending_payments = FeePayment.objects.filter(
            tenant=tenant, is_deleted=False, approval_status=APPROVAL_PENDING,
        ).select_related("student")[:20]
        payload["counts"]["pending_approval"] = FeePayment.objects.filter(
            tenant=tenant, is_deleted=False, approval_status=APPROVAL_PENDING,
        ).count()
        payload["queues"]["pending_payments"] = [
            {
                "id": str(p.id),
                "student": p.student.full_name if p.student_id else "",
                "amount": str(p.amount_paid),
                "date": str(p.payment_date),
            }
            for p in pending_payments
        ]
        payload["counts"]["pending_discounts"] = FeeDiscount.objects.filter(
            tenant=tenant, is_deleted=False, status=DISCOUNT_PENDING,
        ).count()
        payload["counts"]["pending_refunds"] = Refund.objects.filter(
            tenant=tenant, is_deleted=False, status=REFUND_PENDING,
        ).count()

    if _enabled(perms, "invoice_generation"):
        payload["counts"]["open_invoices"] = Invoice.objects.filter(
            tenant=tenant, is_deleted=False, status__in=["draft", "sent", "overdue"],
        ).count()

    if _enabled(perms, "expenses"):
        payload["counts"]["expense_entries"] = AccountingEntry.objects.filter(
            tenant=tenant, is_deleted=False, entry_type="expense",
        ).count()

    if role == UserRole.ASSISTANT_BURSAR and _enabled(perms, "assistant_bursar_workspace"):
        payload["quick_links"] = [
            {"label": "Record Payment", "path": "/school-admin/finance/payments", "feature_key": "payment_recording"},
            {"label": "Create Invoice", "path": "/school-admin/finance/invoices", "feature_key": "invoice_generation"},
            {"label": "Student Billing", "path": "/school-admin/finance", "feature_key": "student_billing"},
            {"label": "Debtors", "path": "/school-admin/finance/debtors", "feature_key": "debtor_management"},
        ]
    elif role == UserRole.BURSAR and _enabled(perms, "bursar_workspace"):
        payload["quick_links"] = [
            {"label": "Approval Queue", "path": "/school-admin/finance/approval", "feature_key": "transaction_approval"},
            {"label": "Fee Structures", "path": "/school-admin/finance/structures", "feature_key": "fee_structures"},
            {"label": "Financial Reports", "path": "/school-admin/finance/reports", "feature_key": "financial_reports"},
            {"label": "Results fee gate", "path": "/school-admin/finance/results-access", "feature_key": "bursar_workspace"},
            {"label": "Accounting Periods", "path": "/school-admin/finance/periods", "feature_key": "accounting_periods"},
        ]

    if role == UserRole.ASSISTANT_BURSAR and _enabled(perms, "assistant_bursar_workspace"):
        payload["quick_links"].append(
            {"label": "Results fee gate", "path": "/school-admin/finance/results-access", "feature_key": "assistant_bursar_workspace"},
        )

    if _enabled(perms, "finance_analytics"):
        collected = FeePayment.objects.filter(
            tenant=tenant, is_deleted=False, status="completed",
        ).aggregate(total=Sum("amount_paid"))["total"]
        payload["counts"]["total_collected"] = str(collected or 0)

    # Actionable debtor preview for bursary workspaces
    if is_school_wide and (
        _enabled(perms, "debtor_management") or _enabled(perms, "bursar_workspace")
    ):
        top_debtors = StudentFeeBalance.objects.filter(
            tenant=tenant, is_deleted=False, status=BALANCE_DEBTOR, balance__gt=0,
        ).select_related("student", "term").order_by("-balance")[:8]
        payload["queues"]["top_debtors"] = [
            {
                "id": str(b.id),
                "student": b.student.full_name if b.student_id else "",
                "admission_number": b.student.admission_number if b.student_id else "",
                "term": b.term.name if b.term_id else "",
                "balance": str(b.balance),
            }
            for b in top_debtors
        ]

    return payload