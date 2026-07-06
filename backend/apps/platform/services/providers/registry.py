"""Provider registry and channel readiness helpers."""
from __future__ import annotations

from typing import Any, Optional

from django.conf import settings

from apps.platform.models import EmailSetting, SMSSetting, WhatsAppSetting
from apps.platform.services.providers.email import (
    MailgunEmailProvider,
    SendgridEmailProvider,
    SmtpEmailProvider,
)
from apps.platform.services.providers.sms import (
    AfricasTalkingSmsProvider,
    NexmoSmsProvider,
    TwilioSmsProvider,
)
from apps.platform.services.providers.whatsapp import (
    AfricasTalkingWhatsAppProvider,
    MetaWhatsAppProvider,
    TwilioWhatsAppProvider,
)

EMAIL_PROVIDERS = {
    "smtp": SmtpEmailProvider,
    "sendgrid": SendgridEmailProvider,
    "mailgun": MailgunEmailProvider,
}

SMS_PROVIDERS = {
    "twilio": TwilioSmsProvider,
    "africas_talking": AfricasTalkingSmsProvider,
    "nexmo": NexmoSmsProvider,
}

WHATSAPP_PROVIDERS = {
    "meta": MetaWhatsAppProvider,
    "twilio": TwilioWhatsAppProvider,
    "africas_talking": AfricasTalkingWhatsAppProvider,
}


def get_email_provider(provider_slug: str):
    return EMAIL_PROVIDERS.get(provider_slug, SmtpEmailProvider)()


def get_sms_provider(provider_slug: str):
    return SMS_PROVIDERS.get(provider_slug, AfricasTalkingSmsProvider)()


def get_whatsapp_provider(provider_slug: str):
    return WHATSAPP_PROVIDERS.get(provider_slug, MetaWhatsAppProvider)()


def _channel_status(config, provider_map: dict, *, channel: str) -> dict[str, Any]:
    live_dispatch = bool(getattr(settings, "INTEGRATION_LIVE_DISPATCH", False))
    if not config:
        return {
            "channel": channel,
            "configured": False,
            "active": False,
            "ready": False,
            "provider": None,
            "validation_errors": ["No active platform setting record"],
            "live_dispatch": live_dispatch,
            "deployment_ready": False,
        }

    adapter = provider_map.get(config.provider, list(provider_map.values())[0])()
    errors = adapter.validate_config(config)
    return {
        "channel": channel,
        "configured": True,
        "active": bool(config.is_active),
        "ready": config.is_active and not errors,
        "provider": config.provider,
        "validation_errors": errors,
        "live_dispatch": live_dispatch,
        "deployment_ready": config.is_active and not errors,
    }


def get_integration_channel_status() -> dict[str, Any]:
    from apps.platform.services.email_config import diagnose_smtp_config, ensure_email_config

    email = ensure_email_config() or EmailSetting.objects.first()
    smtp_diagnostic = diagnose_smtp_config()
    sms = SMSSetting.objects.filter(is_active=True).first() or SMSSetting.objects.first()
    whatsapp = WhatsAppSetting.objects.filter(is_active=True).first() or WhatsAppSetting.objects.first()

    channels = {
        "email": _channel_status(email, EMAIL_PROVIDERS, channel="email"),
        "sms": _channel_status(sms, SMS_PROVIDERS, channel="sms"),
        "whatsapp": _channel_status(whatsapp, WHATSAPP_PROVIDERS, channel="whatsapp"),
    }
    return {
        "live_dispatch": bool(getattr(settings, "INTEGRATION_LIVE_DISPATCH", False)),
        "channels": channels,
        "smtp_diagnostic": smtp_diagnostic,
        "notes": (
            "Broadcasts validate recipients, build provider payloads, and log deliveries. "
            "Outbound messages return failed until INTEGRATION_LIVE_DISPATCH=true and "
            "provider HTTP dispatch is connected at deployment."
        ),
    }