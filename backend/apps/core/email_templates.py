"""Shared HTML + plain-text email templates for Apex Hub outbound mail."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Literal

from django.conf import settings
from django.utils import timezone

EmailTone = Literal["info", "warning", "critical", "success", "announcement", "broadcast"]
EmailScope = Literal["platform", "school"]

_TONE_STYLES: dict[str, dict[str, str]] = {
    "info": {
        "label": "Information",
        "accent": "#2563eb",
        "badge_bg": "#eff6ff",
        "badge_border": "#bfdbfe",
        "badge_text": "#1d4ed8",
    },
    "warning": {
        "label": "Important",
        "accent": "#d97706",
        "badge_bg": "#fffbeb",
        "badge_border": "#fde68a",
        "badge_text": "#b45309",
    },
    "critical": {
        "label": "Urgent",
        "accent": "#dc2626",
        "badge_bg": "#fef2f2",
        "badge_border": "#fecaca",
        "badge_text": "#b91c1c",
    },
    "success": {
        "label": "Success",
        "accent": "#16a34a",
        "badge_bg": "#f0fdf4",
        "badge_border": "#bbf7d0",
        "badge_text": "#15803d",
    },
    "announcement": {
        "label": "Announcement",
        "accent": "#7c3aed",
        "badge_bg": "#f5f3ff",
        "badge_border": "#ddd6fe",
        "badge_text": "#6d28d9",
    },
    "broadcast": {
        "label": "Broadcast",
        "accent": "#0f766e",
        "badge_bg": "#f0fdfa",
        "badge_border": "#99f6e4",
        "badge_text": "#0f766e",
    },
}


@dataclass(frozen=True)
class BrandedEmail:
    text_body: str
    html_body: str


def _platform_name() -> str:
    return (getattr(settings, "PLATFORM_NAME", "") or "Apex Hub").strip()


def _support_email() -> str:
    return (
        getattr(settings, "DEFAULT_FROM_EMAIL", "") or "client.apexhub@gmail.com"
    ).strip()


def _school_name(tenant) -> str:
    if tenant is None:
        return "Your School"
    return (getattr(tenant, "name", "") or "Your School").strip()


def _brand_label(*, scope: EmailScope, tenant=None) -> str:
    if scope == "school":
        return _school_name(tenant)
    return _platform_name()


def _footer_line(*, scope: EmailScope, tenant=None) -> str:
    platform = _platform_name()
    school = _school_name(tenant)
    support = _support_email()
    if scope == "school":
        return f"Sent via {platform} on behalf of {school} · {support}"
    return f"Sent securely from {support}"


def _escape_text(value: str) -> str:
    return html.escape((value or "").strip())


def _paragraphs_to_html(body: str) -> str:
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", (body or "").strip()) if chunk.strip()]
    if not chunks:
        return '<p style="margin:0;font-size:15px;line-height:1.7;color:#475569;">&nbsp;</p>'
    return "".join(
        f'<p style="margin:0 0 14px;font-size:15px;line-height:1.7;color:#475569;">'
        f'{html.escape(chunk).replace(chr(10), "<br />")}</p>'
        for chunk in chunks
    )


def _paragraphs_to_text(body: str) -> str:
    return (body or "").strip()


def build_branded_email(
    *,
    title: str,
    body: str,
    tone: EmailTone = "info",
    scope: EmailScope = "platform",
    tenant=None,
    greeting: str = "",
    subtitle: str = "",
    highlight_html: str = "",
    footer_note: str = "",
) -> BrandedEmail:
    """Render a professional HTML + plain-text email using the shared Apex layout."""
    tone_style = _TONE_STYLES.get(tone, _TONE_STYLES["info"])
    brand = _brand_label(scope=scope, tenant=tenant)
    footer = _footer_line(scope=scope, tenant=tenant)
    year = timezone.now().year
    support = _support_email()

    safe_title = _escape_text(title)
    safe_subtitle = _escape_text(subtitle)
    safe_greeting = _escape_text(greeting)
    safe_footer_note = _escape_text(footer_note)

    greeting_html = ""
    if safe_greeting:
        greeting_html = (
            f'<p style="margin:0 0 12px;font-size:15px;line-height:1.6;color:#475569;">'
            f"Hello {safe_greeting},</p>"
        )
    subtitle_html = ""
    if safe_subtitle:
        subtitle_html = (
            f'<p style="margin:0;font-size:15px;line-height:1.6;color:#475569;">{safe_subtitle}</p>'
        )

    highlight_block = highlight_html or ""
    footer_note_html = ""
    if safe_footer_note:
        footer_note_html = (
            f'<p style="margin:14px 0 0;font-size:13px;line-height:1.6;color:#64748b;">'
            f"{safe_footer_note}</p>"
        )

    text_parts = [f"{brand} — {title}", "─" * 36, ""]
    if greeting:
        text_parts.append(f"Hello {greeting.strip()},")
        text_parts.append("")
    if subtitle:
        text_parts.append(subtitle.strip())
        text_parts.append("")
    text_parts.append(_paragraphs_to_text(body))
    if footer_note:
        text_parts.extend(["", footer_note.strip()])
    text_parts.extend(["", "—", brand, footer])

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title}</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#0f172a;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f1f5f9;padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border-radius:16px;border:1px solid #e2e8f0;overflow:hidden;">
          <tr>
            <td style="padding:28px 32px 16px;">
              <div style="font-size:13px;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;color:{tone_style['accent']};">{_escape_text(brand)}</div>
              <div style="display:inline-block;margin-top:14px;padding:6px 10px;border-radius:999px;background:{tone_style['badge_bg']};border:1px solid {tone_style['badge_border']};font-size:11px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:{tone_style['badge_text']};">{tone_style['label']}</div>
              <h1 style="margin:14px 0 8px;font-size:24px;line-height:1.3;font-weight:700;color:#0f172a;">{safe_title}</h1>
              {subtitle_html}
            </td>
          </tr>
          <tr>
            <td style="padding:0 32px 8px;">
              {greeting_html}
              {_paragraphs_to_html(body)}
              {highlight_block}
              {footer_note_html}
            </td>
          </tr>
          <tr>
            <td style="padding:18px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;">
              <p style="margin:0;font-size:12px;line-height:1.5;color:#94a3b8;">
                {_escape_text(footer)}<br />
                &copy; {year} {_escape_text(_platform_name())}
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    return BrandedEmail(text_body="\n".join(text_parts), html_body=html_body)


def build_password_reset_email(
    *,
    first_name: str,
    email: str,
    otp: str,
    expires_minutes: int,
) -> BrandedEmail:
    platform = _platform_name()
    safe_otp = _escape_text(otp)
    highlight = f"""
              <div style="margin-top:18px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:24px;text-align:center;">
                <div style="font-size:12px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#64748b;margin-bottom:12px;">Verification code</div>
                <div style="font-size:34px;font-weight:700;letter-spacing:0.35em;color:#0f172a;padding-left:0.35em;">{safe_otp}</div>
              </div>"""

    return build_branded_email(
        title="Password reset code",
        body=(
            f"We received a request to reset the password for your {platform} account ({email}). "
            f"Enter the verification code below on the password reset page to choose a new password.\n\n"
            f"Your verification code:\n\n    {otp}\n\n"
            f"This code expires in {expires_minutes} minutes. For your security, do not share it with anyone."
        ),
        tone="info",
        scope="platform",
        greeting=first_name or "there",
        subtitle="Use the verification code below to reset your password.",
        highlight_html=highlight,
        footer_note="If you did not request a password reset, you can ignore this email. Your password will remain unchanged.",
    )


def build_staff_portal_welcome_email(
    *,
    first_name: str,
    email: str,
    temp_password: str,
    tenant,
    login_url: str,
) -> BrandedEmail:
    school = _school_name(tenant)
    safe_password = _escape_text(temp_password)
    highlight = f"""
              <div style="margin-top:18px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:24px;">
                <div style="font-size:12px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#64748b;margin-bottom:12px;">One-time password</div>
                <div style="font-size:28px;font-weight:700;letter-spacing:0.2em;color:#0f172a;">{safe_password}</div>
              </div>"""

    return build_branded_email(
        title="Your staff portal account",
        body=(
            f"Welcome to {school}. A portal account has been created for you.\n\n"
            f"Sign in at: {login_url}\n"
            f"Email: {email}\n"
            f"One-time password: {temp_password}\n\n"
            "You will be asked to choose a new password immediately after your first sign-in. "
            "Do not share this password with anyone."
        ),
        tone="info",
        scope="school",
        tenant=tenant,
        greeting=first_name or "there",
        subtitle="Use these credentials for your first sign-in only.",
        highlight_html=highlight,
        footer_note="If you were not expecting this account, contact your school administrator.",
    )


def build_announcement_email(
    *,
    tenant,
    title: str,
    content: str,
    priority: str = "normal",
) -> BrandedEmail:
    tone_map = {"urgent": "critical", "high": "warning", "normal": "announcement", "low": "info"}
    return build_branded_email(
        title=title,
        body=content,
        tone=tone_map.get(priority, "announcement"),
        scope="school",
        tenant=tenant,
        subtitle="A new announcement from your school.",
    )


def build_school_broadcast_email(
    *,
    tenant,
    title: str,
    message: str,
) -> BrandedEmail:
    return build_branded_email(
        title=title,
        body=message,
        tone="broadcast",
        scope="school",
        tenant=tenant,
        subtitle="Important message from your school administration.",
    )


def build_platform_broadcast_email(
    *,
    title: str,
    message: str,
    severity: str = "info",
) -> BrandedEmail:
    tone_map = {"critical": "critical", "warning": "warning", "info": "info"}
    return build_branded_email(
        title=title,
        body=message,
        tone=tone_map.get(severity, "info"),
        scope="platform",
        subtitle="Platform update for your school account.",
    )


def build_account_notification_email(
    *,
    first_name: str,
    title: str,
    message: str,
    tone: EmailTone = "success",
    scope: EmailScope = "platform",
    tenant=None,
) -> BrandedEmail:
    return build_branded_email(
        title=title,
        body=message,
        tone=tone,
        scope=scope,
        tenant=tenant,
        greeting=first_name or "there",
    )


def build_direct_message_email(
    *,
    tenant,
    subject: str,
    body: str,
) -> BrandedEmail:
    return build_branded_email(
        title=subject,
        body=body,
        tone="info",
        scope="school",
        tenant=tenant,
        subtitle="Message from your school.",
    )