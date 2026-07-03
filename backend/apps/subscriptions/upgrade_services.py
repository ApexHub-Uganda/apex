"""School-admin self-service plan upgrade catalog and checkout (stub payment)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.platform.services.integrations import PaymentService
from apps.platform.services.plan_advertisements import (
    DEFAULT_UPGRADE,
    get_upgrade_options,
    is_top_tier_plan,
    normalize_plan_slug,
)
from apps.subscriptions.models import PaymentProvider, Plan
from apps.subscriptions.plan_tiers import get_plan_feature_breakdown


def _serialize_plan(plan: Plan, *, recommended: bool = False) -> dict[str, Any]:
    features_qs = (
        plan.features.filter(is_active=True)
        .select_related("category")
        .order_by("category__sort_order", "sort_order")
    )
    categories: dict[str, list[dict[str, str]]] = {}
    for feature in features_qs:
        cat_name = feature.category.name if feature.category else "General"
        categories.setdefault(cat_name, []).append({
            "feature_key": feature.feature_key,
            "name": feature.feature_name,
            "description": feature.description or "",
        })

    breakdown = get_plan_feature_breakdown(plan)
    return {
        "id": str(plan.id),
        "slug": plan.slug,
        "name": plan.name,
        "description": plan.description or "",
        "price_monthly": float(plan.price_monthly),
        "price_yearly": float(plan.price_yearly),
        "currency": plan.currency or "USD",
        "max_students": plan.max_students,
        "max_staff": plan.max_staff,
        "max_branches": plan.max_branches,
        "trial_days": plan.trial_days,
        "feature_count": features_qs.count(),
        "feature_categories": [
            {"name": name, "features": items}
            for name, items in categories.items()
        ],
        "module_highlights": [f.feature_name for f in features_qs[:10]],
        "recommended": recommended,
        "inherits_from_slug": breakdown["inherits_from_slug"],
        "inherits_from_label": breakdown["inherits_from_label"],
        "inherited_summary": breakdown["inherited_summary"],
        "inherited_feature_count": breakdown["inherited_feature_count"],
        "exclusive_feature_count": breakdown["exclusive_feature_count"],
        "exclusive_feature_categories": breakdown["exclusive_feature_categories"],
    }


def _default_payment_methods_payload() -> list[dict[str, Any]]:
    from apps.core.constants import PaymentMethodType

    return [
        {
            "type": PaymentMethodType.CARD,
            "label": "Credit or Debit Card",
            "description": "Pay with Visa, Mastercard, or Amex",
            "default": True,
            "providers": [
                {"slug": "stripe", "name": "Stripe", "is_sandbox": True, "is_active": False, "status": "not_connected"},
                {"slug": "paypal", "name": "PayPal", "is_sandbox": True, "is_active": False, "status": "not_connected"},
            ],
        },
        {
            "type": PaymentMethodType.MOBILE_MONEY,
            "label": "Mobile Money",
            "description": "Pay with M-Pesa, MTN MoMo, or Airtel Money",
            "default": False,
            "providers": [
                {"slug": "mpesa", "name": "M-Pesa", "is_sandbox": True, "is_active": False, "status": "not_available"},
                {"slug": "mtn_momo", "name": "MTN MoMo", "is_sandbox": True, "is_active": False, "status": "not_available"},
                {"slug": "airtel_money", "name": "Airtel Money", "is_sandbox": True, "is_active": False, "status": "not_available"},
            ],
        },
    ]


def _payment_methods_payload() -> list[dict[str, Any]]:
    from django.db import DatabaseError

    from apps.core.constants import PaymentMethodType

    try:
        providers = list(PaymentProvider.objects.order_by("method_type", "-is_active", "name"))
    except DatabaseError:
        return _default_payment_methods_payload()

    card_providers = [p for p in providers if p.method_type == PaymentMethodType.CARD]
    mobile_providers = [p for p in providers if p.method_type == PaymentMethodType.MOBILE_MONEY]

    if not card_providers:
        card_providers_data = [
            {"slug": "stripe", "name": "Stripe", "is_sandbox": True, "is_active": False, "status": "not_connected"},
            {"slug": "paypal", "name": "PayPal", "is_sandbox": True, "is_active": False, "status": "not_connected"},
        ]
    else:
        card_providers_data = [
            {
                "slug": p.slug,
                "name": p.name,
                "is_sandbox": p.is_sandbox,
                "is_active": p.is_active,
                "status": "not_connected",
            }
            for p in card_providers
        ]

    if not mobile_providers:
        mobile_providers_data = [
            {"slug": "mpesa", "name": "M-Pesa", "is_sandbox": True, "is_active": False, "status": "not_available"},
            {"slug": "mtn_momo", "name": "MTN MoMo", "is_sandbox": True, "is_active": False, "status": "not_available"},
            {"slug": "airtel_money", "name": "Airtel Money", "is_sandbox": True, "is_active": False, "status": "not_available"},
        ]
    else:
        mobile_providers_data = [
            {
                "slug": p.slug,
                "name": p.name,
                "is_sandbox": p.is_sandbox,
                "is_active": p.is_active,
                "status": "not_available",
            }
            for p in mobile_providers
        ]

    return [
        {
            "type": PaymentMethodType.CARD,
            "label": "Credit or Debit Card",
            "description": "Pay with Visa, Mastercard, or Amex",
            "default": True,
            "providers": card_providers_data,
        },
        {
            "type": PaymentMethodType.MOBILE_MONEY,
            "label": "Mobile Money",
            "description": "Pay with M-Pesa, MTN MoMo, or Airtel Money",
            "default": False,
            "providers": mobile_providers_data,
        },
    ]


def _upgrade_plan_queryset():
    """Active plans eligible for school-admin self-service upgrades."""
    return Plan.objects.filter(is_active=True)


def get_upgrade_catalog(tenant) -> dict[str, Any]:
    """Plans available for upgrade plus current subscription context."""
    sub = tenant.active_subscription
    current_slug = normalize_plan_slug(sub.plan.slug) if sub and sub.plan else None
    current_plan = None
    if sub and sub.plan:
        current_plan = _serialize_plan(sub.plan)

    upgrade_slugs = get_upgrade_options(current_slug) if current_slug else []
    recommended_slug = (
        normalize_plan_slug(DEFAULT_UPGRADE.get(current_slug))
        if current_slug
        else None
    )

    upgrade_plans = []
    for slug in upgrade_slugs:
        plan = _upgrade_plan_queryset().filter(slug=slug).first()
        if plan:
            upgrade_plans.append(
                _serialize_plan(plan, recommended=(slug == recommended_slug)),
            )

    return {
        "current_plan": current_plan,
        "current_plan_slug": current_slug,
        "is_top_tier": is_top_tier_plan(current_slug),
        "current_subscription": {
            "status": sub.status if sub else None,
            "billing_cycle": sub.billing_cycle if sub else None,
        },
        "upgrade_plans": upgrade_plans,
        "payment_methods": _payment_methods_payload(),
        "checkout_note": (
            "Card and mobile money checkout use sandbox credentials in this environment. "
            "Payments are recorded but will not complete until live gateway APIs are connected."
        ),
    }


def process_upgrade_checkout(
    tenant,
    *,
    plan_slug: str,
    billing_cycle: str = "monthly",
    payment_method: str = "card",
    provider_slug: str = "",
    phone_number: str = "",
    card_last_four: str = "",
    card_brand: str = "",
    payer_name: str = "",
    actor=None,
) -> dict[str, Any]:
    """Initiate upgrade checkout; payment fails with dummy/unconfigured gateway."""
    sub = tenant.active_subscription
    current_slug = normalize_plan_slug(sub.plan.slug) if sub and sub.plan else None
    allowed = set(get_upgrade_options(current_slug)) if current_slug else set()
    target_slug = normalize_plan_slug(plan_slug)

    plan = _upgrade_plan_queryset().filter(slug=target_slug).first()
    if not plan:
        raise ValueError("Plan not found.")
    if current_slug and target_slug not in allowed and target_slug != current_slug:
        raise ValueError("Selected plan is not an available upgrade from your current plan.")

    if billing_cycle not in ("monthly", "yearly"):
        billing_cycle = "monthly"

    amount = plan.price_yearly if billing_cycle == "yearly" else plan.price_monthly
    if amount <= 0:
        raise ValueError("Selected plan does not require payment.")

    payment_result = PaymentService.process_checkout(
        tenant=tenant,
        plan=plan,
        amount=Decimal(str(amount)),
        billing_cycle=billing_cycle,
        currency=plan.currency or "USD",
        payment_method=payment_method,
        provider_slug=provider_slug,
        phone_number=phone_number,
        card_last_four=card_last_four,
        card_brand=card_brand,
        payer_name=payer_name,
    )

    if actor:
        from apps.communication.services import create_user_notification

        create_user_notification(
            user=actor,
            tenant=tenant,
            title="Plan upgrade payment could not be completed",
            message=payment_result.message,
            notification_type="warning",
            action_url="/school-admin/upgrade",
            metadata={
                "event": "upgrade_payment_failed",
                "plan_slug": plan.slug,
                "plan_name": plan.name,
                "billing_cycle": billing_cycle,
                "payment_method": payment_method,
                "provider_slug": provider_slug or payment_result.metadata.get("provider"),
                "reference": payment_result.reference,
                "amount": float(amount),
            },
        )

    return {
        "success": False,
        "message": payment_result.message,
        "reference": payment_result.reference,
        "plan": {"slug": plan.slug, "name": plan.name},
        "billing_cycle": billing_cycle,
        "payment_method": payment_method,
        "amount": float(amount),
        "currency": plan.currency or "USD",
        "provider_slug": provider_slug or payment_result.metadata.get("provider"),
        "transaction_id": payment_result.metadata.get("transaction_id"),
        "requires_admin_activation": True,
    }