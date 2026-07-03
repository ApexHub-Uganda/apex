import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import {
  FiArrowLeft, FiArrowRight, FiCheck, FiLayers,
  FiShield, FiStar, FiXCircle,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import PaymentCheckoutForm from '../../components/PaymentCheckoutForm';
import PlanFeatureBreakdown from '../../components/PlanFeatureBreakdown';
import PlanVerifiedBadge from '../../components/PlanVerifiedBadge';
import { PageSkeleton } from '../../components/LoadingSkeleton';
import { planUpgradeService } from '../../services/moduleService';
import { getPlanMeta } from '../../config/schoolDashboard';
import { useTenant } from '../../hooks/useTenant';
import { extractApiError, notify } from '../../utils/notify';
import { isTopTierPlanSlug } from '../../utils/planBadge';

const STEPS = [
  { key: 'plans', label: 'Choose plan' },
  { key: 'features', label: 'Features' },
  { key: 'billing', label: 'Billing' },
  { key: 'review', label: 'Review' },
  { key: 'payment', label: 'Payment' },
  { key: 'result', label: 'Complete' },
];

const formatMoney = (amount, currency = 'USD') => {
  const value = Number(amount) || 0;
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(value);
  } catch {
    return `${currency} ${value.toFixed(2)}`;
  }
};

function StepIndicator({ currentIndex }) {
  return (
    <div className="plan-upgrade-steps" aria-label="Upgrade progress">
      {STEPS.map((step, idx) => (
        <div
          key={step.key}
          className={`plan-upgrade-step ${idx === currentIndex ? 'is-active' : ''} ${idx < currentIndex ? 'is-done' : ''}`}
        >
          <span className="plan-upgrade-step-dot">
            {idx < currentIndex ? <FiCheck size={12} /> : idx + 1}
          </span>
          <span className="plan-upgrade-step-label d-none d-md-inline">{step.label}</span>
        </div>
      ))}
    </div>
  );
}

function PlanCard({ plan, selected, current, onSelect }) {
  const meta = getPlanMeta(plan.slug);
  const isCurrent = current;

  return (
    <motion.button
      type="button"
      className={`plan-upgrade-card ${selected ? 'is-selected' : ''} ${isCurrent ? 'is-current' : ''}`}
      onClick={() => !isCurrent && onSelect(plan)}
      whileHover={isCurrent ? undefined : { y: -4 }}
      layout
    >
      {plan.recommended && !isCurrent && (
        <span className="plan-upgrade-card-badge">
          <FiStar size={12} /> Recommended
        </span>
      )}
      {isCurrent && <span className="plan-upgrade-card-badge is-muted">Current plan</span>}
      <div className="d-flex align-items-center gap-2 mb-2">
        <h5 className="fw-bold mb-0">{plan.name}</h5>
        <PlanVerifiedBadge planSlug={plan.slug} size="sm" />
      </div>
      <p className="text-muted small mb-3">{meta.description || plan.description}</p>
      <div className="plan-upgrade-card-price">
        <span className="plan-upgrade-card-amount">
          {formatMoney(plan.price_monthly, plan.currency)}
        </span>
        <span className="text-muted small">/ month</span>
      </div>
      <div className="text-muted small mb-3">
        or {formatMoney(plan.price_yearly, plan.currency)} / year
      </div>
      <ul className="plan-upgrade-card-highlights">
        {(plan.module_highlights || []).slice(0, 4).map((item) => (
          <li key={item}>
            <FiCheck size={13} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
      <div className="plan-upgrade-card-footer small text-muted">
        {plan.feature_count} features included
      </div>
    </motion.button>
  );
}

export function PlanUpgrade() {
  const [searchParams] = useSearchParams();
  const preselectedPlan = searchParams.get('plan');
  const { tenant } = useTenant();

  const [stepIndex, setStepIndex] = useState(0);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [billingCycle, setBillingCycle] = useState('monthly');
  const [checkoutResult, setCheckoutResult] = useState(null);

  const { data: catalog, isLoading, isError, refetch } = useQuery({
    queryKey: ['plan-upgrade-catalog', tenant?.id],
    queryFn: () => planUpgradeService.getCatalog(),
    retry: 1,
  });

  const checkoutMutation = useMutation({
    mutationFn: (payload) => planUpgradeService.checkout(payload),
    onSuccess: (data) => {
      setCheckoutResult(data);
      setStepIndex(5);
    },
    onError: (err) => {
      const message = extractApiError(err, 'Payment could not be processed.');
      notify.error(message);
    },
  });

  const upgradePlans = catalog?.upgrade_plans ?? [];
  const currentPlan = catalog?.current_plan;
  const paymentMethods = catalog?.payment_methods ?? [];

  useEffect(() => {
    if (!upgradePlans.length || selectedPlan) return;
    const match = upgradePlans.find((p) => p.slug === preselectedPlan)
      || upgradePlans.find((p) => p.recommended)
      || upgradePlans[0];
    if (match) setSelectedPlan(match);
  }, [upgradePlans, preselectedPlan, selectedPlan]);

  const amount = useMemo(() => {
    if (!selectedPlan) return 0;
    return billingCycle === 'yearly' ? selectedPlan.price_yearly : selectedPlan.price_monthly;
  }, [selectedPlan, billingCycle]);

  const yearlySavings = useMemo(() => {
    if (!selectedPlan) return 0;
    const monthlyAnnual = selectedPlan.price_monthly * 12;
    return Math.max(0, monthlyAnnual - selectedPlan.price_yearly);
  }, [selectedPlan]);

  const goNext = () => setStepIndex((i) => Math.min(i + 1, STEPS.length - 1));
  const goBack = () => setStepIndex((i) => Math.max(i - 1, 0));

  const handlePaymentSubmit = (paymentPayload) => {
    if (!selectedPlan) return;
    checkoutMutation.mutate({
      plan_slug: selectedPlan.slug,
      billing_cycle: billingCycle,
      ...paymentPayload,
    });
  };

  if (isLoading) return <PageSkeleton />;

  if (isError) {
    return (
      <div>
        <PageHeader title="Plan Upgrade" subtitle="Unable to load upgrade catalog" />
        <div className="apex-card p-5 text-center">
          <FiLayers size={36} className="text-muted mb-3" />
          <h5 className="fw-bold">Upgrade catalog unavailable</h5>
          <p className="text-muted mb-4">
            We could not load available plans right now. This is usually temporary — please retry.
          </p>
          <div className="d-flex justify-content-center gap-2">
            <button type="button" className="btn btn-primary btn-sm" onClick={() => refetch()}>
              Retry
            </button>
            <Link to="/school-admin" className="btn btn-outline-secondary btn-sm">
              <FiArrowLeft className="me-1" /> Back to dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const isTopTier = catalog?.is_top_tier ?? isTopTierPlanSlug(currentPlan?.slug);

  if (!upgradePlans.length) {
    return (
      <div>
        <PageHeader
          title="Plan Upgrade"
          subtitle={isTopTier ? "You're on the highest available plan" : 'Upgrade options unavailable'}
        />
        <div className="apex-card p-5 text-center">
          <FiLayers size={36} className="text-muted mb-3" />
          <h5 className="fw-bold">
            {isTopTier ? 'No upgrades available' : 'Unable to load upgrade options'}
          </h5>
          <p className="text-muted mb-4">
            {isTopTier && currentPlan
              ? `Your school is on ${currentPlan.name}, our highest tier. Contact support if you need a custom arrangement.`
              : currentPlan
                ? `Your school is on ${currentPlan.name}. Higher-tier plans are not available right now — please contact support or try again later.`
                : 'Unable to load upgrade options.'}
          </p>
          <Link to="/school-admin" className="btn btn-outline-secondary btn-sm">
            <FiArrowLeft className="me-1" /> Back to dashboard
          </Link>
        </div>
      </div>
    );
  }

  const stepKey = STEPS[stepIndex].key;

  return (
    <div className="plan-upgrade-page">
      <PageHeader
        title="Upgrade your plan"
        subtitle="Compare plans, review features, and complete checkout for your school"
        actions={(
          <Link to="/school-admin" className="btn btn-sm btn-outline-secondary">
            <FiArrowLeft size={14} className="me-1" /> Dashboard
          </Link>
        )}
      />

      <StepIndicator currentIndex={stepIndex} />

      {catalog?.checkout_note && stepIndex < 5 && (
        <div className="plan-upgrade-notice apex-card p-3 mb-4">
          <FiShield size={16} className="me-2 flex-shrink-0" />
          <span className="small">{catalog.checkout_note}</span>
        </div>
      )}

      <AnimatePresence mode="wait">
        <motion.div
          key={stepKey}
          className="plan-upgrade-panel"
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -16 }}
          transition={{ duration: 0.22 }}
        >
          {stepKey === 'plans' && (
            <>
              <div className="d-flex align-items-center justify-content-between mb-3">
                <h5 className="fw-bold mb-0">Select a plan</h5>
                {currentPlan && (
                  <span className="small text-muted">
                    Current: <strong>{currentPlan.name}</strong>
                  </span>
                )}
              </div>
              <div className="row g-3">
                {currentPlan && (
                  <div className="col-md-6 col-xl-4">
                    <PlanCard plan={currentPlan} selected={false} current onSelect={() => {}} />
                  </div>
                )}
                {upgradePlans.map((plan) => (
                  <div className="col-md-6 col-xl-4" key={plan.slug}>
                    <PlanCard
                      plan={plan}
                      selected={selectedPlan?.slug === plan.slug}
                      current={false}
                      onSelect={setSelectedPlan}
                    />
                  </div>
                ))}
              </div>
            </>
          )}

          {stepKey === 'features' && selectedPlan && (
            <>
              <h5 className="fw-bold mb-1">What&apos;s included in {selectedPlan.name}</h5>
              <p className="text-muted small mb-4">
                {selectedPlan.inherited_summary
                  ? selectedPlan.inherited_summary
                  : `${selectedPlan.feature_count} features across ${(selectedPlan.feature_categories || []).length} categories`}
              </p>
              <PlanFeatureBreakdown plan={selectedPlan} />
            </>
          )}

          {stepKey === 'billing' && selectedPlan && (
            <>
              <h5 className="fw-bold mb-3">Choose billing cycle</h5>
              <div className="row g-3 mb-4">
                <div className="col-md-6">
                  <button
                    type="button"
                    className={`plan-upgrade-billing-option w-100 ${billingCycle === 'monthly' ? 'is-selected' : ''}`}
                    onClick={() => setBillingCycle('monthly')}
                  >
                    <span className="fw-bold">Monthly</span>
                    <span className="plan-upgrade-billing-price">
                      {formatMoney(selectedPlan.price_monthly, selectedPlan.currency)}
                      <small>/mo</small>
                    </span>
                    <span className="text-muted small">Flexible, cancel anytime</span>
                  </button>
                </div>
                <div className="col-md-6">
                  <button
                    type="button"
                    className={`plan-upgrade-billing-option w-100 ${billingCycle === 'yearly' ? 'is-selected' : ''}`}
                    onClick={() => setBillingCycle('yearly')}
                  >
                    <span className="fw-bold">Yearly</span>
                    <span className="plan-upgrade-billing-price">
                      {formatMoney(selectedPlan.price_yearly, selectedPlan.currency)}
                      <small>/yr</small>
                    </span>
                    {yearlySavings > 0 && (
                      <span className="plan-upgrade-save-badge">
                        Save {formatMoney(yearlySavings, selectedPlan.currency)}
                      </span>
                    )}
                  </button>
                </div>
              </div>
              <div className="apex-card p-4 plan-upgrade-summary-strip">
                <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
                  <div>
                    <div className="small text-muted">Due today</div>
                    <div className="fs-4 fw-bold">{formatMoney(amount, selectedPlan.currency)}</div>
                  </div>
                  <div className="text-muted small">
                    Billed {billingCycle === 'yearly' ? 'annually' : 'every month'} · {tenant?.name}
                  </div>
                </div>
              </div>
            </>
          )}

          {stepKey === 'review' && selectedPlan && (
            <>
              <h5 className="fw-bold mb-3">Review your upgrade</h5>
              <div className="apex-card p-4 plan-upgrade-review">
                <div className="row g-3">
                  <div className="col-sm-6">
                    <div className="small text-muted">School</div>
                    <div className="fw-semibold">{tenant?.name || '—'}</div>
                  </div>
                  <div className="col-sm-6">
                    <div className="small text-muted">Current plan</div>
                    <div className="fw-semibold">{currentPlan?.name || '—'}</div>
                  </div>
                  <div className="col-sm-6">
                    <div className="small text-muted">Upgrading to</div>
                    <div className="fw-semibold d-flex align-items-center gap-2">
                      {selectedPlan.name}
                      <PlanVerifiedBadge planSlug={selectedPlan.slug} size="sm" />
                    </div>
                  </div>
                  <div className="col-sm-6">
                    <div className="small text-muted">Billing</div>
                    <div className="fw-semibold text-capitalize">{billingCycle}</div>
                  </div>
                  <div className="col-12">
                    <hr />
                    <div className="d-flex justify-content-between align-items-center">
                      <span className="fw-bold">Total due</span>
                      <span className="fs-4 fw-bold text-primary">
                        {formatMoney(amount, selectedPlan.currency)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {stepKey === 'payment' && selectedPlan && (
            <div className="apex-card p-4">
              <h5 className="fw-bold mb-1">Secure checkout</h5>
              <p className="text-muted small mb-4">
                Pay {formatMoney(amount, selectedPlan.currency)} for {selectedPlan.name} ({billingCycle} billing).
              </p>
              <PaymentCheckoutForm
                paymentMethods={paymentMethods}
                amountLabel={formatMoney(amount, selectedPlan.currency)}
                loading={checkoutMutation.isPending}
                submitLabel="Complete upgrade"
                onSubmit={handlePaymentSubmit}
              />
            </div>
          )}

          {stepKey === 'result' && checkoutResult && (
            <div className="apex-card p-5 text-center plan-upgrade-result">
              <div className="plan-upgrade-result-icon is-failed">
                <FiXCircle size={40} />
              </div>
              <h4 className="fw-bold mb-2">Payment could not be processed</h4>
              <p className="text-muted mb-4 mx-auto" style={{ maxWidth: 520 }}>
                {checkoutResult.message}
              </p>
              <div className="plan-upgrade-result-meta text-start mx-auto" style={{ maxWidth: 420 }}>
                <div className="d-flex justify-content-between py-2 border-bottom">
                  <span className="text-muted">Reference</span>
                  <span className="fw-mono small">{checkoutResult.reference}</span>
                </div>
                <div className="d-flex justify-content-between py-2 border-bottom">
                  <span className="text-muted">Plan</span>
                  <span className="fw-semibold">{checkoutResult.plan?.name}</span>
                </div>
                <div className="d-flex justify-content-between py-2 border-bottom">
                  <span className="text-muted">Amount</span>
                  <span className="fw-semibold">
                    {formatMoney(checkoutResult.amount, checkoutResult.currency)}
                  </span>
                </div>
                <div className="d-flex justify-content-between py-2">
                  <span className="text-muted">Method</span>
                  <span className="fw-semibold text-capitalize">
                    {(checkoutResult.payment_method || 'card').replace('_', ' ')}
                  </span>
                </div>
              </div>
              <p className="small text-muted mt-4 mb-4">
                A super admin can activate your new plan manually. You&apos;ll receive a notification when your subscription changes.
              </p>
              <div className="d-flex gap-2 justify-content-center flex-wrap">
                <Link to="/school-admin" className="btn btn-primary btn-sm">
                  Back to dashboard
                </Link>
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={() => {
                    setCheckoutResult(null);
                    setStepIndex(0);
                  }}
                >
                  Try again
                </button>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {stepIndex < 5 && (
        <div className="plan-upgrade-nav">
          <button
            type="button"
            className="btn btn-outline-secondary"
            onClick={goBack}
            disabled={stepIndex === 0}
          >
            <FiArrowLeft className="me-1" /> Back
          </button>
          {stepKey !== 'payment' && (
            <button
              type="button"
              className="btn btn-primary d-inline-flex align-items-center gap-2"
              onClick={goNext}
              disabled={!selectedPlan}
            >
              Continue <FiArrowRight />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default PlanUpgrade;