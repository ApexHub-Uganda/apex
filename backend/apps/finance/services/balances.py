"""Term-scoped student fee balance recalculation (debtors + results clearance)."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum

from apps.finance.constants import (
    APPROVAL_APPROVED,
    BALANCE_CLEARED,
    BALANCE_CREDIT,
    BALANCE_DEBTOR,
    DISCOUNT_APPROVED,
    REFUND_PROCESSED,
)
from apps.finance.models import FeeDiscount, FeePayment, Invoice, Refund, StudentFeeBalance


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


@transaction.atomic
def sync_student_fee_balance(*, tenant, student, term) -> StudentFeeBalance:
    """
    Recalculate one student+term balance.

    Billed  = invoices for this term (non-cancelled) minus approved discounts
    Paid    = approved completed payments for this term minus processed refunds
    """
    inv_qs = Invoice.objects.filter(
        tenant=tenant,
        student=student,
        is_deleted=False,
    ).exclude(status="cancelled")

    # Prefer term FK when present
    if any(f.name == "term" for f in Invoice._meta.fields):
        inv_qs = inv_qs.filter(term=term)

    billed = inv_qs.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

    disc_filter = Q(fee_structure__term=term)
    if any(f.name == "term" for f in FeeDiscount._meta.fields):
        disc_filter = disc_filter | Q(term=term)
    if any(f.name == "term" for f in Invoice._meta.fields):
        disc_filter = disc_filter | Q(invoice__term=term)

    disc_qs = FeeDiscount.objects.filter(
        tenant=tenant,
        student=student,
        is_deleted=False,
        status=DISCOUNT_APPROVED,
    ).filter(disc_filter)

    discount_total = Decimal("0")
    for d in disc_qs.distinct():
        if d.amount:
            discount_total += _d(d.amount)
        elif d.percent is not None and d.fee_structure_id:
            discount_total += (
                _d(d.fee_structure.amount) * _d(d.percent) / Decimal("100")
            ).quantize(Decimal("0.01"))

    effective_billed = max(Decimal("0"), _d(billed) - discount_total)

    pay_filter = Q(fee_structure__term=term)
    if any(f.name == "term" for f in FeePayment._meta.fields):
        pay_filter = pay_filter | Q(term=term)

    pay_qs = FeePayment.objects.filter(
        tenant=tenant,
        student=student,
        is_deleted=False,
        approval_status=APPROVAL_APPROVED,
        status="completed",
    ).filter(pay_filter)

    paid = pay_qs.aggregate(total=Sum("amount_paid"))["total"] or Decimal("0")

    refund_total = (
        Refund.objects.filter(
            tenant=tenant,
            is_deleted=False,
            status=REFUND_PROCESSED,
            fee_payment__in=pay_qs,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )

    net_paid = max(Decimal("0"), _d(paid) - _d(refund_total))
    balance = effective_billed - net_paid

    if balance < 0:
        status = BALANCE_CREDIT
    elif balance == 0:
        status = BALANCE_CLEARED
    else:
        status = BALANCE_DEBTOR

    row, _ = StudentFeeBalance.objects.update_or_create(
        tenant=tenant,
        student=student,
        term=term,
        defaults={
            "total_billed": effective_billed,
            "total_paid": net_paid,
            "balance": balance,
            "status": status,
            "is_deleted": False,
        },
    )
    return row


def recalculate_student_balances(*, tenant, student) -> list:
    from apps.academics.models import Term

    term_ids = set()
    inv = Invoice.objects.filter(tenant=tenant, student=student, is_deleted=False).exclude(status="cancelled")
    if any(f.name == "term" for f in Invoice._meta.fields):
        term_ids |= set(inv.exclude(term_id=None).values_list("term_id", flat=True))
    term_ids |= set(
        FeePayment.objects.filter(tenant=tenant, student=student, is_deleted=False)
        .filter(fee_structure__isnull=False)
        .values_list("fee_structure__term_id", flat=True)
    )
    rows = []
    for term in Term.objects.filter(tenant=tenant, pk__in=[t for t in term_ids if t]):
        rows.append(sync_student_fee_balance(tenant=tenant, student=student, term=term))
    return rows
