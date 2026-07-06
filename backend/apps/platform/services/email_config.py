"""Sync platform EmailSetting records from Django environment variables."""
from __future__ import annotations

import re
from typing import Any, Optional

from django.conf import settings

from apps.platform.models import EmailSetting


def _normalize_app_password(value: str) -> str:
    """Gmail app passwords are 16 chars — strip spaces from pasted values."""
    return re.sub(r"\s+", "", (value or "").strip())


def sync_email_settings_from_env() -> Optional[EmailSetting]:
    """Create or update the active EmailSetting from EMAIL_* Django settings."""
    host = (getattr(settings, "EMAIL_HOST", "") or "").strip()
    if not host:
        return EmailSetting.objects.filter(is_active=True).first()

    values = {
        "provider": "smtp",
        "host": host,
        "port": int(getattr(settings, "EMAIL_PORT", 587) or 587),
        "use_tls": bool(getattr(settings, "EMAIL_USE_TLS", True)),
        "username": (getattr(settings, "EMAIL_HOST_USER", "") or "").strip(),
        "password": _normalize_app_password(getattr(settings, "EMAIL_HOST_PASSWORD", "") or ""),
        "from_email": (
            getattr(settings, "DEFAULT_FROM_EMAIL", "") or "noreply@apexhub.io"
        ).strip(),
        "is_active": True,
    }

    record = (
        EmailSetting.objects.filter(is_active=True).order_by("-updated_at").first()
        or EmailSetting.objects.order_by("-updated_at").first()
    )
    if record:
        for key, value in values.items():
            setattr(record, key, value)
        record.save()
        return record

    return EmailSetting.objects.create(**values)


def ensure_email_config() -> Optional[EmailSetting]:
    """Return an active email configuration, syncing from env when needed."""
    active = EmailSetting.objects.filter(is_active=True).first()
    if active and active.host:
        return active

    host = (getattr(settings, "EMAIL_HOST", "") or "").strip()
    if host:
        return sync_email_settings_from_env()

    return EmailSetting.objects.filter(host__gt="").first()


def diagnose_smtp_config() -> dict[str, Any]:
    """Return non-secret SMTP configuration health for super-admins."""
    from apps.platform.services.providers.registry import get_email_provider

    record = ensure_email_config()
    live = bool(getattr(settings, "INTEGRATION_LIVE_DISPATCH", False))
    if not record:
        return {
            "configured": False,
            "live_dispatch": live,
            "error": "No email settings found. Set EMAIL_HOST and related variables in .env.",
        }

    adapter = get_email_provider(record.provider)
    validation_errors = adapter.validate_config(record)
    return {
        "configured": True,
        "live_dispatch": live,
        "provider": record.provider,
        "host": record.host,
        "port": record.port,
        "use_tls": record.use_tls,
        "username": record.username,
        "from_email": record.from_email,
        "is_active": record.is_active,
        "password_set": bool(record.password),
        "password_length": len(record.password or ""),
        "validation_errors": validation_errors,
        "ready": record.is_active and not validation_errors and live,
    }


def format_smtp_error(exc: Exception) -> str:
    """Translate low-level SMTP exceptions into actionable guidance."""
    raw = str(exc)
    lower = raw.lower()
    if "535" in raw or "badcredentials" in lower or "username and password not accepted" in lower:
        username = (getattr(settings, "EMAIL_HOST_USER", "") or "your Gmail account").strip()
        return (
            f"Gmail SMTP authentication failed for {username}. "
            "Regenerate a Google App Password (Google Account → Security → 2-Step Verification → "
            "App passwords), update EMAIL_HOST_PASSWORD in .env with the 16-character password "
            "(no spaces), restart the backend, and try again."
        )
    if "connection refused" in lower or "timed out" in lower:
        return f"Cannot reach SMTP server at {getattr(settings, 'EMAIL_HOST', 'smtp')}: {raw}"
    return f"SMTP send failed: {raw}"