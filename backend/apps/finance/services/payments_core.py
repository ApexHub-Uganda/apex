"""Payment recording, allocation to invoices, reverse/refund balance effects."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.finance.constants import APPROVAL_APPROVED, APPROVAL_PENDING, APPROVAL_REVERSED, REFUND_PROCESSED
from apps.finance.models import FeePayment, Invoice
from apps.finance.services.balances import sync_student_fee_balance
from apps.finance.services.finance_audit import log_finance_action
from apps.finance.services.numbering import generate_payment_reference, generate_receipt_number
from apps.finance.scoping import user_can_approve_finance_transactions
from apps.tenants.role_permissions import user_can_access_feature, user_is_school_admin


class PaymentServiceError(Exception):
    def __init__(self, message: str, *, code: str = "payment_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def payment_requires_approval(user) -> bool:
    if user_is_school_admin(user):
        return False
    tenant = getattr(user, "tenant", None)
    if tenant is None:
        return True
    if user_can_access_feature(tenant, user, "transaction_approval", require_write=True):
        return False
    if user_can_access_feature(tenant, user, "payment_recording", require_write=True):
        return True
    return True


@transaction.atomic
def allocate_payment_to_invoices(*, tenant, student, amount: Decimal, term=None) -> list[dict]:
    """FIFO allocate amount across open invoices (optionally term-scoped)."""
    remaining = Decimal(str(amount))
    qs = Invoice.objects.filter(
        tenant=tenant, student=student, is_deleted=False,
    ).exclude(status__in=["cancelled", "paid"]).order_by("due_date", "issue_date")
    if term is not None and any(f.name == "term" for f in Invoice._meta.fields):
        qs = qs.filter(term=term)

    allocations = []
    for inv in qs.select_for_update():
        if remaining <= 0:
            break
        outstanding = Decimal(str(inv.total_amount)) - Decimal(str(inv.amount_paid or 0))
        if outstanding <= 0:
            continue
        apply = min(remaining, outstanding)
        inv.amount_paid = Decimal(str(inv.amount_paid or 0)) + apply
        if inv.amount_paid >= inv.total_amount:
            inv.status = "paid"
        elif inv.amount_paid > 0:
            inv.status = "sent"
        inv.save(update_fields=["amount_paid", "status", "updated_at"])
        allocations.append({"invoice_id": str(inv.id), "amount": str(apply)})
        remaining -= apply
    return allocations


@transaction.atomic
def record_fee_payment(*, tenant, user, data: dict, request=None) -> FeePayment:
    """Create a fee payment and, when auto-approved, sync balances + allocate invoices."""
    from apps.finance.models import FeeStructure
    from apps.students.models import Student

    student = Student.objects.filter(tenant=tenant, pk=data["student"], is_deleted=False).first()
    if student is None:
        raise PaymentServiceError("Student not found.", code="student_not_found")
    fs = FeeStructure.objects.filter(tenant=tenant, pk=data["fee_structure"], is_deleted=False).first()
    if fs is None:
        raise PaymentServiceError("Fee structure not found.", code="fee_structure_not_found")

    amount = Decimal(str(data["amount_paid"]))
    if amount <= 0:
        raise PaymentServiceError("Amount must be positive.", code="invalid_amount")

    needs_approval = payment_requires_approval(user)
    approval_status = APPROVAL_PENDING if needs_approval else APPROVAL_APPROVED
    status_val = "pending" if needs_approval else "completed"
    receipt = ""
    if approval_status == APPROVAL_APPROVED:
        receipt = generate_receipt_number(tenant=tenant)

    kwargs = dict(
        tenant=tenant,
        student=student,
        fee_structure=fs,
        amount_paid=amount,
        payment_date=data.get("payment_date") or timezone.localdate(),
        payment_method=data.get("payment_method") or "cash",
        reference=data.get("reference") or "",
        receipt_number=receipt or data.get("receipt_number") or "",
        mpesa_transaction_id=data.get("mpesa_transaction_id") or "",
        mpesa_phone=data.get("mpesa_phone") or "",
        notes=data.get("notes") or "",
        received_by=user,
        approval_status=approval_status,
        status=status_val,
        created_by=user,
        updated_by=user,
    )
    if any(f.name == "term" for f in FeePayment._meta.fields):
        kwargs["term"] = fs.term
    if any(f.name == "payment_reference" for f in FeePayment._meta.fields):
        kwargs["payment_reference"] = generate_payment_reference(
            tenant=tenant, channel=kwargs["payment_method"],
        )
    if data.get("invoice") and any(f.name == "invoice" for f in FeePayment._meta.fields):
        inv = Invoice.objects.filter(tenant=tenant, pk=data["invoice"], student=student).first()
        if inv:
            kwargs["invoice"] = inv

    payment = FeePayment.objects.create(**kwargs)

    if approval_status == APPROVAL_APPROVED:
        allocate_payment_to_invoices(
            tenant=tenant, student=student, amount=amount, term=fs.term,
        )
        sync_student_fee_balance(tenant=tenant, student=student, term=fs.term)

    log_finance_action(
        tenant=tenant,
        user=user,
        action="payment_recorded",
        resource_type="FeePayment",
        resource_id=str(payment.id),
        description=f"Payment {amount} for {student.admission_number}",
        changes={
            "amount": str(amount),
            "approval_status": approval_status,
            "receipt_number": payment.receipt_number,
        },
        request=request,
    )
    return payment


@transaction.atomic
def finalize_approved_payment(*, payment: FeePayment, user, request=None) -> FeePayment:
    if not user_can_approve_finance_transactions(user, payment.tenant):
        raise PaymentServiceError("Transaction approval permission required.", code="forbidden_approve")
    if payment.approval_status != APPROVAL_PENDING:
        raise PaymentServiceError("Only pending payments can be approved.", code="invalid_status")

    payment.approval_status = APPROVAL_APPROVED
    payment.status = "completed"
    payment.approved_by = user
    payment.approved_at = timezone.now()
    payment.updated_by = user
    if not payment.receipt_number:
        payment.receipt_number = generate_receipt_number(tenant=payment.tenant)
    payment.save()

    term = getattr(payment, "term", None) or (
        payment.fee_structure.term if payment.fee_structure_id else None
    )
    if term:
        allocate_payment_to_invoices(
            tenant=payment.tenant,
            student=payment.student,
            amount=payment.amount_paid,
            term=term,
        )
        sync_student_fee_balance(tenant=payment.tenant, student=payment.student, term=term)

    log_finance_action(
        tenant=payment.tenant,
        user=user,
        action="payment_approved",
        resource_type="FeePayment",
        resource_id=str(payment.id),
        description=f"Approved payment {payment.receipt_number}",
        request=request,
    )
    return payment


@transaction.atomic
def reverse_fee_payment(*, payment: FeePayment, user, reason: str = "", request=None) -> FeePayment:
    if not user_can_approve_finance_transactions(user, payment.tenant):
        raise PaymentServiceError("Transaction approval permission required.", code="forbidden_reverse")
    if payment.approval_status not in {APPROVAL_APPROVED, APPROVAL_PENDING}:
        raise PaymentServiceError("This payment cannot be reversed.", code="invalid_status")

    was_approved = payment.approval_status == APPROVAL_APPROVED
    amount = Decimal(str(payment.amount_paid))
    payment.approval_status = APPROVAL_REVERSED
    payment.status = "failed"
    payment.reversal_reason = (reason or "").strip()
    payment.updated_by = user
    payment.save()

    term = getattr(payment, "term", None) or (
        payment.fee_structure.term if payment.fee_structure_id else None
    )
    if was_approved and term:
        # Reduce invoice allocations proportionally / FIFO reverse
        inv_qs = Invoice.objects.filter(
            tenant=payment.tenant, student=payment.student, is_deleted=False,
        ).exclude(status="cancelled").order_by("-due_date")
        if any(f.name == "term" for f in Invoice._meta.fields):
            inv_qs = inv_qs.filter(term=term)
        remaining = amount
        for inv in inv_qs.select_for_update():
            if remaining <= 0:
                break
            paid = Decimal(str(inv.amount_paid or 0))
            if paid <= 0:
                continue
            take = min(paid, remaining)
            inv.amount_paid = paid - take
            if inv.amount_paid <= 0:
                inv.status = "sent"
            inv.save(update_fields=["amount_paid", "status", "updated_at"])
            remaining -= take
        sync_student_fee_balance(tenant=payment.tenant, student=payment.student, term=term)

    log_finance_action(
        tenant=payment.tenant,
        user=user,
        action="payment_reversed",
        resource_type="FeePayment",
        resource_id=str(payment.id),
        description=reason or "Payment reversed",
        request=request,
    )
    return payment
