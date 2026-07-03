"""SMS provider adapters (Twilio, Africa's Talking, Nexmo/Vonage)."""
from __future__ import annotations

from apps.platform.services.providers.base import (
    BaseMessagingProvider,
    ProviderRequest,
    ProviderResponse,
    normalize_phone_e164,
)


class TwilioSmsProvider(BaseMessagingProvider):
    provider_slug = "twilio"

    def validate_config(self, config) -> list[str]:
        errors = []
        if not config.api_key:
            errors.append("account_sid (api_key)")
        if not config.api_secret:
            errors.append("auth_token (api_secret)")
        if not config.sender_id:
            errors.append("from_number (sender_id)")
        return errors

    def build_request(self, config, *, to: str, subject: str, message: str) -> ProviderRequest:
        to_e164 = normalize_phone_e164(to)
        endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{config.api_key}/Messages.json"
        return ProviderRequest(
            provider=self.provider_slug,
            endpoint=endpoint,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=(config.api_key, config.api_secret),
            body={
                "To": to_e164,
                "From": config.sender_id,
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
                "Twilio SMS live HTTP dispatch is not wired yet. "
                "Implement POST to the prepared endpoint in providers/sms.py."
            ),
            metadata={"provider": self.provider_slug, "endpoint": request.endpoint, "request_body": request.body},
        )


class AfricasTalkingSmsProvider(BaseMessagingProvider):
    provider_slug = "africas_talking"

    def validate_config(self, config) -> list[str]:
        errors = []
        if not config.api_key:
            errors.append("api_key")
        if not config.sender_id:
            errors.append("sender_id")
        return errors

    def build_request(self, config, *, to: str, subject: str, message: str) -> ProviderRequest:
        return ProviderRequest(
            provider=self.provider_slug,
            endpoint="https://api.africastalking.com/version1/messaging",
            method="POST",
            headers={
                "apiKey": config.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            body={
                "username": config.api_secret or "sandbox",
                "to": normalize_phone_e164(to),
                "message": message,
                "from": config.sender_id,
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
                "Africa's Talking SMS live HTTP dispatch is not wired yet. "
                "Implement POST to the prepared endpoint in providers/sms.py."
            ),
            metadata={"provider": self.provider_slug, "endpoint": request.endpoint, "request_body": request.body},
        )


class NexmoSmsProvider(BaseMessagingProvider):
    provider_slug = "nexmo"

    def validate_config(self, config) -> list[str]:
        errors = []
        if not config.api_key:
            errors.append("api_key")
        if not config.api_secret:
            errors.append("api_secret")
        if not config.sender_id:
            errors.append("sender_id")
        return errors

    def build_request(self, config, *, to: str, subject: str, message: str) -> ProviderRequest:
        return ProviderRequest(
            provider=self.provider_slug,
            endpoint="https://rest.nexmo.com/sms/json",
            method="POST",
            headers={"Content-Type": "application/json"},
            body={
                "api_key": config.api_key,
                "api_secret": config.api_secret,
                "to": normalize_phone_e164(to),
                "from": config.sender_id,
                "text": message,
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
                "Vonage/Nexmo SMS live HTTP dispatch is not wired yet. "
                "Implement POST to the prepared endpoint in providers/sms.py."
            ),
            metadata={"provider": self.provider_slug, "endpoint": request.endpoint, "request_body": request.body},
        )