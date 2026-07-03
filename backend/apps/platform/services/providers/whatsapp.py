"""WhatsApp Business API provider adapters (Meta Cloud API, Twilio)."""
from __future__ import annotations

from apps.platform.services.providers.base import (
    BaseMessagingProvider,
    ProviderRequest,
    ProviderResponse,
    normalize_phone_e164,
)


class MetaWhatsAppProvider(BaseMessagingProvider):
    provider_slug = "meta"

    def validate_config(self, config) -> list[str]:
        errors = []
        if not config.api_key:
            errors.append("access_token (api_key)")
        if not config.phone_number_id:
            errors.append("phone_number_id")
        return errors

    def build_request(self, config, *, to: str, subject: str, message: str) -> ProviderRequest:
        to_e164 = normalize_phone_e164(to).lstrip("+")
        endpoint = f"https://graph.facebook.com/v19.0/{config.phone_number_id}/messages"
        return ProviderRequest(
            provider=self.provider_slug,
            endpoint=endpoint,
            method="POST",
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            body={
                "messaging_product": "whatsapp",
                "to": to_e164,
                "type": "text",
                "text": {"preview_url": False, "body": message},
            },
        )

    def dispatch_live(
        self,
        config,
        request: ProviderRequest,
        *,
        to: str,
        subject: str,
        message: str,
    ) -> ProviderResponse:
        return ProviderResponse(
            success=False,
            message=(
                "Meta WhatsApp Cloud API live HTTP dispatch is not wired yet. "
                "Implement POST to the prepared endpoint in providers/whatsapp.py."
            ),
            metadata={"provider": self.provider_slug, "endpoint": request.endpoint, "request_body": request.body},
        )


class TwilioWhatsAppProvider(BaseMessagingProvider):
    provider_slug = "twilio"

    def validate_config(self, config) -> list[str]:
        errors = []
        if not config.api_key:
            errors.append("account_sid (api_key)")
        if not config.api_secret:
            errors.append("auth_token (api_secret)")
        if not config.phone_number_id:
            errors.append("whatsapp_from (phone_number_id)")
        return errors

    def build_request(self, config, *, to: str, subject: str, message: str) -> ProviderRequest:
        to_addr = f"whatsapp:{normalize_phone_e164(to)}"
        from_addr = f"whatsapp:{config.phone_number_id}"
        endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{config.api_key}/Messages.json"
        return ProviderRequest(
            provider=self.provider_slug,
            endpoint=endpoint,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=(config.api_key, config.api_secret),
            body={
                "To": to_addr,
                "From": from_addr,
                "Body": message,
            },
        )

    def dispatch_live(
        self,
        config,
        request: ProviderRequest,
        *,
        to: str,
        subject: str,
        message: str,
    ) -> ProviderResponse:
        return ProviderResponse(
            success=False,
            message=(
                "Twilio WhatsApp live HTTP dispatch is not wired yet. "
                "Implement POST to the prepared endpoint in providers/whatsapp.py."
            ),
            metadata={"provider": self.provider_slug, "endpoint": request.endpoint, "request_body": request.body},
        )


class AfricasTalkingWhatsAppProvider(BaseMessagingProvider):
    provider_slug = "africas_talking"

    def validate_config(self, config) -> list[str]:
        errors = []
        if not config.api_key:
            errors.append("api_key")
        if not config.phone_number_id:
            errors.append("channel_number (phone_number_id)")
        return errors

    def build_request(self, config, *, to: str, subject: str, message: str) -> ProviderRequest:
        return ProviderRequest(
            provider=self.provider_slug,
            endpoint="https://chatapi.africastalking.com/whatsapp/message",
            method="POST",
            headers={
                "apiKey": config.api_key,
                "Content-Type": "application/json",
            },
            body={
                "to": normalize_phone_e164(to),
                "from": config.phone_number_id,
                "message": message,
            },
        )

    def dispatch_live(
        self,
        config,
        request: ProviderRequest,
        *,
        to: str,
        subject: str,
        message: str,
    ) -> ProviderResponse:
        return ProviderResponse(
            success=False,
            message=(
                "Africa's Talking WhatsApp live HTTP dispatch is not wired yet. "
                "Implement POST to the prepared endpoint in providers/whatsapp.py."
            ),
            metadata={"provider": self.provider_slug, "endpoint": request.endpoint, "request_body": request.body},
        )