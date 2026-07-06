import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FiLayers } from 'react-icons/fi';
import Modal from './Modal';
import StatusBadge from './StatusBadge';
import { plansService } from '../services/moduleService';

const STATUS_OPTIONS = [
  { value: 'trial', label: 'Trial' },
  { value: 'active', label: 'Active' },
  { value: 'grace_period', label: 'Grace Period' },
];

export function ChangeSchoolPlanModal({
  show,
  onHide,
  school,
  subscription,
  onSave,
  saving = false,
}) {
  const [planSlug, setPlanSlug] = useState('');
  const [billingCycle, setBillingCycle] = useState('monthly');
  const [subscriptionStatus, setSubscriptionStatus] = useState('trial');
  const [periodDays, setPeriodDays] = useState(30);
  const [notes, setNotes] = useState('');

  const { data: plans = [], isLoading } = useQuery({
    queryKey: ['plans', 'admin-select'],
    queryFn: () => plansService.list({ page_size: 50, is_active: true }),
    enabled: show,
    staleTime: 60 * 1000,
  });

  useEffect(() => {
    if (!show) return;
    setPlanSlug(subscription?.plan_slug || '');
    setBillingCycle(subscription?.billing_cycle || 'monthly');
    setSubscriptionStatus(subscription?.status === 'grace_period' ? 'grace_period' : subscription?.status || 'trial');
    setPeriodDays(30);
    setNotes('');
  }, [show, subscription]);

  const selectedPlan = plans.find((p) => p.slug === planSlug);
  const isDowngrade = subscription?.plan_slug && planSlug && planSlug !== subscription.plan_slug;

  const handleSubmit = async () => {
    if (!planSlug) return;
    await onSave({
      plan_slug: planSlug,
      billing_cycle: billingCycle,
      subscription_status: subscriptionStatus,
      period_days: periodDays,
      notes,
    });
  };

  return (
    <Modal
      show={show}
      onHide={onHide}
      title="Change School Plan"
      size="lg"
      footer={(
        <button
          type="button"
          className="btn btn-primary ms-auto"
          onClick={handleSubmit}
          disabled={saving || !planSlug || isLoading}
        >
          {saving ? 'Applying…' : 'Apply Plan Change'}
        </button>
      )}
    >
      <div className="d-flex align-items-center gap-2 mb-3 p-3 rounded-3" style={{ background: 'var(--apex-bg)' }}>
        <FiLayers style={{ color: 'var(--apex-primary)' }} />
        <div>
          <div className="fw-semibold">{school?.name}</div>
          <div className="small text-muted">
            Current: {subscription?.plan || 'No plan'}
            {subscription?.status && (
              <span className="ms-2"><StatusBadge status={subscription.status} /></span>
            )}
          </div>
        </div>
      </div>

      {isLoading ? (
        <p className="text-muted">Loading plans…</p>
      ) : (
        <div className="row g-3">
          <div className="col-md-6">
            <label className="form-label fw-medium">New Plan *</label>
            <select className="form-select" value={planSlug} onChange={(e) => setPlanSlug(e.target.value)}>
              <option value="">Select a plan</option>
              {plans.map((plan) => (
                <option key={plan.id} value={plan.slug}>
                  {plan.name}
                  {plan.slug === subscription?.plan_slug ? ' (current)' : ''}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-6">
            <label className="form-label fw-medium">Billing Cycle</label>
            <select className="form-select" value={billingCycle} onChange={(e) => setBillingCycle(e.target.value)}>
              <option value="monthly">Monthly</option>
              <option value="yearly">Yearly</option>
            </select>
          </div>
          <div className="col-md-6">
            <label className="form-label fw-medium">Subscription Status</label>
            <select
              className="form-select"
              value={subscriptionStatus}
              onChange={(e) => setSubscriptionStatus(e.target.value)}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          {subscriptionStatus === 'active' && (
            <div className="col-md-6">
              <label className="form-label fw-medium">Active Period (days)</label>
              <input
                type="number"
                className="form-control"
                min={1}
                max={365}
                value={periodDays}
                onChange={(e) => setPeriodDays(Number(e.target.value) || 30)}
              />
            </div>
          )}
          <div className="col-12">
            <label className="form-label fw-medium">Admin Notes (optional)</label>
            <textarea
              className="form-control"
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Reason for plan change, billing adjustment, etc."
            />
          </div>
        </div>
      )}

      {selectedPlan && (
        <div className="alert alert-light border small mt-3 mb-0">
          <strong>{selectedPlan.name}</strong>
          {' — '}
          ${selectedPlan.price_monthly}/mo · ${selectedPlan.price_yearly}/yr
          <br />
          <span className="text-muted">
            {(selectedPlan.enabled_features_detail?.length
              || selectedPlan.features?.length
              || selectedPlan.feature_count
              || 0)} features · Unlimited users
          </span>
        </div>
      )}

      {isDowngrade && (
        <div className="alert alert-warning small mt-3 mb-0">
          Changing plans will cancel the current subscription and assign the new plan immediately.
          The school&apos;s enabled modules will update on their next login or page refresh.
        </div>
      )}
    </Modal>
  );
}

export default ChangeSchoolPlanModal;