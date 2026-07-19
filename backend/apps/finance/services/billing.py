"""Billing engine: fee structures -> invoices + line items -> student term balances."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.academics.models import Class, Term
from apps.finance.models import FeeStructure, Invoice
from apps.finance.services.balances import sync_student_fee_balance
from apps.finance.services.finance_audit import log_finance_action
from apps.finance.services.numbering import generate_invoice_number
from apps.students.models import Student


class BillingError(Exception):
    def __init__(self, message: str, *, code: str = "billing_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def _line_from_structure(fs: FeeStructure) -> dict[str, Any]:
    return {
        "fee_structure_id": str(fs.id),
        "name": fs.name,
        "fee_category": fs.fee_category,
        "amount": str(fs.amount),
        "currency": fs.currency or "UGX",
        "is_mandatory": fs.is_mandatory,
    }


@transaction.atomic
def bill_student_for_term(
    *,
    tenant,
    student: Student,
    term: Term,
    actor=None,
    due_date=None,
    notes: str = "",
    only_mandatory: bool = True,
    request=None,
    skip_if_exists: bool = True,
) -> Invoice | None:
    if student.tenant_id != tenant.id:
        raise BillingError("Student does not belong to this school.", code="tenant_mismatch")
    if term.tenant_id != tenant.id:
        raise BillingError("Term does not belong to this school.", code="tenant_mismatch")
    if not student.school_class_id:
        raise BillingError("Student has no class assigned.", code="no_class")

    inv_qs = Invoice.objects.filter(
        tenant=tenant, student=student, is_deleted=False,
    ).exclude(status="cancelled")
    if any(f.name == "term" for f in Invoice._meta.fields):
        inv_qs = inv_qs.filter(term=term)
    if skip_if_exists:
        existing = inv_qs.first()
        if existing:
            return existing

    structures = FeeStructure.objects.filter(
        tenant=tenant,
        school_class_id=student.school_class_id,
        term=term,
        is_deleted=False,
    )
    if only_mandatory:
        structures = structures.filter(is_mandatory=True)
    structures = list(structures)
    if not structures:
        raise BillingError(
            f"No fee structures for class / {term.name}.",
            code="no_structures",
        )

    lines = [_line_from_structure(fs) for fs in structures]
    total = sum(Decimal(str(fs.amount)) for fs in structures)
    issue = timezone.localdate()
    due = due_date or max(
        (fs.due_date for fs in structures if fs.due_date),
        default=issue + timedelta(days=30),
    )

    create_kwargs = dict(
        tenant=tenant,
        student=student,
        invoice_number=generate_invoice_number(tenant=tenant),
        issue_date=issue,
        due_date=due,
        total_amount=total,
        amount_paid=Decimal("0"),
        status="sent",
        line_items=lines,
        notes=notes or f"Term billing — {term.name}",
        created_by=actor,
        updated_by=actor,
    )
    if any(f.name == "term" for f in Invoice._meta.fields):
        create_kwargs["term"] = term

    inv = Invoice.objects.create(**create_kwargs)
    sync_student_fee_balance(tenant=tenant, student=student, term=term)
    log_finance_action(
        tenant=tenant,
        user=actor,
        action="invoice_generated",
        resource_type="Invoice",
        resource_id=str(inv.id),
        description=f"Billed {student.admission_number} for {term.name}: {total}",
        changes={"invoice_number": inv.invoice_number, "total": str(total), "lines": len(lines)},
        request=request,
    )
    return inv


@transaction.atomic
def bill_class_for_term(
    *,
    tenant,
    school_class: Class,
    term: Term,
    actor=None,
    due_date=None,
    only_mandatory: bool = True,
    student_ids: list | None = None,
    request=None,
) -> dict[str, Any]:
    if school_class.tenant_id != tenant.id or term.tenant_id != tenant.id:
        raise BillingError("Class/term tenant mismatch.", code="tenant_mismatch")

    students = Student.objects.filter(
        tenant=tenant,
        school_class=school_class,
        is_deleted=False,
        status="active",
    )
    if student_ids:
        students = students.filter(pk__in=student_ids)

    created, skipped, errors = [], [], []
    for student in students:
        try:
            before_qs = Invoice.objects.filter(
                tenant=tenant, student=student, is_deleted=False,
            ).exclude(status="cancelled")
            if any(f.name == "term" for f in Invoice._meta.fields):
                before_qs = before_qs.filter(term=term)
            before = before_qs.exists()
            inv = bill_student_for_term(
                tenant=tenant,
                student=student,
                term=term,
                actor=actor,
                due_date=due_date,
                only_mandatory=only_mandatory,
                request=request,
                skip_if_exists=True,
            )
            if before:
                skipped.append(str(student.id))
            elif inv:
                created.append({
                    "student_id": str(student.id),
                    "invoice_id": str(inv.id),
                    "number": inv.invoice_number,
                })
        except BillingError as exc:
            errors.append({"student_id": str(student.id), "error": exc.message, "code": exc.code})

    log_finance_action(
        tenant=tenant,
        user=actor,
        action="bulk_billing",
        resource_type="Class",
        resource_id=str(school_class.id),
        description=(
            f"Billed class {school_class.name} / {term.name}: "
            f"{len(created)} created, {len(skipped)} skipped"
        ),
        changes={"created": len(created), "skipped": len(skipped), "errors": len(errors)},
        request=request,
    )
    return {
        "created_count": len(created),
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "class_id": str(school_class.id),
        "term_id": str(term.id),
    }
