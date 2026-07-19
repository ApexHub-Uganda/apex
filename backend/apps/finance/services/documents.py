"""Branded PDF documents: receipts, invoices, student fee statements."""
from __future__ import annotations

from typing import Any

from reportlab.platypus import Spacer, Table

from apps.core.pdf_template import (
    branded_table_style,
    build_branded_pdf,
    get_pdf_styles,
    p,
)


def build_receipt_pdf(*, tenant, payment, request=None) -> bytes:
    student = payment.student
    meta = {
        "doc": "receipt",
        "receipt": payment.receipt_number or "",
        "student": getattr(student, "admission_number", "") if student else "",
        "amount": str(payment.amount_paid),
    }

    def story(ctx, styles):
        rows = [
            [p("Field", styles["Label"]), p("Value", styles["Label"])],
            [p("Receipt No.", styles["Body"]), p(payment.receipt_number or "—", styles["Body"])],
            [p("Date", styles["Body"]), p(str(payment.payment_date), styles["Body"])],
            [p("Student", styles["Body"]), p(student.full_name if student else "—", styles["Body"])],
            [p("Admission No.", styles["Body"]), p(getattr(student, "admission_number", "—") if student else "—", styles["Body"])],
            [p("Class", styles["Body"]), p(
                student.school_class.name if student and student.school_class_id else "—", styles["Body"],
            )],
            [p("Fee item", styles["Body"]), p(
                payment.fee_structure.name if payment.fee_structure_id else "—", styles["Body"],
            )],
            [p("Amount paid", styles["Body"]), p(str(payment.amount_paid), styles["Body"])],
            [p("Method", styles["Body"]), p(payment.payment_method, styles["Body"])],
            [p("Reference", styles["Body"]), p(payment.reference or "—", styles["Body"])],
            [p("M-Pesa Txn", styles["Body"]), p(payment.mpesa_transaction_id or "—", styles["Body"])],
            [p("Received by", styles["Body"]), p(
                payment.received_by.full_name if payment.received_by_id else "—", styles["Body"],
            )],
            [p("Status", styles["Body"]), p(f"{payment.status} / {payment.approval_status}", styles["Body"])],
        ]
        table = Table(rows, colWidths=[ctx.content_width * 0.35, ctx.content_width * 0.65])
        table.setStyle(branded_table_style(ctx, header=True))
        return [
            p("This is an official fee receipt. Keep for your records.", styles["Meta"]),
            Spacer(1, 8),
            table,
        ]

    return build_branded_pdf(
        tenant=tenant,
        document_type="fee_receipt",
        document_meta=meta,
        title="Official Fee Receipt",
        subtitle=payment.receipt_number or "",
        build_story=story,
        request=request,
    )


def build_invoice_pdf(*, tenant, invoice, request=None) -> bytes:
    student = invoice.student
    lines = invoice.line_items or []
    meta = {
        "doc": "invoice",
        "invoice": invoice.invoice_number,
        "student": getattr(student, "admission_number", "") if student else "",
        "total": str(invoice.total_amount),
    }

    def story(ctx, styles):
        body = [
            p(f"Invoice {invoice.invoice_number}", styles["Heading"]),
            p(f"Issue: {invoice.issue_date} · Due: {invoice.due_date} · Status: {invoice.status}", styles["Meta"]),
            Spacer(1, 6),
            p(f"Bill to: {student.full_name if student else '—'} ({getattr(student, 'admission_number', '')})", styles["Body"]),
            Spacer(1, 8),
        ]
        rows = [[p("Item", styles["Label"]), p("Amount", styles["Label"])]]
        if lines:
            for line in lines:
                name = line.get("name") if isinstance(line, dict) else str(line)
                amt = line.get("amount", "") if isinstance(line, dict) else ""
                rows.append([p(name, styles["Body"]), p(str(amt), styles["Body"])])
        else:
            rows.append([p("Fee charge", styles["Body"]), p(str(invoice.total_amount), styles["Body"])])
        rows.append([p("Total", styles["Label"]), p(str(invoice.total_amount), styles["Label"])])
        rows.append([p("Paid", styles["Body"]), p(str(invoice.amount_paid or 0), styles["Body"])])
        bal = (invoice.total_amount or 0) - (invoice.amount_paid or 0)
        rows.append([p("Balance", styles["Label"]), p(str(bal), styles["Label"])])
        table = Table(rows, colWidths=[ctx.content_width * 0.7, ctx.content_width * 0.3])
        table.setStyle(branded_table_style(ctx, header=True))
        body.append(table)
        if invoice.notes:
            body.append(Spacer(1, 8))
            body.append(p(invoice.notes, styles["Meta"]))
        return body

    return build_branded_pdf(
        tenant=tenant,
        document_type="fee_invoice",
        document_meta=meta,
        title="Fee Invoice",
        subtitle=invoice.invoice_number,
        build_story=story,
        request=request,
    )


def build_student_statement_pdf(*, tenant, student, statement: dict[str, Any], request=None) -> bytes:
    meta = {
        "doc": "statement",
        "student": student.admission_number,
        "balance": (statement.get("summary") or {}).get("balance", ""),
    }

    def story(ctx, styles):
        summary = statement.get("summary") or {}
        items = [
            p(f"{student.full_name} · {student.admission_number}", styles["Heading"]),
            p(
                f"Billed: {summary.get('total_billed')} · Paid: {summary.get('total_paid')} · "
                f"Balance: {summary.get('balance')}",
                styles["Body"],
            ),
            Spacer(1, 8),
            p("Recent payments", styles["Heading"]),
        ]
        pay_rows = [[p("Date", styles["Label"]), p("Item", styles["Label"]), p("Amount", styles["Label"]), p("Receipt", styles["Label"])]]
        for pay in (statement.get("payments") or [])[:40]:
            pay_rows.append([
                p(pay.get("payment_date", ""), styles["Small"]),
                p(pay.get("fee_item", ""), styles["Small"]),
                p(pay.get("amount_paid", ""), styles["Small"]),
                p(pay.get("receipt_number", ""), styles["Small"]),
            ])
        if len(pay_rows) == 1:
            pay_rows.append([p("—", styles["Small"]), p("No payments", styles["Small"]), p("", styles["Small"]), p("", styles["Small"])])
        t = Table(pay_rows, colWidths=[ctx.content_width * 0.2] * 4)
        t.setStyle(branded_table_style(ctx, header=True))
        items.append(t)
        return items

    return build_branded_pdf(
        tenant=tenant,
        document_type="fee_statement",
        document_meta=meta,
        title="Student Fee Statement",
        subtitle=student.full_name,
        build_story=story,
        request=request,
    )
