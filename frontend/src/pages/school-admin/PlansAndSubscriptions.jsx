import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  FiArrowRight, FiCalendar, FiCheck, FiCreditCard, FiLayers, FiSmartphone, FiTrendingUp,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import PlanNameWithBadge from '../../components/PlanNameWithBadge';
import StatusBadge from '../../components/StatusBadge';
import { PageSkeleton } from '../../components/LoadingSkeleton';
import { billingService, planUpgradeService } from '../../services/moduleService';
import { tenantService } from '../../services/tenantService';
import { useTenant } from '../../hooks/useTenant';
import { getPlanMeta } from '../../config/schoolDashboard';
import { buildUpgradePath } from '../../utils/upgradePaths';
import { isTopTierPlanSlug, normalizePlanSlug } from '../../utils/planBadge';

const formatMoney = (amount, currency = 'USD') => {
  const value = Number(amount) || 0;
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(value);
  } catch {
    return `${currency} ${value.toFixed(2)}`;
  }
};

const formatDate = (value) => {
  if (!value) return '—';
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
  });
};

const methodLabel = (method) => {
  if (method === 'mobile_money') return 'Mobile Money';
  if (method === 'card') return 'Card';
  return method || '—';
};

export function PlansAndSubscriptions() {
  const { tenant } = useTenant();

  const { data: subscription, isLoading: subLoading } = useQuery({
    queryKey: ['school-subscription-current', tenant?.id],
    queryFn: () => tenantService.getCurrentSubscription(),
    enabled: !!tenant?.id,
  });

  const {
    data: catalog,
    isLoading: catalogLoading,
    isError: catalogError,
    refetch: refetchCatalog,
  } = useQuery({
    queryKey: ['plan-upgrade-catalog', tenant?.id, 'settings'],
    queryFn: () => planUpgradeService.getCatalog(),
    enabled: !!tenant?.id,
    retry: 1,
  });

  const { data: transactions = [], isLoading: txLoading } = useQuery({
    queryKey: ['school-payment-transactions', tenant?.id],
    queryFn: () => billingService.listTransactions({ page_size: 8, ordering: '-created_at' }),
    enabled: !!tenant?.id,
  });

  if (subLoading && !subscription) return <PageSkeleton />;

  const planSlug = subscription?.plan_slug
    || tenant?.subscription?.plan_slug
    || catalog?.current_plan?.slug;
  const planName = subscription?.plan_name
    || tenant?.subscription?.plan_name
    || catalog?.current_plan?.name;
  const upgradePlans = catalog?.upgrade_plans ?? [];
  const normalizedPlanSlug = normalizePlanSlug(planSlug);
  const isTopTier = catalog?.is_top_tier ?? isTopTierPlanSlug(normalizedPlanSlug);
  const hasUpgrades = upgradePlans.length > 0;
  const billingCycle = subscription?.billing_cycle || catalog?.current_subscription?.billing_cycle || 'monthly';

  return (
    <div className="school-plans-page">
      <PageHeader
        title="Plans & Subscriptions"
        subtitle="Your school's subscription, billing cycle, and payment history"
        actions={hasUpgrades && (
          <Link to={buildUpgradePath()} className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1">
            <FiTrendingUp size={14} /> Upgrade plan
          </Link>
        )}
      />

      <div className="row g-3 mb-4">
        <div className="col-lg-7">
          <motion.div className="apex-card p-4 h-100" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <div className="d-flex flex-wrap align-items-start justify-content-between gap-3 mb-3">
              <div>
                <div className="small text-muted mb-1">Current plan</div>
                <PlanNameWithBadge
                  planSlug={planSlug}
                  planName={planName || 'Your Plan'}
                  size="md"
                  className="fw-bold fs-5"
                />
              </div>
              {subscription?.status && <StatusBadge status={subscription.status} />}
            </div>

            <p className="text-muted small mb-4">
              {getPlanMeta(planSlug).description}
            </p>

            <div className="row g-3">
              <div className="col-sm-6">
                <div className="school-plans-stat">
                  <FiCalendar className="text-muted" />
                  <div>
                    <div className="small text-muted">Billing cycle</div>
                    <div className="fw-semibold text-capitalize">{billingCycle}</div>
                  </div>
                </div>
              </div>
              <div className="col-sm-6">
                <div className="school-plans-stat">
                  <FiLayers className="text-muted" />
                  <div>
                    <div className="small text-muted">Features enabled</div>
                    <div className="fw-semibold">
                      {catalog?.current_plan?.feature_count ?? tenant?.subscription?.feature_count ?? '—'}
                    </div>
                  </div>
                </div>
              </div>
              <div className="col-sm-6">
                <div className="school-plans-stat">
                  <FiCalendar className="text-muted" />
                  <div>
                    <div className="small text-muted">Trial ends</div>
                    <div className="fw-semibold">{formatDate(subscription?.trial_ends_at)}</div>
                  </div>
                </div>
              </div>
              <div className="col-sm-6">
                <div className="school-plans-stat">
                  <FiCalendar className="text-muted" />
                  <div>
                    <div className="small text-muted">Next billing / period end</div>
                    <div className="fw-semibold">
                      {formatDate(subscription?.current_period_end || subscription?.next_billing)}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {catalog?.checkout_note && (
              <div className="school-plans-notice small mt-4 mb-0">
                {catalog.checkout_note}
              </div>
            )}
          </motion.div>
        </div>

        <div className="col-lg-5">
          <motion.div
            className="apex-card p-4 h-100 school-plans-upgrade-card"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
          >
            <h5 className="fw-bold mb-2 d-flex align-items-center gap-2">
              <FiTrendingUp /> Upgrade your plan
            </h5>
            <p className="text-muted small mb-3">
              Compare plans, review features, and complete checkout with card or mobile money.
            </p>

            {catalogLoading ? (
              <p className="text-muted small">Loading upgrade options…</p>
            ) : catalogError ? (
              <div className="mb-3">
                <p className="text-muted small mb-2">
                  Could not load upgrade options. Please refresh or try again in a moment.
                </p>
                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => refetchCatalog()}>
                  Retry
                </button>
              </div>
            ) : hasUpgrades ? (
              <ul className="school-plans-upgrade-list mb-3">
                {upgradePlans.slice(0, 3).map((plan) => (
                  <li key={plan.slug}>
                    <div>
                      <span className="fw-semibold">{plan.name}</span>
                      {plan.recommended && (
                        <span className="school-plans-recommended ms-2">Recommended</span>
                      )}
                      <div className="text-muted small">
                        {formatMoney(plan.price_monthly, plan.currency)}/mo · {plan.feature_count} features
                      </div>
                      {plan.inherited_summary && (
                        <div className="text-muted small mt-1">{plan.inherited_summary}</div>
                      )}
                    </div>
                    <Link
                      to={buildUpgradePath(plan.slug)}
                      className="btn btn-sm btn-outline-primary"
                    >
                      View
                    </Link>
                  </li>
                ))}
              </ul>
            ) : isTopTier ? (
              <p className="text-muted small mb-3">
                You are on the highest available plan tier. Contact support for custom arrangements.
              </p>
            ) : (
              <p className="text-muted small mb-3">
                Upgrade options are temporarily unavailable. Please try again later or contact support
                if you expected to move to a higher plan.
              </p>
            )}

            {hasUpgrades && (
              <Link to={buildUpgradePath()} className="btn btn-primary w-100 d-inline-flex align-items-center justify-content-center gap-2">
                Start upgrade wizard <FiArrowRight size={14} />
              </Link>
            )}
          </motion.div>
        </div>
      </div>

      {catalog?.payment_methods?.length > 0 && (
        <motion.div className="apex-card p-4 mb-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
          <h5 className="fw-bold mb-3">Accepted payment methods</h5>
          <div className="row g-3">
            {catalog.payment_methods.map((method) => (
              <div className="col-md-6" key={method.type}>
                <div className="school-plans-payment-method">
                  {method.type === 'mobile_money' ? <FiSmartphone /> : <FiCreditCard />}
                  <div>
                    <div className="fw-semibold">{method.label}</div>
                    <div className="text-muted small">{method.description}</div>
                    <div className="text-muted small mt-1">
                      {(method.providers || []).map((p) => p.name).join(' · ')}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}>
        <div className="d-flex align-items-center justify-content-between mb-3">
          <h5 className="fw-bold mb-0">Payment history</h5>
          <span className="text-muted small">Recent subscription checkout attempts</span>
        </div>

        {txLoading ? (
          <p className="text-muted small mb-0">Loading transactions…</p>
        ) : transactions.length === 0 ? (
          <p className="text-muted small mb-0">
            No payment attempts recorded yet. Completed upgrades will appear here after checkout.
          </p>
        ) : (
          <div className="table-responsive">
            <table className="table table-sm align-middle mb-0 school-plans-table">
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>Amount</th>
                  <th>Method</th>
                  <th>Status</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr key={tx.id}>
                    <td className="font-monospace small">{tx.reference}</td>
                    <td>{formatMoney(tx.amount, tx.currency)}</td>
                    <td className="text-capitalize">{methodLabel(tx.payment_method)}</td>
                    <td><StatusBadge status={tx.status} /></td>
                    <td className="text-muted small">{formatDate(tx.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>
    </div>
  );
}

export default PlansAndSubscriptions;