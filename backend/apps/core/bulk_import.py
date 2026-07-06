"""CSV bulk import utilities — template generation, parsing, and validation."""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from apps.core.email_validation import validate_deliverable_email

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[\d\s\-()]{7,20}$")


@dataclass
class ImportColumn:
    key: str
    label: str
    required: bool = False
    help_text: str = ""
    choices: list[str] | None = None
    field_type: str = "string"  # string, date, decimal, integer, boolean, email, phone


@dataclass
class ImportSpec:
    entity_name: str
    columns: list[ImportColumn]
    description: str = ""

    @property
    def required_keys(self) -> set[str]:
        return {c.key for c in self.columns if c.required}

    @property
    def all_keys(self) -> set[str]:
        return {c.key for c in self.columns}

    def column_map(self) -> dict[str, ImportColumn]:
        return {c.key: c for c in self.columns}


def normalize_header(header: str) -> str:
    return header.strip().lower().replace(" ", "_").replace("-", "_")


def generate_csv_template(spec: ImportSpec) -> bytes:
    """Build a UTF-8 CSV template with header row and one example row."""
    output = io.StringIO()
    writer = csv.writer(output)
    headers = [col.label for col in spec.columns]
    writer.writerow(headers)
    hints = []
    for col in spec.columns:
        hint = col.help_text or ""
        if col.choices:
            hint = f"{hint} Options: {', '.join(col.choices)}".strip()
        if col.required:
            hint = f"{hint} (required)".strip()
        hints.append(hint)
    writer.writerow(hints)
    return output.getvalue().encode("utf-8-sig")


def parse_upload(file_obj) -> tuple[list[str], list[dict[str, str]]]:
    """Parse uploaded CSV/Excel-compatible CSV into normalized row dicts."""
    raw = file_obj.read()
    if isinstance(raw, bytes):
        text = raw.decode("utf-8-sig", errors="replace")
    else:
        text = str(raw)

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], []

    raw_headers = rows[0]
    headers = [normalize_header(h) for h in raw_headers]
    label_to_key = {normalize_header(col.label): col.key for col in []}

    data_rows: list[dict[str, str]] = []
    for row_values in rows[1:]:
        if not any(str(v).strip() for v in row_values):
            continue
        if all(str(v).strip().startswith("(") or "required" in str(v).lower() or "options:" in str(v).lower()
               for v in row_values if str(v).strip()):
            continue
        row_dict: dict[str, str] = {}
        for idx, header in enumerate(headers):
            if not header:
                continue
            value = row_values[idx].strip() if idx < len(row_values) else ""
            row_dict[header] = value
        data_rows.append(row_dict)
    return headers, data_rows


def map_headers_to_keys(headers: list[str], spec: ImportSpec) -> dict[str, str]:
    """Map file headers to spec column keys (by label or key)."""
    col_map = spec.column_map()
    label_lookup = {normalize_header(c.label): c.key for c in spec.columns}
    key_lookup = {normalize_header(c.key): c.key for c in spec.columns}
    mapping: dict[str, str] = {}
    for header in headers:
        if header in key_lookup:
            mapping[header] = key_lookup[header]
        elif header in label_lookup:
            mapping[header] = label_lookup[header]
    return mapping


def validate_headers(headers: list[str], spec: ImportSpec) -> list[dict[str, Any]]:
    """Return header-level errors (missing required columns)."""
    mapping = map_headers_to_keys(headers, spec)
    mapped_keys = set(mapping.values())
    errors: list[dict[str, Any]] = []
    for col in spec.columns:
        if col.required and col.key not in mapped_keys:
            errors.append({
                "row": 0,
                "field": col.key,
                "message": f"Missing required column: {col.label}",
            })
    unknown = [h for h in headers if h and h not in mapping]
    if unknown:
        for h in unknown:
            errors.append({
                "row": 0,
                "field": h,
                "message": f"Unrecognized column: {h}",
                "severity": "warning",
            })
    return errors


def _parse_bool(value: str) -> bool | None:
    v = value.strip().lower()
    if v in ("yes", "y", "true", "1"):
        return True
    if v in ("no", "n", "false", "0"):
        return False
    return None


def _parse_date(value: str) -> date | None:
    v = value.strip()
    if not v:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    return None


def _coerce_value(col: ImportColumn, raw: str) -> tuple[Any, str | None]:
    value = raw.strip()
    if not value:
        if col.required:
            return None, f"{col.label} is required"
        return None, None

    if col.choices:
        normalized = value.lower().replace(" ", "_")
        valid = {c.lower(): c for c in col.choices}
        if normalized not in valid:
            return None, f"{col.label} must be one of: {', '.join(col.choices)}"
        return valid[normalized], None

    if col.field_type == "date":
        parsed = _parse_date(value)
        if parsed is None:
            return None, f"{col.label} must be a valid date (YYYY-MM-DD)"
        return parsed, None

    if col.field_type == "decimal":
        try:
            return Decimal(value.replace(",", "")), None
        except InvalidOperation:
            return None, f"{col.label} must be a valid number"

    if col.field_type == "integer":
        try:
            return int(value), None
        except ValueError:
            return None, f"{col.label} must be a whole number"

    if col.field_type == "boolean":
        parsed = _parse_bool(value)
        if parsed is None:
            return None, f"{col.label} must be yes/no"
        return parsed, None

    if col.field_type == "email":
        error = validate_deliverable_email(value, required=col.required)
        if error:
            return None, error
        return value.lower(), None

    if col.field_type == "phone":
        if not PHONE_RE.match(value):
            return None, f"{col.label} must be a valid phone number"
        return value, None

    return value, None


def validate_rows(
    spec: ImportSpec,
    headers: list[str],
    raw_rows: list[dict[str, str]],
    *,
    row_resolver: Callable[[dict[str, Any], int], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Validate parsed rows against spec; optional resolver adds FK/business rules."""
    header_errors = validate_headers(headers, spec)
    mapping = map_headers_to_keys(headers, spec)
    col_map = spec.column_map()

    ready: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = list(header_errors)

    if any(e.get("severity") != "warning" for e in header_errors):
        return {
            "ready": [],
            "errors": errors,
            "total_rows": len(raw_rows),
            "valid_count": 0,
            "error_count": len(errors),
            "can_commit": False,
        }

    for idx, raw_row in enumerate(raw_rows, start=2):
        parsed: dict[str, Any] = {"_row_number": idx}
        row_errors: list[dict[str, Any]] = []

        for file_header, spec_key in mapping.items():
            col = col_map.get(spec_key)
            if not col:
                continue
            raw_val = raw_row.get(file_header, "")
            coerced, err = _coerce_value(col, raw_val)
            if err:
                row_errors.append({"row": idx, "field": spec_key, "message": err})
            elif coerced is not None:
                parsed[spec_key] = coerced

        for col in spec.columns:
            if col.required and col.key not in parsed:
                row_errors.append({
                    "row": idx,
                    "field": col.key,
                    "message": f"{col.label} is required",
                })

        if row_resolver:
            row_errors.extend(row_resolver(parsed, idx))

        if row_errors:
            errors.extend(row_errors)
        else:
            ready.append(parsed)

    return {
        "ready": ready,
        "errors": errors,
        "total_rows": len(raw_rows),
        "valid_count": len(ready),
        "error_count": len([e for e in errors if e.get("severity") != "warning"]),
        "can_commit": len(ready) > 0 and not any(
            e.get("severity") != "warning" and e.get("row") == 0 for e in errors
        ),
    }