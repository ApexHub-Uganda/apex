"""External integration service layer.

Messaging providers validate configuration, build deployment-ready API payloads,
and dispatch only when INTEGRATION_LIVE_DISPATCH=true. Until then, broadcasts
complete the full pipeline but mark channel deliveries as failed.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

from django.utils import timezone

from apps.platform.models import CallSetting, EmailSetting, SMSSetting, WhatsAppSetting
from apps.platform.services.providers.base import ProviderResponse
from apps.platform.services.providers.registry import (
    get_email_provider,
    get_sms_provider,
    get_whatsapp_provider,
)
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


def _from_provider_response(response: ProviderResponse, *, reference: str) -> IntegrationResult:
    return IntegrationResult(
        success=response.success,
        message=response.message,
        reference=reference,
        external_id=response.external_id,
        metadata=response.metadata,
    )


def _log_email_attempt(*, to: str, subject: str, body: str, result: IntegrationResult, tenant=None):
    from apps.communication.models import EmailMessage

    EmailMessage.objects.create(
        tenant=tenant,
        recipient_email=to,
        subject=subject,
        body=body,
        status="sent" if result.success else "failed",
        sent_at=timezone.now() if result.success else None,
    )


def _log_sms_attempt(*, to: str, message: str, result: IntegrationResult, tenant=None):
    from apps.communication.models import SMSMessage

    SMSMessage.objects.create(
        tenant=tenant,
        recipient_phone=to,
        message=message,
        status="sent" if result.success else "failed",
        sent_at=timezone.now() if result.success else None,
        provider_response=result.metadata or {},
    )


class EmailService:
    """SMTP / transactional email gateway."""

    @staticmethod
    def _get_config() -> Optional[EmailSetting]:
        from apps.platform.services.email_config import ensure_email_config

        return ensure_email_config()

    @classmethod
    def send(
        cls,
        to: str | list[str],
        subject: str,
        body: str,
        *,
        html_body: str = "",
        from_email: str = "",
        tenant=None,
        log_attempt: bool = True,
    ) -> IntegrationResult:
        reference = f"email_{uuid.uuid4().hex[:12]}"
        recipients = [addr.strip() for addr in ([to] if isinstance(to, str) else to) if (addr or "").strip()]

        config = cls._get_config()
        if not config:
            result = IntegrationResult(
                success=False,
                message="Email service is not configured. Add an active record in Platform → Email settings.",
                reference=reference,
                metadata={"recipients": recipients, "subject": subject, "provider": "none"},
            )
            if log_attempt and recipients:
                for recipient in recipients:
                    _log_email_attempt(
                        to=recipient, subject=subject, body=body, result=result, tenant=tenant,
                    )
            return result

        adapter = get_email_provider(config.provider)
        sender = from_email or config.from_email
        delivery_results: list[dict[str, Any]] = []
        sent_count = 0
        failed_count = 0

        for recipient in recipients:
            response = adapter.dispatch(
                config,
                to=recipient,
                subject=subject,
                message=body,
                html_body=html_body,
            )
            item = _from_provider_response(response, reference=reference)
            item.metadata = {
                **(item.metadata or {}),
                "recipient": recipient,
                "subject": subject,
                "from_email": sender,
                "attempted_at": timezone.now().isoformat(),
            }
            delivery_results.append(item.to_dict())
            if item.success:
                sent_count += 1
            else:
                failed_count += 1
            if log_attempt:
                _log_email_attempt(
                    to=recipient, subject=subject, body=body, result=item, tenant=tenant,
                )

        if not recipients:
            return IntegrationResult(
                success=False,
                message="No email recipients provided.",
                reference=reference,
                metadata={"recipients": [], "subject": subject, "provider": config.provider},
            )

        all_sent = sent_count == len(recipients)
        any_sent = sent_count > 0
        if all_sent:
            message = f"Email delivered to {sent_count} recipient(s)."
        elif any_sent:
            message = f"Email delivered to {sent_count} of {len(recipients)} recipient(s); {failed_count} failed."
        else:
            message = delivery_results[0]["message"] if delivery_results else "Email delivery failed."

        return IntegrationResult(
            success=all_sent,
            message=message,
            reference=reference,
            metadata={
                "recipients": recipients,
                "subject": subject,
                "from_email": sender,
                "provider": config.provider,
                "sent_count": sent_count,
                "failed_count": failed_count,
                "deliveries": delivery_results,
                "attempted_at": timezone.now().isoformat(),
            },
        )


class SMSService:
    """SMS gateway (Africa's Talking, Twilio, etc.)."""

    @staticmethod
    def _get_config() -> Optional[SMSSetting]:
        return SMSSetting.objects.filter(is_active=True).first()

    @classmethod
    def send(cls, to: str, message: str, *, sender_id: str = "", tenant=None) -> IntegrationResult:
        reference = f"sms_{uuid.uuid4().hex[:12]}"
        config = cls._get_config()
        if not config:
            result = IntegrationResult(
                success=False,
                message="SMS service is not configured. Add an active record in Platform → SMS settings.",
                reference=reference,
                metadata={"to": to, "provider": "none"},
            )
            _log_sms_attempt(to=to, message=message, result=result, tenant=tenant)
            return result

        adapter = get_sms_provider(config.provider)
        response = adapter.dispatch(config, to=to, subject="", message=message)
        result = _from_provider_response(response, reference=reference)
        result.metadata = {
            **(result.metadata or {}),
            "to": to,
            "sender_id": sender_id or config.sender_id,
            "attempted_at": timezone.now().isoformat(),
        }
        _log_sms_attempt(to=to, message=message, result=result, tenant=tenant)
        return result


class WhatsAppService:
    """WhatsApp Business API gateway."""

    @staticmethod
    def _get_config() -> Optional[WhatsAppSetting]:
        return WhatsAppSetting.objects.filter(is_active=True).first()

    @classmethod
    def send(cls, to: str, message: str, *, tenant=None) -> IntegrationResult:
        reference = f"whatsapp_{uuid.uuid4().hex[:12]}"
        config = cls._get_config()
        if not config:
            return IntegrationResult(
                success=False,
                message="WhatsApp service is not configured. Add an active record in Platform → WhatsApp settings.",
                reference=reference,
                metadata={"to": to, "provider": "none"},
            )

        adapter = get_whatsapp_provider(config.provider)
        response = adapter.dispatch(config, to=to, subject="", message=message)
        result = _from_provider_response(response, reference=reference)
        result.metadata = {
            **(result.metadata or {}),
            "to": to,
            "attempted_at": timezone.now().isoformat(),
        }
        return result


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

    CARD_PROVIDER_SLUGS = ("stripe", "paypal")
    MOBILE_PROVIDER_SLUGS = ("mpesa", "mtn_momo", "airtel_money")

    @classmethod
    def _resolve_provider(
        cls,
        *,
        payment_method: str,
        provider_slug: str = "",
    ) -> PaymentProvider:
        from apps.core.constants import PaymentMethodType

        method = payment_method or PaymentMethodType.CARD
        if provider_slug:
            provider = PaymentProvider.objects.filter(slug=provider_slug).first()
            if provider:
                return provider

        preferred_slugs = (
            cls.MOBILE_PROVIDER_SLUGS
            if method == PaymentMethodType.MOBILE_MONEY
            else cls.CARD_PROVIDER_SLUGS
        )
        for slug in preferred_slugs:
            provider = PaymentProvider.objects.filter(slug=slug).first()
            if provider:
                return provider

        provider = (
            PaymentProvider.objects.filter(method_type=method, is_active=True).first()
            or PaymentProvider.objects.filter(method_type=method).first()
            or PaymentProvider.objects.filter(is_active=True).first()
        )
        if provider:
            return provider

        defaults = {
            PaymentMethodType.MOBILE_MONEY: {
                "slug": "mpesa",
                "name": "M-Pesa",
                "method_type": PaymentMethodType.MOBILE_MONEY,
            },
            PaymentMethodType.CARD: {
                "slug": "stripe",
                "name": "Stripe",
                "method_type": PaymentMethodType.CARD,
            },
        }
        cfg = defaults[method]
        provider, _ = PaymentProvider.objects.get_or_create(
            slug=cfg["slug"],
            defaults={
                "name": cfg["name"],
                "method_type": cfg["method_type"],
                "is_active": False,
                "is_sandbox": True,
            },
        )
        return provider

    @classmethod
    def process_checkout(
        cls,
        *,
        tenant,
        plan,
        amount: Decimal,
        billing_cycle: str = "monthly",
        currency: str = "USD",
        payment_method: str = "card",
        provider_slug: str = "",
        phone_number: str = "",
        card_last_four: str = "",
        card_brand: str = "",
        payer_name: str = "",
    ) -> IntegrationResult:
        from apps.core.constants import PaymentMethodType
        from apps.subscriptions.payment_utils import (
            mask_phone,
            normalize_payment_method,
            validate_checkout_details,
        )

        method = normalize_payment_method(payment_method)
        validate_checkout_details(
            payment_method=method,
            phone_number=phone_number,
            card_last_four=card_last_four,
            payer_name=payer_name,
        )

        provider = cls._resolve_provider(payment_method=method, provider_slug=provider_slug)
        reference = f"pay_{uuid.uuid4().hex[:12]}"
        masked_phone = mask_phone(phone_number) if method == PaymentMethodType.MOBILE_MONEY else ""

        subscription = tenant.subscriptions.filter(plan=plan).order_by("-created_at").first()
        if not subscription:
            subscription = Subscription.objects.create(tenant=tenant, plan=plan, status="trial")

        txn_metadata = {
            "billing_cycle": billing_cycle,
            "plan_slug": plan.slug,
            "checkout_attempted_at": timezone.now().isoformat(),
            "payment_method": method,
        }
        if method == PaymentMethodType.CARD:
            txn_metadata.update({
                "card_last_four": card_last_four,
                "card_brand": card_brand or "card",
                "payer_name": payer_name.strip(),
            })
        else:
            txn_metadata.update({
                "phone_masked": masked_phone,
                "phone_submitted": True,
            })

        txn = PaymentTransaction.objects.create(
            tenant=tenant,
            subscription=subscription,
            provider=provider,
            amount=amount,
            currency=currency,
            status="failed",
            reference=reference,
            payment_method=method,
            payer_phone=masked_phone,
            metadata=txn_metadata,
        )

        tenant.payment_attempted = True
        tenant.save(update_fields=["payment_attempted", "updated_at"])

        if method == PaymentMethodType.MOBILE_MONEY:
            message = (
                f"Mobile money payment could not be completed: {provider.name} is not yet available. "
                f"We recorded your request for {masked_phone or 'the submitted number'}. "
                "A super admin will follow up once mobile money checkout is enabled."
            )
        else:
            ending = f" ending in {card_last_four}" if card_last_four else ""
            message = (
                f"Card payment failed: {provider.name} gateway API not connected{ending}. "
                "Your request has been recorded — a super admin will activate your account after verification."
            )

        return IntegrationResult(
            success=False,
            message=message,
            reference=reference,
            external_id=txn.external_id,
            metadata={
                "transaction_id": str(txn.id),
                "provider": provider.slug,
                "payment_method": method,
                "amount": float(amount),
                "currency": currency,
                "payer_phone": masked_phone,
                "card_last_four": card_last_four,
            },
        )