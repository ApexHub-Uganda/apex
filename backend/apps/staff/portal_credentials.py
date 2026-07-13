"""Email portal credentials to newly onboarded staff."""
from __future__ import annotations

from django.conf import settings

from apps.core.email_templates import build_staff_portal_welcome_email
from apps.platform.services.integrations import EmailService
from apps.staff.services import StaffOnboardingError


def _frontend_login_url() -> str:
    base = (getattr(settings, "FRONTEND_BASE_URL", "") or "http://localhost:5173").rstrip("/")
    return f"{base}/login"


def send_staff_portal_credentials_email(*, user, tenant, temp_password: str) -> None:
    """Send one-time portal password to a new staff member."""
    branded = build_staff_portal_welcome_email(
        first_name=user.first_name,
        email=user.email,
        temp_password=temp_password,
        tenant=tenant,
        login_url=_frontend_login_url(),
    )
    result = EmailService.send(
        user.email,
        f"{tenant.name} — your portal login",
        branded.text_body,
        html_body=branded.html_body,
        tenant=tenant,
        log_attempt=False,
    )
    if not result.success:
        raise StaffOnboardingError(
            result.message or "Unable to send portal credentials email. Check email settings and try again.",
        )