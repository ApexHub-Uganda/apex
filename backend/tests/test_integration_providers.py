import pytest
from django.test import override_settings

from apps.platform.models import EmailSetting, SMSSetting, WhatsAppSetting
from apps.platform.services.integrations import EmailService, SMSService, WhatsAppService
from apps.platform.services.providers import get_integration_channel_status
from apps.platform.services.providers.registry import get_email_provider


@pytest.mark.django_db
class TestIntegrationProviders:
    @override_settings(INTEGRATION_LIVE_DISPATCH=False)
    def test_channel_status_reports_unconfigured_channels(self):
        status = get_integration_channel_status()
        assert "email" in status["channels"]
        assert "sms" in status["channels"]
        assert "whatsapp" in status["channels"]
        assert status["live_dispatch"] is False

    @override_settings(INTEGRATION_LIVE_DISPATCH=False)
    def test_email_builds_smtp_payload_before_live_dispatch(self):
        EmailSetting.objects.all().delete()
        EmailSetting.objects.create(
            provider="smtp",
            host="smtp.example.com",
            port=587,
            username="api",
            password="secret",
            from_email="noreply@example.com",
            is_active=True,
        )
        result = EmailService.send("admin@test.edu", "Subject", "Body")
        assert result.success is False
        assert "live dispatch is disabled" in result.message.lower()
        assert result.metadata["provider"] == "smtp"
        deliveries = result.metadata.get("deliveries") or []
        endpoint = deliveries[0]["metadata"]["endpoint"] if deliveries else result.metadata.get("endpoint", "")
        assert "smtp.example.com" in endpoint

    @override_settings(INTEGRATION_LIVE_DISPATCH=True)
    def test_sms_twilio_payload_prepared_with_normalized_phone(self):
        SMSSetting.objects.create(
            provider="twilio",
            api_key="AC123",
            api_secret="token",
            sender_id="+15550001111",
            is_active=True,
        )
        result = SMSService.send("0712345678", "Hello school admin")
        assert result.success is False
        assert "twilio" in result.message.lower()
        assert result.metadata["request_body"]["To"].startswith("+")

    def test_whatsapp_meta_requires_phone_number_id(self):
        WhatsAppSetting.objects.create(
            provider="meta",
            api_key="token",
            is_active=True,
        )
        status = get_integration_channel_status()
        assert "phone_number_id" in " ".join(status["channels"]["whatsapp"]["validation_errors"])

    def test_smtp_provider_validation_lists_missing_host(self):
        adapter = get_email_provider("smtp")
        config = EmailSetting(provider="smtp", from_email="a@b.com")
        errors = adapter.validate_config(config)
        assert "host" in errors