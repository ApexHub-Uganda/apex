"""Audit log services including PDF export."""
from __future__ import annotations

import io
from typing import Any

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.core.exports import escape_pdf_text


def _styles():
    styles = getSampleStyleSheet()
    if "Meta" not in styles.byName:
        styles.add(ParagraphStyle(name="Meta", fontSize=9, textColor=colors.grey))
    if "Section" not in styles.byName:
        styles.add(ParagraphStyle(
            name="Section",
            fontSize=12,
            spaceAfter=6,
            textColor=colors.HexColor("#0F766E"),
        ))
    if "BodySafe" not in styles.byName:
        styles.add(ParagraphStyle(name="BodySafe", fontSize=9, leading=12))
    if "Mono" not in styles.byName:
        styles.add(ParagraphStyle(name="Mono", fontName="Courier", fontSize=8, leading=10))
    return styles


def _p(text: Any, style) -> Paragraph:
    return Paragraph(escape_pdf_text(text), style)


def build_audit_log_pdf(log_data: dict[str, Any]) -> bytes:
    """Generate a detailed PDF for a single audit log entry."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    styles = _styles()
    story = []

    story.append(Paragraph("Apex Hub — Audit Log Report", styles["Title"]))
    story.append(_p(
        f"Generated {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        styles["Meta"],
    ))
    story.append(Spacer(1, 0.2 * inch))

    summary_rows = [
        [_p("Log ID", styles["BodySafe"]), _p(log_data.get("id", "—"), styles["BodySafe"])],
        [_p("Timestamp", styles["BodySafe"]), _p(log_data.get("timestamp", "—"), styles["BodySafe"])],
        [_p("User", styles["BodySafe"]), _p(log_data.get("user", "—"), styles["BodySafe"])],
        [_p("School / Scope", styles["BodySafe"]), _p(log_data.get("tenant_name") or "Platform", styles["BodySafe"])],
        [_p("Action", styles["BodySafe"]), _p(log_data.get("action", "—"), styles["BodySafe"])],
        [_p("Category", styles["BodySafe"]), _p(log_data.get("category_label", "—"), styles["BodySafe"])],
        [_p("Resource Type", styles["BodySafe"]), _p(log_data.get("resource_type", "—"), styles["BodySafe"])],
        [_p("Resource ID", styles["BodySafe"]), _p(log_data.get("resource_id", "—"), styles["BodySafe"])],
        [_p("Status", styles["BodySafe"]), _p(log_data.get("status_label", "—"), styles["BodySafe"])],
        [_p("IP Address", styles["BodySafe"]), _p(log_data.get("ip", "—"), styles["BodySafe"])],
    ]
    table = Table(summary_rows, colWidths=[1.6 * inch, 4.6 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Description", styles["Section"]))
    story.append(_p(log_data.get("description") or log_data.get("summary") or "—", styles["BodySafe"]))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Request Details", styles["Section"]))
    request_rows = [
        [_p("Method", styles["BodySafe"]), _p(log_data.get("request_method", "—"), styles["BodySafe"])],
        [_p("Path", styles["BodySafe"]), _p(log_data.get("request_path", "—"), styles["BodySafe"])],
        [_p("Status Code", styles["BodySafe"]), _p(str(log_data.get("status_code", "—")), styles["BodySafe"])],
        [_p("User Agent", styles["BodySafe"]), _p(log_data.get("user_agent", "—"), styles["BodySafe"])],
    ]
    req_table = Table(request_rows, colWidths=[1.6 * inch, 4.6 * inch])
    req_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(req_table)
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Changes", styles["Section"]))
    changes = log_data.get("changes") or {}
    # Preformatted avoids invalid XML tags (e.g. <pre>) that corrupt PDFs.
    import json

    if isinstance(changes, (dict, list)):
        changes_text = json.dumps(changes, indent=2, default=str)
    else:
        changes_text = str(changes) if changes else "—"
    story.append(Preformatted(changes_text[:8000], styles["Mono"]))

    doc.build(story)
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("PDF generation produced an invalid document.")
    return pdf_bytes


def build_audit_logs_list_pdf(logs: list[dict[str, Any]], filters: dict[str, Any] | None = None) -> bytes:
    """Generate a PDF table for filtered audit logs."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=0.4 * inch,
        rightMargin=0.4 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    styles = _styles()
    story = []

    story.append(Paragraph("Apex Hub — Audit Logs Export", styles["Title"]))
    story.append(_p(
        f"Generated {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        styles["Meta"],
    ))
    if filters:
        active = ", ".join(f"{k}={v}" for k, v in filters.items() if v)
        if active:
            story.append(_p(f"Filters: {active}", styles["Meta"]))
    story.append(Spacer(1, 0.15 * inch))

    headers = ["Timestamp", "User", "Action", "Category", "School", "Summary", "Status", "IP"]
    rows = [[_p(h, styles["BodySafe"]) for h in headers]]
    for log in logs:
        rows.append([
            _p(str(log.get("timestamp", "—"))[:19], styles["BodySafe"]),
            _p((log.get("user") or "—")[:28], styles["BodySafe"]),
            _p(log.get("action", "—"), styles["BodySafe"]),
            _p(log.get("category_label", "—"), styles["BodySafe"]),
            _p((log.get("tenant_name") or "Platform")[:20], styles["BodySafe"]),
            _p((log.get("summary") or "—")[:42], styles["BodySafe"]),
            _p(log.get("status_label", "—"), styles["BodySafe"]),
            _p(log.get("ip") or "—", styles["BodySafe"]),
        ])

    if len(rows) == 1:
        rows.append([_p("No audit logs matched the current filters.", styles["BodySafe"])] + [""] * 7)

    table = Table(
        rows,
        repeatRows=1,
        colWidths=[1.15 * inch, 1.1 * inch, 0.75 * inch, 0.85 * inch, 0.95 * inch, 2.0 * inch, 0.65 * inch, 0.85 * inch],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F766E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("PDF generation produced an invalid document.")
    return pdf_bytes
