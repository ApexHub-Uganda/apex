"""Finance approval and balance workflows (compat layer over services)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.finance.constants import (
    APPROVAL_APPROVED,
    APPROVAL_PENDING,
    APPROVAL_REVERSED,
    DISCOUNT_APPROVED,
    DISCOUNT_PENDING,
    DISCOUNT_REJECTED,
    PERIOD_CLOSED,
    PERIOD_OPEN,
    REFUND_PENDING,
    REFUND_PROCESSED,
    REFUND_REJECTED,
)
from apps.finance.models import AccountingPeriod, FeeDiscount, FeePayment, Refund
from apps.finance.scoping import user_can_approve_finance_transactions
from apps.finance.services.balances import sync_student_fee_balance
from apps.finance.services.finance_audit import log_finance_action
from apps.finance.services.numbering import generate_receipt_number
from apps.finance.services.payments_core import (
    finalize_approved_payment,
    payment_requires_approval,
    reverse_fee_payment,
)


class FinanceWorkflowError(Exception):
    def __init__(self, message: str, *, code: str = "finance_workflow_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def assistant_bursar_requires_approval(user) -> bool:
    return payment_requires_approval(user)


@transaction.atomic
def approve_payment(*, payment: FeePayment, user, request=None) -> FeePayment:
    try:
        return finalize_approved_payment(payment=payment, user=user, request=request)
    except Exception as exc:
        from apps.finance.services.payments_core import PaymentServiceError
        if isinstance(exc, PaymentServiceError):
            raise FinanceWorkflowError(exc.message, code=exc.code) from exc
        raise


@transaction.atomic
def reverse_payment(*, payment: FeePayment, user, reason: str = "", request=None) -> FeePayment:
    try:
        return reverse_fee_payment(payment=payment, user=user, reason=reason, request=request)
    except Exception as exc:
        from apps.finance.services.payments_core import PaymentServiceError
        if isinstance(exc, PaymentServiceError):
            raise FinanceWorkflowError(exc.message, code=exc.code) from exc
        raise


@transaction.atomic
def reject_payment(*, payment: FeePayment, user, reason: str = "", request=None) -> FeePayment:
    if not user_can_approve_finance_transactions(user, payment.tenant):
        raise FinanceWorkflowError("Transaction approval permission required.", code="forbidden_reject")
    if payment.approval_status != APPROVAL_PENDING:
        raise FinanceWorkflowError("Only pending payments can be rejected.", code="invalid_status")
    from apps.finance.constants import APPROVAL_REJECTED
    payment.approval_status = APPROVAL_REJECTED
    payment.status = "failed"
    payment.reversal_reason = (reason or "").strip()
    payment.updated_by = user
    payment.save()
    log_finance_action(
        tenant=payment.tenant, user=user, action="payment_rejected",
        resource_type="FeePayment", resource_id=str(payment.id),
        description=reason or "Payment rejected", request=request,
    )
    return payment


@transaction.atomic
def approve_discount(*, discount: FeeDiscount, user, request=None) -> FeeDiscount:
    if not user_can_approve_finance_transactions(user, discount.tenant):
        raise FinanceWorkflowError("Transaction approval permission required.", code="forbidden_approve")
    if discount.status != DISCOUNT_PENDING:
        raise FinanceWorkflowError("Only pending discounts can be approved.", code="invalid_status")
    discount.status = DISCOUNT_APPROVED
    discount.approved_by = user
    discount.approved_at = timezone.now()
    discount.updated_by = user
    discount.save(update_fields=["status", "approved_by", "approved_at", "updated_by", "updated_at"])

    term = discount.term or (discount.fee_structure.term if discount.fee_structure_id else None)
    if term is None and discount.invoice_id and getattr(discount.invoice, "term_id", None):
        term = discount.invoice.term
    if term:
        sync_student_fee_balance(tenant=discount.tenant, student=discount.student, term=term)

    log_finance_action(
        tenant=discount.tenant, user=user, action="discount_approved",
        resource_type="FeeDiscount", resource_id=str(discount.id),
        description="Discount approved", request=request,
    )
    return discount


@transaction.atomic
def reject_discount(*, discount: FeeDiscount, user, reason: str = "", request=None) -> FeeDiscount:
    if not user_can_approve_finance_transactions(user, discount.tenant):
        raise FinanceWorkflowError("Transaction approval permission required.", code="forbidden_reject")
    if discount.status != DISCOUNT_PENDING:
        raise FinanceWorkflowError("Only pending discounts can be rejected.", code="invalid_status")
    discount.status = DISCOUNT_REJECTED
    discount.updated_by = user
    discount.save(update_fields=["status", "updated_by", "updated_at"])
    log_finance_action(
        tenant=discount.tenant, user=user, action="discount_rejected",
        resource_type="FeeDiscount", resource_id=str(discount.id),
        description=reason or "Discount rejected", request=request,
    )
    return discount


@transaction.atomic
def approve_refund(*, refund: Refund, user, request=None) -> Refund:
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

    term = getattr(payment, "term", None) or (
        payment.fee_structure.term if payment.fee_structure_id else None
    )
    if term:
        sync_student_fee_balance(tenant=payment.tenant, student=payment.student, term=term)

    log_finance_action(
        tenant=refund.tenant, user=user, action="refund_processed",
        resource_type="Refund", resource_id=str(refund.id),
        description=f"Refund {refund.amount}", request=request,
    )
    return refund


@transaction.atomic
def reject_refund(*, refund: Refund, user, reason: str = "", request=None) -> Refund:
    if not user_can_approve_finance_transactions(user, refund.tenant):
        raise FinanceWorkflowError("Transaction approval permission required.", code="forbidden_reject")
    if refund.status != REFUND_PENDING:
        raise FinanceWorkflowError("Only pending refunds can be rejected.", code="invalid_status")
    refund.status = REFUND_REJECTED
    refund.updated_by = user
    refund.save(update_fields=["status", "updated_by", "updated_at"])
    log_finance_action(
        tenant=refund.tenant, user=user, action="refund_rejected",
        resource_type="Refund", resource_id=str(refund.id),
        description=reason or "Refund rejected", request=request,
    )
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


# re-export for older imports
__all__ = [
    "FinanceWorkflowError",
    "generate_receipt_number",
    "payment_requires_approval",
    "assistant_bursar_requires_approval",
    "sync_student_fee_balance",
    "approve_payment",
    "reverse_payment",
    "reject_payment",
    "approve_discount",
    "reject_discount",
    "approve_refund",
    "reject_refund",
    "close_accounting_period",
    "reopen_accounting_period",
]
