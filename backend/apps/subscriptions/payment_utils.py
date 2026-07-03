"""Payment checkout validation and masking helpers."""
from __future__ import annotations

import re

from apps.core.constants import PaymentMethodType


def normalize_payment_method(value: str | None) -> str:
    if value == PaymentMethodType.MOBILE_MONEY:
        return PaymentMethodType.MOBILE_MONEY
    return PaymentMethodType.CARD


def mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) < 4:
        return ""
    return f"***{digits[-4:]}"


def validate_checkout_details(
    *,
    payment_method: str,
    phone_number: str = "",
    card_last_four: str = "",
    payer_name: str = "",
) -> None:
    if payment_method == PaymentMethodType.MOBILE_MONEY:
        digits = re.sub(r"\D", "", phone_number or "")
        if len(digits) < 9 or len(digits) > 15:
            raise ValueError("Enter a valid mobile money phone number (9–15 digits).")
        return

    last_four = re.sub(r"\D", "", card_last_four or "")
    if len(last_four) != 4:
        raise ValueError("Enter a valid card number to continue.")
    if not payer_name or len(payer_name.strip()) < 2:
        raise ValueError("Enter the name on your card.")