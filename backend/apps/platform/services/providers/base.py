"""Shared types and helpers for outbound messaging providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from django.conf import settings


@dataclass
class ProviderRequest:
    """Fully-built provider payload ready for HTTP / SMTP dispatch."""

    provider: str
    endpoint: str
    method: str
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] = field(default_factory=dict)
    auth: Optional[tuple[str, str]] = None


@dataclass
class ProviderResponse:
    success: bool
    message: str
    external_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseMessagingProvider(ABC):
    """Provider adapter — validates config, builds requests, dispatches when live."""

    provider_slug: str = ""

    @abstractmethod
    def validate_config(self, config) -> list[str]:
        """Return a list of missing/invalid configuration field messages."""

    @abstractmethod
    def build_request(
        self,
        config,
        *,
        to: str,
        subject: str,
        message: str,
        html_body: str = "",
    ) -> ProviderRequest:
        """Build the exact outbound request that will be sent in production."""

    def dispatch(
        self,
        config,
        *,
        to: str,
        subject: str,
        message: str,
        html_body: str = "",
    ) -> ProviderResponse:
        errors = self.validate_config(config)
        if errors:
            return ProviderResponse(
                success=False,
                message=f"{self.provider_slug} is not fully configured: {'; '.join(errors)}",
                metadata={"validation_errors": errors, "provider": self.provider_slug},
            )

        request = self.build_request(
            config, to=to, subject=subject, message=message, html_body=html_body,
        )
        metadata = {
            "provider": self.provider_slug,
            "endpoint": request.endpoint,
            "method": request.method,
            "request_body": request.body,
            "request_headers": {k: v for k, v in request.headers.items() if k.lower() != "authorization"},
        }

        if not getattr(settings, "INTEGRATION_LIVE_DISPATCH", False):
            return ProviderResponse(
                success=False,
                message=(
                    f"{self.provider_slug} request prepared but live dispatch is disabled. "
                    "Set INTEGRATION_LIVE_DISPATCH=true and connect provider credentials at deployment."
                ),
                metadata={
                    **metadata,
                    "live_dispatch": False,
                    "deployment_ready": True,
                },
            )

        return self.dispatch_live(
            config, request, to=to, subject=subject, message=message, html_body=html_body,
        )

    @abstractmethod
    def dispatch_live(
        self,
        config,
        request: ProviderRequest,
        *,
        to: str,
        subject: str,
        message: str,
        html_body: str = "",
    ) -> ProviderResponse:
        """Execute the provider API call. Only invoked when INTEGRATION_LIVE_DISPATCH=true."""


def normalize_phone_e164(phone: str, *, default_region: str = "") -> str:
    """Normalize a phone number to E.164 where possible."""
    raw = (phone or "").strip()
    if not raw:
        return ""
    cleaned = "".join(ch for ch in raw if ch.isdigit() or ch == "+")
    if cleaned.startswith("+"):
        return cleaned
    if cleaned.startswith("00"):
        return f"+{cleaned[2:]}"
    if default_region and not cleaned.startswith("0"):
        return f"+{default_region}{cleaned}"
    if cleaned.startswith("0") and len(cleaned) > 1:
        return f"+{cleaned[1:]}" if default_region else f"+{cleaned}"
    return f"+{cleaned}" if cleaned else ""