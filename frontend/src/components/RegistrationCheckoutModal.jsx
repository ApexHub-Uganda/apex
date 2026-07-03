import Modal from './Modal';
import PaymentCheckoutForm from './PaymentCheckoutForm';

export function RegistrationCheckoutModal({
  open,
  onClose,
  plan,
  loading,
  onSubmit,
}) {
  const amount = Number(plan?.price_monthly) || 0;

  return (
    <Modal
      show={open && Boolean(plan)}
      onHide={onClose}
      title={plan ? `Subscribe to ${plan.name}` : 'Subscribe'}
      size="md"
    >
      {plan && (
        <>
          <p className="text-muted small mb-4">
            Complete checkout for <strong>{plan.name}</strong> at ${amount.toFixed(2)}/month.
            Payment gateways are in sandbox mode and will return a failed status until live APIs are connected.
          </p>
          <PaymentCheckoutForm
            loading={loading}
            submitLabel="Subscribe"
            amountLabel={`$${amount.toFixed(2)}`}
            onSubmit={onSubmit}
          />
        </>
      )}
    </Modal>
  );
}

export default RegistrationCheckoutModal;