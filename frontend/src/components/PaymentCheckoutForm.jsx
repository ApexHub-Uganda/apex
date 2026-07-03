import { useEffect, useMemo, useState } from 'react';
import { FiCreditCard, FiSmartphone } from 'react-icons/fi';
import {
  PAYMENT_METHOD_CARD,
  PAYMENT_METHOD_MOBILE,
  buildCheckoutPayload,
  formatCardNumber,
  formatExpiry,
  validateCardForm,
  validateMobileForm,
} from '../utils/paymentForm';

const DEFAULT_METHODS = [
  {
    type: PAYMENT_METHOD_CARD,
    label: 'Credit or Debit Card',
    description: 'Pay with Visa, Mastercard, or Amex',
    default: true,
    providers: [{ slug: 'stripe', name: 'Stripe' }],
  },
  {
    type: PAYMENT_METHOD_MOBILE,
    label: 'Mobile Money',
    description: 'M-Pesa, MTN MoMo, or Airtel Money',
    providers: [{ slug: 'mpesa', name: 'M-Pesa' }],
  },
];

export function PaymentCheckoutForm({
  amountLabel,
  paymentMethods = DEFAULT_METHODS,
  onSubmit,
  loading = false,
  submitLabel = 'Pay now',
}) {
  const methods = paymentMethods.length ? paymentMethods : DEFAULT_METHODS;
  const [paymentMethod, setPaymentMethod] = useState(PAYMENT_METHOD_CARD);
  const [providerSlug, setProviderSlug] = useState('');
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [cvc, setCvc] = useState('');
  const [cardName, setCardName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [error, setError] = useState('');

  const activeMethod = useMemo(
    () => methods.find((m) => m.type === paymentMethod) || methods[0],
    [methods, paymentMethod],
  );

  useEffect(() => {
    const providers = activeMethod?.providers || [];
    if (providers.length && !providers.some((p) => p.slug === providerSlug)) {
      setProviderSlug(providers[0].slug);
    }
  }, [activeMethod, providerSlug]);

  const handleSubmit = (event) => {
    event.preventDefault();
    setError('');

    if (paymentMethod === PAYMENT_METHOD_MOBILE) {
      const mobileError = validateMobileForm({ phoneNumber });
      if (mobileError) {
        setError(mobileError);
        return;
      }
    } else {
      const cardError = validateCardForm({ cardNumber, expiry, cvc, cardName });
      if (cardError) {
        setError(cardError);
        return;
      }
    }

    onSubmit(buildCheckoutPayload({
      paymentMethod,
      providerSlug,
      cardNumber,
      cardName,
      phoneNumber,
    }));
  };

  return (
    <form className="payment-checkout-form" onSubmit={handleSubmit} noValidate>
      <div className="payment-method-tabs mb-4" role="tablist" aria-label="Payment method">
        {methods.map((method) => (
          <button
            key={method.type}
            type="button"
            role="tab"
            aria-selected={paymentMethod === method.type}
            className={`payment-method-tab ${paymentMethod === method.type ? 'is-active' : ''}`}
            onClick={() => setPaymentMethod(method.type)}
          >
            {method.type === PAYMENT_METHOD_MOBILE ? <FiSmartphone size={16} /> : <FiCreditCard size={16} />}
            <span>{method.label}</span>
          </button>
        ))}
      </div>

      {paymentMethod === PAYMENT_METHOD_CARD ? (
        <div className="payment-checkout-card-panel">
          <p className="text-muted small mb-3">
            Enter your card details exactly as they appear on your card. Payments use sandbox gateways and will not complete until live APIs are connected.
          </p>
          <div className="mb-3">
            <label className="form-label small fw-medium" htmlFor="checkout-card-name">Name on card</label>
            <input
              id="checkout-card-name"
              className="form-control"
              value={cardName}
              onChange={(e) => setCardName(e.target.value)}
              placeholder="Jane Doe"
              autoComplete="cc-name"
            />
          </div>
          <div className="mb-3">
            <label className="form-label small fw-medium" htmlFor="checkout-card-number">Card number</label>
            <input
              id="checkout-card-number"
              className="form-control font-monospace"
              value={cardNumber}
              onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}
              placeholder="4242 4242 4242 4242"
              inputMode="numeric"
              autoComplete="cc-number"
            />
          </div>
          <div className="row g-3 mb-3">
            <div className="col-6">
              <label className="form-label small fw-medium" htmlFor="checkout-expiry">Expiry</label>
              <input
                id="checkout-expiry"
                className="form-control font-monospace"
                value={expiry}
                onChange={(e) => setExpiry(formatExpiry(e.target.value))}
                placeholder="MM/YY"
                inputMode="numeric"
                autoComplete="cc-exp"
              />
            </div>
            <div className="col-6">
              <label className="form-label small fw-medium" htmlFor="checkout-cvc">CVC</label>
              <input
                id="checkout-cvc"
                className="form-control font-monospace"
                value={cvc}
                onChange={(e) => setCvc(e.target.value.replace(/\D/g, '').slice(0, 4))}
                placeholder="123"
                inputMode="numeric"
                autoComplete="cc-csc"
              />
            </div>
          </div>
          {(activeMethod.providers || []).length > 1 && (
            <div className="mb-3">
              <label className="form-label small fw-medium" htmlFor="checkout-card-provider">Processor</label>
              <select
                id="checkout-card-provider"
                className="form-select"
                value={providerSlug}
                onChange={(e) => setProviderSlug(e.target.value)}
              >
                {activeMethod.providers.map((p) => (
                  <option key={p.slug} value={p.slug}>{p.name}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      ) : (
        <div className="payment-checkout-mobile-panel">
          <p className="text-muted small mb-3">
            Enter the mobile money number that will receive the payment prompt. Mobile money is not yet available — your request will be recorded and payment will fail for now.
          </p>
          <div className="mb-3">
            <label className="form-label small fw-medium" htmlFor="checkout-phone">Mobile money number</label>
            <div className="input-group">
              <span className="input-group-text">+</span>
              <input
                id="checkout-phone"
                className="form-control font-monospace"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value.replace(/[^\d+]/g, ''))}
                placeholder="256700000000"
                inputMode="tel"
                autoComplete="tel"
              />
            </div>
          </div>
          {(activeMethod.providers || []).length > 1 && (
            <div className="mb-3">
              <label className="form-label small fw-medium" htmlFor="checkout-mobile-provider">Network</label>
              <select
                id="checkout-mobile-provider"
                className="form-select"
                value={providerSlug}
                onChange={(e) => setProviderSlug(e.target.value)}
              >
                {activeMethod.providers.map((p) => (
                  <option key={p.slug} value={p.slug}>{p.name}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {error && <div className="alert alert-danger py-2 small mb-3">{error}</div>}

      <button type="submit" className="btn btn-primary w-100" disabled={loading}>
        {loading ? 'Processing payment…' : `${submitLabel}${amountLabel ? ` · ${amountLabel}` : ''}`}
      </button>
    </form>
  );
}

export default PaymentCheckoutForm;