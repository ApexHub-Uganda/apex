"""Audit log services including PDF export."""
from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Meta", fontSize=9, textColor=colors.grey))
    styles.add(ParagraphStyle(name="Section", fontSize=12, spaceAfter=6, textColor=colors.HexColor("#0F766E")))
    return styles


def _safe_text(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, default=str)
    return str(value)


def build_audit_log_pdf(log_data: dict[str, Any]) -> bytes:
    """Generate a detailed PDF for a single audit log entry."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.75 * inch, rightMargin=0.75 * inch)
    styles = _styles()
    story = []

    story.append(Paragraph("Apex Hub — Audit Log Report", styles["Title"]))
    story.append(Paragraph(f"Generated {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}", styles["Meta"]))
    story.append(Spacer(1, 0.2 * inch))

    summary_rows = [
        ["Log ID", log_data.get("id", "—")],
        ["Timestamp", log_data.get("timestamp", "—")],
        ["User", log_data.get("user", "—")],
        ["School / Scope", log_data.get("tenant_name") or "Platform"],
        ["Action", log_data.get("action", "—")],
        ["Category", log_data.get("category_label", "—")],
        ["Resource Type", log_data.get("resource_type", "—")],
        ["Resource ID", log_data.get("resource_id", "—")],
        ["Status", log_data.get("status_label", "—")],
        ["IP Address", log_data.get("ip", "—")],
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
    story.append(Paragraph(_safe_text(log_data.get("description") or log_data.get("summary")), styles["Normal"]))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Request Details", styles["Section"]))
    request_rows = [
        ["Method", log_data.get("request_method", "—")],
        ["Path", log_data.get("request_path", "—")],
        ["Status Code", str(log_data.get("status_code", "—"))],
        ["User Agent", log_data.get("user_agent", "—")],
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
    story.append(Paragraph(f"<pre>{_safe_text(changes)}</pre>", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def build_audit_logs_list_pdf(logs: list[dict[str, Any]], filters: dict[str, Any] | None = None) -> bytes:
    """Generate a PDF table for filtered audit logs."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5 * inch, rightMargin=0.5 * inch)
    styles = _styles()
    story = []

    story.append(Paragraph("Apex Hub — Audit Logs Export", styles["Title"]))
    story.append(Paragraph(f"Generated {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}", styles["Meta"]))
    if filters:
        active = ", ".join(f"{k}={v}" for k, v in filters.items() if v)
        if active:
            story.append(Paragraph(f"Filters: {active}", styles["Meta"]))
    story.append(Spacer(1, 0.15 * inch))

    headers = ["Timestamp", "User", "Action", "Category", "School", "Summary", "Status", "IP"]
    rows = [headers]
    for log in logs:
        rows.append([
            log.get("timestamp", "—"),
            (log.get("user") or "—")[:28],
            log.get("action", "—"),
            log.get("category_label", "—"),
            (log.get("tenant_name") or "Platform")[:20],
            (log.get("summary") or "—")[:42],
            log.get("status_label", "—"),
            log.get("ip") or "—",
        ])

    table = Table(rows, repeatRows=1, colWidths=[1.0 * inch, 0.95 * inch, 0.65 * inch, 0.75 * inch, 0.85 * inch, 1.55 * inch, 0.55 * inch, 0.7 * inch])
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
    return buffer.getvalue()