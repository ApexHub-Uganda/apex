"""Self-service password reset via email OTP."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import User
from apps.core.email_templates import build_password_reset_email
from apps.platform.services.integrations import EmailService

OTP_LENGTH = 6
OTP_TTL_MINUTES = 10
MAX_VERIFY_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60
ATTEMPT_CACHE_TTL = OTP_TTL_MINUTES * 60


class PasswordResetError(Exception):
    """Raised when password reset cannot proceed."""

    def __init__(self, message: str, *, code: str = "password_reset_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def _hash_otp(*, user_id: str, otp: str) -> str:
    payload = f"{user_id}:{otp.strip()}"
    return hashlib.sha256(payload.encode()).hexdigest()


def _generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _attempt_cache_key(user_id: str) -> str:
    return f"password_reset_attempts:{user_id}"


def _cooldown_cache_key(user_id: str) -> str:
    return f"password_reset_cooldown:{user_id}"


def _clear_reset_state(user: User) -> None:
    user.password_reset_token = ""
    user.password_reset_expires = None
    user.save(update_fields=["password_reset_token", "password_reset_expires", "updated_at"])
    cache.delete(_attempt_cache_key(str(user.id)))


def _build_email_bodies(*, user: User, otp: str, expires_at) -> tuple[str, str]:
    first_name = (user.first_name or "there").strip() or "there"
    branded = build_password_reset_email(
        first_name=first_name,
        email=user.email,
        otp=otp,
        expires_minutes=OTP_TTL_MINUTES,
    )
    return branded.text_body, branded.html_body


def send_password_reset_otp(*, email: str) -> dict[str, str | int]:
    """Generate and email a 6-digit OTP for an active account."""
    normalized = (email or "").strip().lower()
    try:
        user = User.objects.get(email__iexact=normalized, is_active=True)
    except User.DoesNotExist as exc:
        raise PasswordResetError(
            "No account found with this email address. Check the spelling or contact your school admin.",
            code="account_not_found",
        ) from exc

    cooldown_key = _cooldown_cache_key(str(user.id))
    if cache.get(cooldown_key):
        raise PasswordResetError(
            f"Please wait {RESEND_COOLDOWN_SECONDS} seconds before requesting another code.",
            code="resend_cooldown",
        )

    otp = _generate_otp()
    expires_at = timezone.now() + timedelta(minutes=OTP_TTL_MINUTES)
    user.password_reset_token = _hash_otp(user_id=str(user.id), otp=otp)
    user.password_reset_expires = expires_at
    user.save(update_fields=["password_reset_token", "password_reset_expires", "updated_at"])
    cache.delete(_attempt_cache_key(str(user.id)))

    text_body, html_body = _build_email_bodies(user=user, otp=otp, expires_at=expires_at)
    platform = getattr(settings, "PLATFORM_NAME", "Apex Hub")
    subject = f"{platform} password reset code: {otp}"

    from_email = (
        getattr(settings, "DEFAULT_FROM_EMAIL", "") or "client.apexhub@gmail.com"
    ).strip()

    result = EmailService.send(
        user.email,
        subject,
        text_body,
        html_body=html_body,
        from_email=from_email,
        log_attempt=False,
    )
    if not result.success:
        _clear_reset_state(user)
        raise PasswordResetError(
            result.message or "We could not send the verification email. Try again shortly.",
            code="email_delivery_failed",
        )

    cache.set(cooldown_key, True, timeout=RESEND_COOLDOWN_SECONDS)
    return {
        "email": user.email,
        "expires_in_minutes": OTP_TTL_MINUTES,
        "resend_cooldown_seconds": RESEND_COOLDOWN_SECONDS,
    }


def confirm_password_reset(*, email: str, otp: str, new_password: str) -> User:
    """Validate OTP and set a new password."""
    normalized = (email or "").strip().lower()
    code = (otp or "").strip()
    if not code.isdigit() or len(code) != OTP_LENGTH:
        raise PasswordResetError(
            f"Enter the {OTP_LENGTH}-digit verification code from your email.",
            code="invalid_otp_format",
        )

    try:
        user = User.objects.get(email__iexact=normalized, is_active=True)
    except User.DoesNotExist as exc:
        raise PasswordResetError(
            "No account found with this email address.",
            code="account_not_found",
        ) from exc

    if not user.password_reset_token or not user.password_reset_expires:
        raise PasswordResetError(
            "No active verification code. Request a new code from the forgot password page.",
            code="otp_not_requested",
        )

    if user.password_reset_expires <= timezone.now():
        _clear_reset_state(user)
        raise PasswordResetError(
            "This verification code has expired. Request a new code to continue.",
            code="otp_expired",
        )

    attempt_key = _attempt_cache_key(str(user.id))
    attempts = int(cache.get(attempt_key, 0))
    if attempts >= MAX_VERIFY_ATTEMPTS:
        _clear_reset_state(user)
        raise PasswordResetError(
            "Too many incorrect attempts. Request a new verification code.",
            code="otp_locked",
        )

    expected = user.password_reset_token
    actual = _hash_otp(user_id=str(user.id), otp=code)
    if not hmac.compare_digest(expected, actual):
        cache.set(attempt_key, attempts + 1, timeout=ATTEMPT_CACHE_TTL)
        remaining = max(MAX_VERIFY_ATTEMPTS - (attempts + 1), 0)
        if remaining == 0:
            _clear_reset_state(user)
            raise PasswordResetError(
                "Too many incorrect attempts. Request a new verification code.",
                code="otp_locked",
            )
        raise PasswordResetError(
            f"Incorrect verification code. {remaining} attempt(s) remaining.",
            code="otp_invalid",
        )

    user.set_password(new_password)
    user.password_reset_token = ""
    user.password_reset_expires = None
    user.save(update_fields=["password", "password_reset_token", "password_reset_expires", "updated_at"])
    cache.delete(attempt_key)
    cache.delete(_cooldown_cache_key(str(user.id)))
    return user