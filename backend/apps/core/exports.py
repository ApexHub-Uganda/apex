"""Shared authenticated export helpers (CSV / PDF)."""
from __future__ import annotations

import csv
import io
from typing import Any, Iterable, Sequence
from xml.sax.saxutils import escape as xml_escape

from django.http import HttpResponse
from django.utils import timezone


def escape_pdf_text(value: Any) -> str:
    """Escape text for ReportLab Paragraph (XML-like markup)."""
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        import json

        text = json.dumps(value, indent=2, default=str)
    else:
        text = str(value)
    # ReportLab Paragraph treats content as a tiny XML subset.
    return xml_escape(text, {"'": "&apos;", '"': "&quot;"})


def csv_attachment_response(
    *,
    rows: Sequence[dict[str, Any]],
    filename: str,
    empty_message: str = "No data",
) -> HttpResponse:
    """Build a CSV download response from list-of-dict rows."""
    if not rows:
        return HttpResponse(empty_message, content_type="text/plain; charset=utf-8", status=404)

    buffer = io.StringIO()
    # UTF-8 BOM helps Excel open the file correctly.
    buffer.write("\ufeff")
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _csv_cell(row.get(key)) for key in fieldnames})

    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    safe_name = filename if filename.endswith(".csv") else f"{filename}.csv"
    response["Content-Disposition"] = f'attachment; filename="{safe_name}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


def pdf_attachment_response(*, pdf_bytes: bytes, filename: str) -> HttpResponse:
    """Build a binary PDF download response with correct headers."""
    safe_name = filename if filename.lower().endswith(".pdf") else f"{filename}.pdf"
    response = HttpResponse(bytes(pdf_bytes), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{safe_name}"'
    response["Content-Length"] = str(len(pdf_bytes))
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "no-store"
    return response


def export_filename(prefix: str, *, ext: str = "csv") -> str:
    stamp = timezone.now().strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{stamp}.{ext}"


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        import json

        return json.dumps(value, default=str)
    return str(value)


def rows_from_summary(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten a summary dict into two-column CSV rows."""
    return [{"metric": key, "value": value} for key, value in (summary or {}).items()]
