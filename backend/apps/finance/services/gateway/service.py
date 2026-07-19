"""Gateway payment intents + webhook intake (no live providers)."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.finance.services.finance_audit import log_finance_action
from apps.finance.services.gateway import GATEWAY_NOT_CONFIGURED, get_gateway, list_gateways
from apps.finance.services.numbering import generate_payment_reference


@transaction.atomic
def initiate_online_payment(*, tenant, user, payload: dict, request=None) -> dict:
    """
    Create an online payment attempt and return a graceful not-configured failure.

    Architecture is production-ready; only external HTTP is deferred.
    """
    amount = Decimal(str(payload.get("amount") or 0))
    if amount <= 0:
        return {
            "success": False,
            "code": "invalid_amount",
            "message": "Amount must be greater than zero.",
        }

    gateway_slug = payload.get("gateway") or "mpesa"
    gateway = get_gateway(gateway_slug)
    reference = generate_payment_reference(tenant=tenant, channel=gateway_slug[:3])

    # Persist intent when PaymentIntent model exists
    intent_id = None
    try:
        from apps.finance.models import PaymentIntent
        intent = PaymentIntent.objects.create(
            tenant=tenant,
            student_id=payload.get("student"),
            amount=amount,
            currency=payload.get("currency") or "UGX",
            gateway=gateway.slug,
            reference=reference,
            status="failed",
            failure_message=GATEWAY_NOT_CONFIGURED,
            metadata=payload.get("metadata") or {},
            created_by=user,
            updated_by=user,
        )
        intent_id = str(intent.id)
    except Exception:
        intent_id = None

    result = gateway.initiate_payment(
        amount=amount,
        currency=payload.get("currency") or "UGX",
        reference=reference,
        metadata={"student": payload.get("student"), "user": str(getattr(user, "id", ""))},
    )

    log_finance_action(
        tenant=tenant,
        user=user,
        action="online_payment_attempt",
        resource_type="PaymentIntent",
        resource_id=intent_id or reference,
        description="Online payment blocked — gateway not configured",
        changes={"gateway": gateway.slug, "amount": str(amount), "reference": reference},
        request=request,
    )

    return {
        "success": False,
        "code": result.code,
        "message": result.message,
        "reference": reference,
        "intent_id": intent_id,
        "gateway": gateway.slug,
        "gateways": list_gateways(),
        "recorded_at": timezone.now().isoformat(),
    }


def handle_gateway_webhook(*, tenant, gateway_slug: str, headers: dict, body: bytes, request=None) -> dict:
    gateway = get_gateway(gateway_slug)
    result = gateway.parse_webhook(headers=headers, body=body)
    try:
        from apps.finance.models import PaymentWebhookEvent
        PaymentWebhookEvent.objects.create(
            tenant=tenant,
            gateway=gateway.slug,
            payload_headers={k: str(v)[:200] for k, v in (headers or {}).items()},
            payload_body=(body or b"")[:8000].decode("utf-8", errors="replace"),
            processing_status="ignored",
            result_code=result.code,
            result_message=result.message[:500],
        )
    except Exception:
        pass
    return {
        "success": False,
        "code": result.code,
        "message": result.message,
    }
