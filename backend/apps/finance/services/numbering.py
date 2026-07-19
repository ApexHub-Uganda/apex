"""Document numbering (invoices, receipts, payment refs) — tenant + year scoped."""
from __future__ import annotations

import uuid

from django.db import transaction
from django.utils import timezone

from apps.finance.models import FeePayment, Invoice


@transaction.atomic
def generate_invoice_number(*, tenant) -> str:
    year = timezone.localdate().year
    code = (getattr(tenant, "code", None) or "SCH").upper()
    prefix = f"INV-{code}-{year}-"
    last = (
        Invoice.objects.select_for_update()
        .filter(tenant=tenant, invoice_number__startswith=prefix)
        .order_by("-invoice_number")
        .values_list("invoice_number", flat=True)
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.rsplit("-", 1)[-1]) + 1
        except ValueError:
            seq = Invoice.objects.filter(tenant=tenant, invoice_number__startswith=prefix).count() + 1
    return f"{prefix}{seq:05d}"


@transaction.atomic
def generate_receipt_number(*, tenant) -> str:
    year = timezone.localdate().year
    code = (getattr(tenant, "code", None) or "SCH").upper()
    prefix = f"RCP-{code}-{year}-"
    last = (
        FeePayment.objects.select_for_update()
        .filter(tenant=tenant, receipt_number__startswith=prefix)
        .order_by("-receipt_number")
        .values_list("receipt_number", flat=True)
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.rsplit("-", 1)[-1]) + 1
        except ValueError:
            seq = FeePayment.objects.filter(tenant=tenant, receipt_number__startswith=prefix).count() + 1
    return f"{prefix}{seq:05d}"


def generate_payment_reference(*, tenant, channel: str = "MAN") -> str:
    code = (getattr(tenant, "code", None) or "SCH").upper()[:6]
    ch = (channel or "MAN")[:3].upper()
    stamp = timezone.now().strftime("%y%m%d")
    return f"PAY-{code}-{ch}-{stamp}-{uuid.uuid4().hex[:8].upper()}"
