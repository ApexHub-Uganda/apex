"""Payment gateway architecture — adapters ready; live network calls postponed."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


GATEWAY_NOT_CONFIGURED = (
    "Payment Failed\n"
    "Reason:\n"
    "Payment integrations will be enabled in a future release."
)

GATEWAY_NOT_CONFIGURED_CODE = "gateway_not_configured"


@dataclass
class GatewayResult:
    success: bool
    code: str
    message: str
    external_reference: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class PaymentGatewayAdapter(ABC):
    slug: str = "base"
    display_name: str = "Payment Gateway"

    @abstractmethod
    def initiate_payment(self, *, amount, currency: str, reference: str, metadata: dict) -> GatewayResult:
        ...

    @abstractmethod
    def verify_payment(self, *, external_reference: str) -> GatewayResult:
        ...

    @abstractmethod
    def parse_webhook(self, *, headers: dict, body: bytes) -> GatewayResult:
        ...


class NotConfiguredGateway(PaymentGatewayAdapter):
    """Production-ready stub used until providers are enabled."""

    slug = "not_configured"
    display_name = "Not Configured"

    def initiate_payment(self, *, amount, currency: str, reference: str, metadata: dict) -> GatewayResult:
        return GatewayResult(
            success=False,
            code=GATEWAY_NOT_CONFIGURED_CODE,
            message=GATEWAY_NOT_CONFIGURED,
            external_reference=reference,
            raw={"amount": str(amount), "currency": currency, "metadata": metadata},
        )

    def verify_payment(self, *, external_reference: str) -> GatewayResult:
        return GatewayResult(
            success=False,
            code=GATEWAY_NOT_CONFIGURED_CODE,
            message=GATEWAY_NOT_CONFIGURED,
            external_reference=external_reference,
        )

    def parse_webhook(self, *, headers: dict, body: bytes) -> GatewayResult:
        return GatewayResult(
            success=False,
            code=GATEWAY_NOT_CONFIGURED_CODE,
            message=GATEWAY_NOT_CONFIGURED,
        )


# Named stubs for future provider wiring (no network I/O)
class MpesaStubGateway(NotConfiguredGateway):
    slug = "mpesa"
    display_name = "M-Pesa"


class FlutterwaveStubGateway(NotConfiguredGateway):
    slug = "flutterwave"
    display_name = "Flutterwave"


class StripeStubGateway(NotConfiguredGateway):
    slug = "stripe"
    display_name = "Stripe"


class PesapalStubGateway(NotConfiguredGateway):
    slug = "pesapal"
    display_name = "Pesapal"


_REGISTRY: dict[str, PaymentGatewayAdapter] = {
    "not_configured": NotConfiguredGateway(),
    "mpesa": MpesaStubGateway(),
    "flutterwave": FlutterwaveStubGateway(),
    "stripe": StripeStubGateway(),
    "pesapal": PesapalStubGateway(),
    "card": StripeStubGateway(),
}


def get_gateway(slug: str | None = None) -> PaymentGatewayAdapter:
    if not slug:
        return _REGISTRY["not_configured"]
    return _REGISTRY.get(slug, _REGISTRY["not_configured"])


def list_gateways() -> list[dict[str, Any]]:
    return [
        {
            "slug": g.slug,
            "name": g.display_name,
            "is_configured": False,
            "status": "not_available",
            "message": "Payment gateway not yet configured.",
        }
        for g in _REGISTRY.values()
        if g.slug != "not_configured"
    ]
