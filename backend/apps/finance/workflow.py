"""Finance approval and balance workflows."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.finance.constants import (
    APPROVAL_APPROVED,
    APPROVAL_PENDING,
    APPROVAL_REVERSED,
    BALANCE_CLEARED,
    BALANCE_DEBTOR,
    DISCOUNT_APPROVED,
    DISCOUNT_PENDING,
    PERIOD_CLOSED,
    PERIOD_OPEN,
    REFUND_PENDING,
    REFUND_PROCESSED,
)
from apps.finance.models import (
    AccountingPeriod,
    FeeDiscount,
    FeePayment,
    Refund,
    StudentFeeBalance,
)
from apps.finance.scoping import user_can_approve_finance_transactions
from apps.tenants.role_permissions import user_is_school_admin


class FinanceWorkflowError(Exception):
    def __init__(self, message: str, *, code: str = "finance_workflow_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def generate_receipt_number(*, tenant) -> str:
    year = timezone.localdate().year
    prefix = f"RCP-{tenant.code}-{year}-"
    last = FeePayment.objects.filter(
        tenant=tenant, receipt_number__startswith=prefix,
    ).order_by("-receipt_number").values_list("receipt_number", flat=True).first()
    seq = (int(last.rsplit("-", 1)[-1]) + 1) if last else 1
    return f"{prefix}{seq:05d}"


def payment_requires_approval(user) -> bool:
    """Payments need bursar approval when recorder lacks transaction_approval write."""
    if user_is_school_admin(user):
        return False
    tenant = getattr(user, "tenant", None)
    if tenant is None:
        return True
    from apps.tenants.role_permissions import user_can_access_feature

    if user_can_access_feature(tenant, user, "transaction_approval", require_write=True):
        return False
    if user_can_access_feature(tenant, user, "payment_recording", require_write=True):
        return True
    return True


def assistant_bursar_requires_approval(user) -> bool:
    return payment_requires_approval(user)


@transaction.atomic
def sync_student_fee_balance(*, tenant, student, term) -> StudentFeeBalance:
    from apps.finance.models import Invoice

    billed = Invoice.objects.filter(
        tenant=tenant, student=student, is_deleted=False,
    ).exclude(status="cancelled").aggregate(
        total=Sum("total_amount"),
    )["total"] or Decimal("0")
    paid = FeePayment.objects.filter(
        tenant=tenant, student=student, is_deleted=False,
        approval_status=APPROVAL_APPROVED, status="completed",
    ).aggregate(total=Sum("amount_paid"))["total"] or Decimal("0")
    balance = billed - paid
    status = BALANCE_CLEARED if balance <= 0 else BALANCE_DEBTOR
    row, _ = StudentFeeBalance.objects.update_or_create(
        tenant=tenant,
        student=student,
        term=term,
        defaults={
            "total_billed": billed,
            "total_paid": paid,
            "balance": balance,
            "status": status,
        },
    )
    return row


@transaction.atomic
def approve_payment(*, payment: FeePayment, user) -> FeePayment:
    if not user_can_approve_finance_transactions(user, payment.tenant):
        raise FinanceWorkflowError("Transaction approval permission required.", code="forbidden_approve")
    if payment.approval_status != APPROVAL_PENDING:
        raise FinanceWorkflowError("Only pending payments can be approved.", code="invalid_status")
    now = timezone.now()
    payment.approval_status = APPROVAL_APPROVED
    payment.status = "completed"
    payment.approved_by = user
    payment.approved_at = now
    payment.updated_by = user
    if not payment.receipt_number:
        payment.receipt_number = generate_receipt_number(tenant=payment.tenant)
    payment.save(update_fields=[
        "approval_status", "status", "approved_by", "approved_at",
        "receipt_number", "updated_by", "updated_at",
    ])
    if payment.fee_structure_id and payment.fee_structure.term_id:
        sync_student_fee_balance(
            tenant=payment.tenant,
            student=payment.student,
            term=payment.fee_structure.term,
        )
    return payment


@transaction.atomic
def reverse_payment(*, payment: FeePayment, user, reason: str = "") -> FeePayment:
    if not user_can_approve_finance_transactions(user, payment.tenant):
        raise FinanceWorkflowError("Transaction approval permission required.", code="forbidden_reverse")
    if payment.approval_status not in {APPROVAL_APPROVED, APPROVAL_PENDING}:
        raise FinanceWorkflowError("This payment cannot be reversed.", code="invalid_status")
    payment.approval_status = APPROVAL_REVERSED
    payment.status = "failed"
    payment.reversal_reason = (reason or "").strip()
    payment.updated_by = user
    payment.save(update_fields=[
        "approval_status", "status", "reversal_reason", "updated_by", "updated_at",
    ])
    if payment.fee_structure_id and payment.fee_structure.term_id:
        sync_student_fee_balance(
            tenant=payment.tenant,
            student=payment.student,
            term=payment.fee_structure.term,
        )
    return payment


@transaction.atomic
def approve_discount(*, discount: FeeDiscount, user) -> FeeDiscount:
    if not user_can_approve_finance_transactions(user, discount.tenant):
        raise FinanceWorkflowError("Transaction approval permission required.", code="forbidden_approve")
    if discount.status != DISCOUNT_PENDING:
        raise FinanceWorkflowError("Only pending discounts can be approved.", code="invalid_status")
    discount.status = DISCOUNT_APPROVED
    discount.approved_by = user
    discount.approved_at = timezone.now()
    discount.updated_by = user
    discount.save(update_fields=["status", "approved_by", "approved_at", "updated_by", "updated_at"])
    return discount


@transaction.atomic
def approve_refund(*, refund: Refund, user) -> Refund:
    if not user_can_approve_finance_transactions(user, refund.tenant):
        raise FinanceWorkflowError("Transaction approval permission required.", code="forbidden_approve")
    if refund.status != REFUND_PENDING:
        raise FinanceWorkflowError("Only pending refunds can be approved.", code="invalid_status")
    refund.status = REFUND_PROCESSED
    refund.approved_by = user
    refund.approved_at = timezone.now()
    refund.updated_by = user
    refund.save(update_fields=["status", "approved_by", "approved_at", "updated_by", "updated_at"])
    payment = refund.fee_payment
    payment.status = "refunded"
    payment.updated_by = user
    payment.save(update_fields=["status", "updated_by", "updated_at"])
    return refund


@transaction.atomic
def close_accounting_period(*, period: AccountingPeriod, user) -> AccountingPeriod:
    if not user_can_approve_finance_transactions(user, period.tenant):
        raise FinanceWorkflowError("Transaction approval permission required.", code="forbidden_close")
    if period.status == PERIOD_CLOSED:
        raise FinanceWorkflowError("Period is already closed.", code="already_closed")
    period.status = PERIOD_CLOSED
    period.closed_by = user
    period.closed_at = timezone.now()
    period.updated_by = user
    period.save(update_fields=["status", "closed_by", "closed_at", "updated_by", "updated_at"])
    return period


@transaction.atomic
def reopen_accounting_period(*, period: AccountingPeriod, user) -> AccountingPeriod:
    if not user_can_approve_finance_transactions(user, period.tenant):
        raise FinanceWorkflowError("Transaction approval permission required.", code="forbidden_reopen")
    if period.status != PERIOD_CLOSED:
        raise FinanceWorkflowError("Only closed periods can be reopened.", code="invalid_status")
    period.status = PERIOD_OPEN
    period.closed_by = None
    period.closed_at = None
    period.updated_by = user
    period.save(update_fields=["status", "closed_by", "closed_at", "updated_by", "updated_at"])
    return period