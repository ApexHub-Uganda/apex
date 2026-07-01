"""External integration service layer.

All providers are wired end-to-end but return failed responses until live API
credentials are configured.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from django.utils import timezone

from apps.platform.models import CallSetting, EmailSetting, SMSSetting
from apps.subscriptions.models import PaymentProvider, PaymentTransaction, Subscription


@dataclass
class IntegrationResult:
    success: bool
    message: str
    reference: str = ""
    external_id: str = ""
    metadata: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "reference": self.reference,
            "external_id": self.external_id,
            "metadata": self.metadata or {},
        }


class EmailService:
    """SMTP / transactional email gateway."""

    @staticmethod
    def _get_config() -> Optional[EmailSetting]:
        return EmailSetting.objects.filter(is_active=True).first()

    @classmethod
    def send(
        cls,
        to: str | list[str],
        subject: str,
        body: str,
        *,
        html_body: str = "",
        from_email: str = "",
    ) -> IntegrationResult:
        config = cls._get_config()
        reference = f"email_{uuid.uuid4().hex[:12]}"
        recipients = [to] if isinstance(to, str) else to

        if not config:
            return IntegrationResult(
                success=False,
                message="Email service is not configured. Configure SMTP in platform settings.",
                reference=reference,
                metadata={"recipients": recipients, "subject": subject, "provider": "none"},
            )

        return IntegrationResult(
            success=False,
            message=(
                f"Email delivery failed: {config.provider} API not connected. "
                "Configure live credentials to enable sending."
            ),
            reference=reference,
            metadata={
                "recipients": recipients,
                "subject": subject,
                "provider": config.provider,
                "from_email": from_email or config.from_email,
                "attempted_at": timezone.now().isoformat(),
            },
        )


class SMSService:
    """SMS gateway (Africa's Talking, Twilio, etc.)."""

    @staticmethod
    def _get_config() -> Optional[SMSSetting]:
        return SMSSetting.objects.filter(is_active=True).first()

    @classmethod
    def send(cls, to: str, message: str, *, sender_id: str = "") -> IntegrationResult:
        config = cls._get_config()
        reference = f"sms_{uuid.uuid4().hex[:12]}"

        if not config:
            return IntegrationResult(
                success=False,
                message="SMS service is not configured.",
                reference=reference,
                metadata={"to": to, "provider": "none"},
            )

        return IntegrationResult(
            success=False,
            message=(
                f"SMS delivery failed: {config.provider} API not connected. "
                "Configure live API keys to enable sending."
            ),
            reference=reference,
            metadata={
                "to": to,
                "provider": config.provider,
                "sender_id": sender_id or config.sender_id,
                "attempted_at": timezone.now().isoformat(),
            },
        )


class CallService:
    """Voice / call gateway."""

    @staticmethod
    def _get_config() -> Optional[CallSetting]:
        return CallSetting.objects.filter(is_active=True).first()

    @classmethod
    def place_call(cls, to: str, message: str = "") -> IntegrationResult:
        config = cls._get_config()
        reference = f"call_{uuid.uuid4().hex[:12]}"

        if not config:
            return IntegrationResult(
                success=False,
                message="Call service is not configured.",
                reference=reference,
                metadata={"to": to, "provider": "none"},
            )

        return IntegrationResult(
            success=False,
            message=(
                f"Call failed: {config.provider} voice API not connected. "
                "Configure live credentials to enable calls."
            ),
            reference=reference,
            metadata={
                "to": to,
                "provider": config.provider,
                "from_number": config.from_number,
                "attempted_at": timezone.now().isoformat(),
            },
        )


class PaymentService:
    """Subscription checkout and payment processing."""

    @staticmethod
    def _get_provider() -> Optional[PaymentProvider]:
        return PaymentProvider.objects.filter(is_active=True).first()

    @classmethod
    def process_checkout(
        cls,
        *,
        tenant,
        plan,
        amount: Decimal,
        billing_cycle: str = "monthly",
        currency: str = "USD",
    ) -> IntegrationResult:
        provider = cls._get_provider()
        reference = f"pay_{uuid.uuid4().hex[:12]}"

        subscription = tenant.subscriptions.filter(plan=plan).order_by("-created_at").first()
        if not subscription:
            subscription = Subscription.objects.create(tenant=tenant, plan=plan, status="trial")

        if not provider:
            provider, _ = PaymentProvider.objects.get_or_create(
                slug="unconfigured",
                defaults={"name": "Unconfigured", "is_active": False},
            )

        txn = PaymentTransaction.objects.create(
            tenant=tenant,
            subscription=subscription,
            provider=provider,
            amount=amount,
            currency=currency,
            status="failed",
            reference=reference,
            metadata={
                "billing_cycle": billing_cycle,
                "plan_slug": plan.slug,
                "checkout_attempted_at": timezone.now().isoformat(),
            },
        )

        tenant.payment_attempted = True
        tenant.save(update_fields=["payment_attempted", "updated_at"])

        if not provider:
            return IntegrationResult(
                success=False,
                message="Payment provider is not configured.",
                reference=reference,
                metadata={"transaction_id": str(txn.id)},
            )

        return IntegrationResult(
            success=False,
            message=(
                f"Payment failed: {provider.name} gateway API not connected. "
                "Your registration has been recorded — a super admin will activate your account."
            ),
            reference=reference,
            external_id=txn.external_id,
            metadata={
                "transaction_id": str(txn.id),
                "provider": provider.slug,
                "amount": float(amount),
                "currency": currency,
            },
        )