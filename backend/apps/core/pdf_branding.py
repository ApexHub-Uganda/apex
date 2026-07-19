"""Extract school branding for PDF templates and UI theme application."""
from __future__ import annotations

import re
from typing import Any

from apps.core.constants import COLOR_ACCENT, COLOR_PRIMARY, COLOR_SECONDARY
from apps.core.media_utils import resolve_media_url

_HEX_RE = re.compile(r"^#([0-9A-Fa-f]{6})$")


def normalize_hex_color(value: str | None, default: str) -> str:
    """Return #RRGGBB or *default* if value is missing/invalid."""
    if not value:
        return default
    text = str(value).strip()
    if _HEX_RE.match(text):
        return text.upper() if text.startswith("#") else f"#{text.upper()}"
    # Allow #rgb shorthand
    if re.match(r"^#[0-9A-Fa-f]{3}$", text):
        r, g, b = text[1], text[2], text[3]
        return f"#{r}{r}{g}{g}{b}{b}".upper()
    return default


def build_tenant_branding(tenant, *, request=None) -> dict[str, Any]:
    """
    Canonical branding payload used by the PDF engine and school settings UI.

    Safe for tenants with incomplete profiles — always returns usable defaults.
    """
    if tenant is None:
        return {
            "school_id": None,
            "school_name": "School",
            "school_code": "",
            "email": "",
            "phone": "",
            "address": "",
            "city": "",
            "country": "",
            "website": "",
            "timezone": "Africa/Nairobi",
            "tagline": "",
            "motto": "",
            "logo_url": None,
            "logo_path": None,
            "primary_color": COLOR_PRIMARY,
            "secondary_color": COLOR_SECONDARY,
            "accent_color": COLOR_ACCENT,
            "contact_line": "",
            "location_line": "",
        }

    primary = normalize_hex_color(getattr(tenant, "primary_color", None), COLOR_PRIMARY)
    secondary = normalize_hex_color(getattr(tenant, "secondary_color", None), COLOR_SECONDARY)
    accent = normalize_hex_color(getattr(tenant, "accent_color", None), COLOR_ACCENT)

    address = (getattr(tenant, "address", None) or "").strip()
    city = (getattr(tenant, "city", None) or "").strip()
    country = (getattr(tenant, "country", None) or "").strip()
    location_parts = [p for p in (address, city, country) if p]
    location_line = ", ".join(location_parts)

    email = (getattr(tenant, "email", None) or "").strip()
    phone = (getattr(tenant, "phone", None) or "").strip()
    website = (getattr(tenant, "website", None) or "").strip()
    contact_parts = [p for p in (phone, email, website) if p]
    contact_line = "  ·  ".join(contact_parts)

    logo_field = getattr(tenant, "logo", None)
    logo_path = None
    if logo_field and getattr(logo_field, "name", None):
        try:
            logo_path = logo_field.path
        except Exception:
            logo_path = None

    tagline = (getattr(tenant, "tagline", None) or "").strip()

    return {
        "school_id": str(tenant.id),
        "school_name": tenant.name or "School",
        "school_code": getattr(tenant, "code", "") or "",
        "email": email,
        "phone": phone,
        "address": address,
        "city": city,
        "country": country,
        "website": website,
        "timezone": getattr(tenant, "timezone", None) or "Africa/Nairobi",
        "tagline": tagline,
        "motto": tagline,  # motto/tagline — same field in current schema
        "logo_url": resolve_media_url(request, logo_field) if logo_field else None,
        "logo_path": logo_path,
        "primary_color": primary,
        "secondary_color": secondary,
        "accent_color": accent,
        "contact_line": contact_line,
        "location_line": location_line,
    }
