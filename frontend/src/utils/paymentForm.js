export const PAYMENT_METHOD_CARD = 'card';
export const PAYMENT_METHOD_MOBILE = 'mobile_money';

export function formatCardNumber(value) {
  const digits = String(value || '').replace(/\D/g, '').slice(0, 16);
  return digits.replace(/(\d{4})(?=\d)/g, '$1 ').trim();
}

export function formatExpiry(value) {
  const digits = String(value || '').replace(/\D/g, '').slice(0, 4);
  if (digits.length <= 2) return digits;
  return `${digits.slice(0, 2)}/${digits.slice(2)}`;
}

export function detectCardBrand(number) {
  const digits = String(number || '').replace(/\D/g, '');
  if (/^4/.test(digits)) return 'visa';
  if (/^5[1-5]/.test(digits)) return 'mastercard';
  if (/^3[47]/.test(digits)) return 'amex';
  return 'card';
}

export function getCardLastFour(number) {
  const digits = String(number || '').replace(/\D/g, '');
  return digits.slice(-4);
}

export function validateCardForm({ cardNumber, expiry, cvc, cardName }) {
  const digits = String(cardNumber || '').replace(/\D/g, '');
  if (digits.length < 13 || digits.length > 19) {
    return 'Enter a valid card number.';
  }
  const expiryDigits = String(expiry || '').replace(/\D/g, '');
  if (expiryDigits.length !== 4) {
    return 'Enter expiry as MM/YY.';
  }
  const month = Number(expiryDigits.slice(0, 2));
  if (month < 1 || month > 12) {
    return 'Enter a valid expiry month.';
  }
  if (String(cvc || '').replace(/\D/g, '').length < 3) {
    return 'Enter a valid security code.';
  }
  if (!String(cardName || '').trim()) {
    return 'Enter the name on your card.';
  }
  return null;
}

export function validateMobileForm({ phoneNumber }) {
  const digits = String(phoneNumber || '').replace(/\D/g, '');
  if (digits.length < 9 || digits.length > 15) {
    return 'Enter a valid mobile money phone number.';
  }
  return null;
}

export function buildCheckoutPayload({
  paymentMethod,
  providerSlug,
  cardNumber,
  cardName,
  phoneNumber,
}) {
  if (paymentMethod === PAYMENT_METHOD_MOBILE) {
    const digits = String(phoneNumber || '').replace(/\D/g, '');
    return {
      payment_method: PAYMENT_METHOD_MOBILE,
      provider_slug: providerSlug,
      phone_number: digits.startsWith('+') ? digits : `+${digits}`,
    };
  }
  return {
    payment_method: PAYMENT_METHOD_CARD,
    provider_slug: providerSlug,
    card_last_four: getCardLastFour(cardNumber),
    card_brand: detectCardBrand(cardNumber),
    payer_name: String(cardName || '').trim(),
  };
}