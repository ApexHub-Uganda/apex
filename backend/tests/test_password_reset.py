"""Password reset OTP flow tests."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test.utils import override_settings
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import User
from apps.accounts.password_reset import (
    OTP_LENGTH,
    PasswordResetError,
    confirm_password_reset,
    send_password_reset_otp,
    _hash_otp,
)
from apps.platform.services.integrations import IntegrationResult


@pytest.fixture(autouse=True)
def _reset_password_reset_throttle():
    cache.clear()
    with override_settings(
        REST_FRAMEWORK={
            **settings.REST_FRAMEWORK,
            "DEFAULT_THROTTLE_RATES": {
                **settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}),
                "password_reset": "1000/min",
            },
        },
    ):
        yield
    cache.clear()


@pytest.mark.django_db
class TestPasswordResetOtp:
    def test_request_otp_unknown_email_returns_error(self, api_client):
        response = api_client.post("/api/v1/auth/password-reset/", {
            "email": "missing.user@demoschool.edu",
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No account found" in str(response.data)

    def test_request_otp_invalid_email_format(self, api_client):
        response = api_client.post("/api/v1/auth/password-reset/", {
            "email": "not-an-email",
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("apps.accounts.password_reset.EmailService.send")
    def test_request_otp_success(self, mock_send, api_client, super_admin):
        mock_send.return_value = IntegrationResult(
            success=True,
            message="Email delivered to 1 recipient(s).",
        )

        response = api_client.post("/api/v1/auth/password-reset/", {
            "email": super_admin.email,
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "6-digit" in response.data["message"]
        mock_send.assert_called_once()

        super_admin.refresh_from_db()
        assert super_admin.password_reset_token
        assert super_admin.password_reset_expires
        assert super_admin.password_reset_expires > timezone.now()

        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs.get("from_email") or mock_send.call_args[0]
        subject = mock_send.call_args[0][1]
        body = mock_send.call_args[0][2]
        assert "password reset" in subject.lower()
        assert "verification code" in body.lower() or "verification code" in (call_kwargs.get("html_body") or "").lower()

    @patch("apps.accounts.password_reset.EmailService.send")
    def test_request_otp_send_failure_surfaces_error(self, mock_send, api_client, super_admin):
        mock_send.return_value = IntegrationResult(
            success=False,
            message="Gmail SMTP authentication failed.",
        )

        response = api_client.post("/api/v1/auth/password-reset/", {
            "email": super_admin.email,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "could not send" in str(response.data).lower() or "smtp" in str(response.data).lower()

        super_admin.refresh_from_db()
        assert not super_admin.password_reset_token

    @patch("apps.accounts.password_reset.EmailService.send")
    def test_confirm_otp_resets_password(self, mock_send, api_client, super_admin):
        mock_send.return_value = IntegrationResult(success=True, message="sent")

        api_client.post("/api/v1/auth/password-reset/", {"email": super_admin.email})
        otp = "482910"
        super_admin.refresh_from_db()
        super_admin.password_reset_token = _hash_otp(user_id=str(super_admin.id), otp=otp)
        super_admin.password_reset_expires = timezone.now() + timezone.timedelta(minutes=10)
        super_admin.save(update_fields=["password_reset_token", "password_reset_expires", "updated_at"])

        response = api_client.post("/api/v1/auth/password-reset/confirm/", {
            "email": super_admin.email,
            "otp": otp,
            "new_password": "NewSecure@2026",
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

        super_admin.refresh_from_db()
        assert super_admin.check_password("NewSecure@2026")
        assert not super_admin.password_reset_token

        login_response = api_client.post("/api/v1/auth/login/", {
            "email": super_admin.email,
            "password": "NewSecure@2026",
        })
        assert login_response.status_code == status.HTTP_200_OK

    def test_confirm_wrong_otp_returns_error(self, api_client, super_admin):
        super_admin.password_reset_token = _hash_otp(user_id=str(super_admin.id), otp="111111")
        super_admin.password_reset_expires = timezone.now() + timezone.timedelta(minutes=10)
        super_admin.save(update_fields=["password_reset_token", "password_reset_expires", "updated_at"])

        response = api_client.post("/api/v1/auth/password-reset/confirm/", {
            "email": super_admin.email,
            "otp": "222222",
            "new_password": "AnotherPass@2026",
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "incorrect" in str(response.data).lower()

    def test_confirm_expired_otp_returns_error(self, api_client, super_admin):
        otp = "909090"
        super_admin.password_reset_token = _hash_otp(user_id=str(super_admin.id), otp=otp)
        super_admin.password_reset_expires = timezone.now() - timezone.timedelta(minutes=1)
        super_admin.save(update_fields=["password_reset_token", "password_reset_expires", "updated_at"])

        response = api_client.post("/api/v1/auth/password-reset/confirm/", {
            "email": super_admin.email,
            "otp": otp,
            "new_password": "AnotherPass@2026",
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "expired" in str(response.data).lower()

    @patch("apps.accounts.password_reset.EmailService.send")
    def test_resend_cooldown_blocks_rapid_requests(self, mock_send, api_client, super_admin):
        mock_send.return_value = IntegrationResult(success=True, message="sent")

        first = api_client.post("/api/v1/auth/password-reset/", {"email": super_admin.email})
        assert first.status_code == status.HTTP_200_OK

        second = api_client.post("/api/v1/auth/password-reset/", {"email": super_admin.email})
        assert second.status_code == status.HTTP_400_BAD_REQUEST
        assert "wait" in str(second.data).lower()

    def test_service_generates_six_digit_otp(self, super_admin):
        with patch("apps.accounts.password_reset.EmailService.send") as mock_send:
            mock_send.return_value = IntegrationResult(success=True, message="sent")
            send_password_reset_otp(email=super_admin.email)
        assert mock_send.call_args[0][1]
        subject = mock_send.call_args[0][1]
        code = subject.rsplit(": ", 1)[-1]
        assert len(code) == OTP_LENGTH
        assert code.isdigit()

    def test_confirm_password_reset_service(self, super_admin):
        otp = "135790"
        super_admin.password_reset_token = _hash_otp(user_id=str(super_admin.id), otp=otp)
        super_admin.password_reset_expires = timezone.now() + timezone.timedelta(minutes=10)
        super_admin.save(update_fields=["password_reset_token", "password_reset_expires", "updated_at"])

        confirm_password_reset(
            email=super_admin.email,
            otp=otp,
            new_password="ServicePass@2026",
        )
        super_admin.refresh_from_db()
        assert super_admin.check_password("ServicePass@2026")

    def test_confirm_unknown_email_raises(self):
        with pytest.raises(PasswordResetError) as exc:
            confirm_password_reset(
                email="ghost.user@demoschool.edu",
                otp="123456",
                new_password="ServicePass@2026",
            )
        assert exc.value.code == "account_not_found"