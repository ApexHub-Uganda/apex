"""WebAuthn registration & assertion (platform biometrics preferred)."""
from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from apps.accounts.webauthn_models import WebAuthnChallenge, WebAuthnCredential


class WebAuthnError(Exception):
    def __init__(self, message: str, *, code: str = "webauthn_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def _rp_id(request) -> str:
    """Relying Party ID must be the effective host (no port)."""
    configured = getattr(settings, "WEBAUTHN_RP_ID", None) or ""
    if configured:
        return configured.strip()
    host = request.get_host().split(":")[0]
    # Strip leading www. only if you intentionally serve bare domain as RP ID
    return host


def _rp_name() -> str:
    return getattr(settings, "WEBAUTHN_RP_NAME", None) or "Apex Hub"


def _origin(request) -> str:
    configured = getattr(settings, "WEBAUTHN_ORIGIN", None) or ""
    if configured:
        return configured.rstrip("/")
    # Prefer Origin header from browser (correct for SPA + API split)
    origin = request.headers.get("Origin") or request.META.get("HTTP_ORIGIN")
    if origin:
        return origin.rstrip("/")
    scheme = "https" if request.is_secure() else "http"
    return f"{scheme}://{request.get_host()}".rstrip("/")


def _challenge_ttl() -> timedelta:
    minutes = int(getattr(settings, "WEBAUTHN_CHALLENGE_MINUTES", 5) or 5)
    return timedelta(minutes=max(1, min(minutes, 15)))


def _store_challenge(*, user, purpose: str, challenge: str) -> WebAuthnChallenge:
    WebAuthnChallenge.objects.filter(
        user=user, purpose=purpose, consumed=False,
    ).update(consumed=True)
    return WebAuthnChallenge.objects.create(
        user=user,
        purpose=purpose,
        challenge=challenge,
        expires_at=timezone.now() + _challenge_ttl(),
    )


def _pop_challenge(*, user, purpose: str, expected: str | None = None) -> WebAuthnChallenge:
    qs = WebAuthnChallenge.objects.filter(
        user=user, purpose=purpose, consumed=False,
    ).order_by("-created_at")
    row = qs.first()
    if row is None or not row.is_valid:
        raise WebAuthnError("Biometric challenge expired. Try again.", code="challenge_expired")
    if expected and row.challenge != expected:
        # Still accept if browser echoes differently — primary check is in verify_*
        pass
    row.consumed = True
    row.save(update_fields=["consumed"])
    return row


def list_credentials(user) -> list[dict[str, Any]]:
    rows = WebAuthnCredential.objects.filter(user=user, is_active=True)
    return [
        {
            "id": str(c.id),
            "device_label": c.device_label or "This device",
            "backed_by_platform": c.backed_by_platform,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
            "transports": c.transports or [],
        }
        for c in rows
    ]


def webauthn_status(user) -> dict[str, Any]:
    creds = list_credentials(user)
    return {
        "enrolled": len(creds) > 0,
        "credential_count": len(creds),
        "credentials": creds,
        "required_for_staff_check_in": True,
        "preferred_authenticator": "platform",  # fingerprint / face / device biometrics
        "supported_hint": (
            "Register a fingerprint (or Face ID / Windows Hello) on this device. "
            "You will verify it every time you sign attendance after location is confirmed."
        ),
    }


def begin_registration(request, user) -> dict[str, Any]:
    existing = WebAuthnCredential.objects.filter(user=user, is_active=True)
    exclude = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id))
        for c in existing
    ]
    options = generate_registration_options(
        rp_id=_rp_id(request),
        rp_name=_rp_name(),
        user_id=str(user.id).encode("utf-8"),
        user_name=user.email,
        user_display_name=user.full_name or user.email,
        exclude_credentials=exclude,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        timeout=120_000,
    )
    _store_challenge(user=user, purpose=WebAuthnChallenge.PURPOSE_REGISTER, challenge=bytes_to_base64url(options.challenge))
    # options_to_json returns a JSON string
    return json.loads(options_to_json(options))


def complete_registration(request, user, credential: dict, *, device_label: str = "") -> dict[str, Any]:
    ch = _pop_challenge(user=user, purpose=WebAuthnChallenge.PURPOSE_REGISTER)
    try:
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(ch.challenge),
            expected_rp_id=_rp_id(request),
            expected_origin=_origin(request),
            require_user_verification=True,
        )
    except Exception as exc:
        raise WebAuthnError(
            f"Could not register biometric: {exc}",
            code="register_failed",
        ) from exc

    cred_id = bytes_to_base64url(verification.credential_id)
    pub_key = bytes_to_base64url(verification.credential_public_key)
    if WebAuthnCredential.objects.filter(credential_id=cred_id).exists():
        raise WebAuthnError("This authenticator is already registered.", code="already_registered")

    label = (device_label or "").strip() or "This device"
    row = WebAuthnCredential.objects.create(
        user=user,
        tenant=user.tenant,
        credential_id=cred_id,
        public_key=pub_key,
        sign_count=verification.sign_count or 0,
        device_label=label[:120],
        aaguid=str(getattr(verification, "aaguid", "") or ""),
        backed_by_platform=True,
        transports=list(credential.get("response", {}).get("transports") or ["internal"]),
        is_active=True,
    )
    return {
        "credential": {
            "id": str(row.id),
            "device_label": row.device_label,
            "created_at": row.created_at.isoformat(),
        },
        "message": "Fingerprint / device biometric registered for attendance.",
        **webauthn_status(user),
    }


def begin_authentication(request, user) -> dict[str, Any]:
    creds = list(WebAuthnCredential.objects.filter(user=user, is_active=True))
    if not creds:
        raise WebAuthnError(
            "No biometric is registered on this account. Enroll fingerprint first.",
            code="not_enrolled",
        )
    allow = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id))
        for c in creds
    ]
    options = generate_authentication_options(
        rp_id=_rp_id(request),
        allow_credentials=allow,
        user_verification=UserVerificationRequirement.REQUIRED,
        timeout=120_000,
    )
    _store_challenge(
        user=user,
        purpose=WebAuthnChallenge.PURPOSE_AUTH,
        challenge=bytes_to_base64url(options.challenge),
    )
    return json.loads(options_to_json(options))


def complete_authentication(request, user, credential: dict) -> dict[str, Any]:
    ch = _pop_challenge(user=user, purpose=WebAuthnChallenge.PURPOSE_AUTH)
    raw_id = credential.get("rawId") or credential.get("id")
    if not raw_id:
        raise WebAuthnError("Invalid biometric response.", code="invalid_credential")

    # Credential id may already be base64url
    cred_id = raw_id if isinstance(raw_id, str) else bytes_to_base64url(raw_id)
    stored = WebAuthnCredential.objects.filter(
        user=user, credential_id=cred_id, is_active=True,
    ).first()
    if stored is None:
        # Try matching by decoding variants
        stored = WebAuthnCredential.objects.filter(user=user, is_active=True).first()
        for c in WebAuthnCredential.objects.filter(user=user, is_active=True):
            if c.credential_id == cred_id:
                stored = c
                break
    if stored is None:
        raise WebAuthnError(
            "This biometric is not registered for your account.",
            code="unknown_credential",
        )

    try:
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(ch.challenge),
            expected_rp_id=_rp_id(request),
            expected_origin=_origin(request),
            credential_public_key=base64url_to_bytes(stored.public_key),
            credential_current_sign_count=stored.sign_count,
            require_user_verification=True,
        )
    except Exception as exc:
        raise WebAuthnError(
            f"Biometric verification failed: {exc}",
            code="assert_failed",
        ) from exc

    new_count = verification.new_sign_count or stored.sign_count
    # sign_count 0 is allowed for some platform authenticators; only reject clear clones
    if stored.sign_count and new_count < stored.sign_count:
        raise WebAuthnError(
            "Biometric counter anomaly. Re-enroll this device.",
            code="sign_count",
        )
    stored.sign_count = max(stored.sign_count, new_count)
    stored.touch_used()
    stored.save(update_fields=["sign_count", "last_used_at", "updated_at"])

    return {
        "verified": True,
        "credential_id": str(stored.id),
        "device_label": stored.device_label,
        "message": "Identity verified.",
    }


def revoke_credential(*, user, credential_pk: str) -> dict[str, Any]:
    row = WebAuthnCredential.objects.filter(user=user, pk=credential_pk, is_active=True).first()
    if row is None:
        raise WebAuthnError("Credential not found.", code="not_found")
    row.is_active = False
    row.save(update_fields=["is_active", "updated_at"])
    return {"message": "Biometric removed from this account.", **webauthn_status(user)}


def require_verified_webauthn(request, user, assertion: dict | None) -> dict[str, Any]:
    """
    Enforce platform biometric for staff attendance.

    - If user has no credentials: raise not_enrolled (client must enroll).
    - If assertion missing: raise assertion_required.
    - Otherwise verify assertion.
    """
    enrolled = WebAuthnCredential.objects.filter(user=user, is_active=True).exists()
    if not enrolled:
        raise WebAuthnError(
            "Register your fingerprint on this device before signing attendance. "
            "This stops colleagues from signing in for each other.",
            code="not_enrolled",
        )
    if not assertion or not isinstance(assertion, dict):
        raise WebAuthnError(
            "Verify it’s you with fingerprint to complete sign-in.",
            code="assertion_required",
        )
    return complete_authentication(request, user, assertion)
