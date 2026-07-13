import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  FiLayers, FiTrendingUp, FiClock, FiDollarSign, FiAlertTriangle,
  FiEdit2, FiTrash2,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import StatCard from '../../components/StatCard';
import StatusBadge from '../../components/StatusBadge';
import DataTable from '../../components/DataTable';

import { DoughnutChart } from '../../components/Charts';
import ProgressBar from '../../components/ProgressBar';
import { PageSkeleton } from '../../components/LoadingSkeleton';
import { dashboardService } from '../../services/dashboardService';
import { plansService, subscriptionsService } from '../../services/moduleService';
import { alert, extractApiError, notify } from '../../utils/notify';

const EMPTY_CHART = { labels: [], datasets: [] };
const TABS = ['overview', 'plans', 'subscriptions'];

const formatDate = (v) => (v ? new Date(v).toLocaleDateString() : '—');
const formatCurrency = (v) => {
  const n = Number(v) || 0;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return n.toFixed(0);
};

export function PlansAndSubscriptions() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTab] = useState(searchParams.get('tab') || 'overview');
  const [subFilter, setSubFilter] = useState('');
  const queryClient = useQueryClient();

  useEffect(() => {
    const nextTab = searchParams.get('tab');
    if (nextTab && nextTab !== tab) {
      setTab(nextTab);
    }
  }, [searchParams, tab]);

  const { data: hub, isLoading: hubLoading, isError: hubError } = useQuery({
    queryKey: ['plans-subscriptions-hub'],
    queryFn: () => dashboardService.getPlansSubscriptionsHub(),
  });

  const { data: plans = [], isLoading: plansLoading } = useQuery({
    queryKey: ['plans'],
    queryFn: () => plansService.list({ page_size: 50 }),
    enabled: tab === 'plans' || tab === 'overview',
  });

  const { data: subscriptions = [], isLoading: subsLoading, refetch: refetchSubs } = useQuery({
    queryKey: ['subscriptions', subFilter],
    queryFn: () => subscriptionsService.list({
      page_size: 100,
      ordering: '-created_at',
      ...(subFilter ? { status: subFilter } : {}),
    }),
    enabled: tab === 'subscriptions' || tab === 'overview',
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['plans-subscriptions-hub'] });
    queryClient.invalidateQueries({ queryKey: ['plans'] });
    queryClient.invalidateQueries({ queryKey: ['subscriptions'] });
  };

  const openEditPlan = (plan) => {
    navigate(`/super-admin/plans/${plan.id}/edit?tab=${tab}`);
  };

  const deletePlan = async (plan) => {
    let preview;
    try {
      preview = await plansService.getDeletionPreview(plan.id);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to check plan usage.'));
      return;
    }

    const result = await alert.deletePlan({
      planName: plan.name,
      subscriptionCount: preview?.subscription_count ?? 0,
      reassignOptions: preview?.reassign_options ?? [],
      suggestedReassignPlanId: preview?.suggested_reassign_plan_id,
    });
    if (!result.isConfirmed) return;

    try {
      const params = result.value ? { reassign_to: result.value } : {};
      const response = await plansService.delete(plan.id, params);
      notify.success(response?.message || 'Plan deleted successfully.');
      invalidateAll();
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to delete plan.'));
    }
  };

  const activateSubscription = async (id) => {
    try {
      await subscriptionsService.activate(id);
      notify.success('Subscription activated.');
      refetchSubs();
      invalidateAll();
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to activate subscription.'));
    }
  };

  const suspendSubscription = async (id) => {
    const result = await alert.confirm({
      title: 'Suspend subscription?',
      text: 'The school will lose active subscription access.',
      confirmText: 'Suspend',
      danger: true,
      icon: 'warning',
    });
    if (!result.isConfirmed) return;
    try {
      await subscriptionsService.suspend(id);
      notify.warning('Subscription suspended.');
      refetchSubs();
      invalidateAll();
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to suspend subscription.'));
    }
  };

  if (hubLoading) return <PageSkeleton />;

  if (hubError) {
    return (
      <div className="apex-card p-5 text-center">
        <FiAlertTriangle size={32} className="text-warning mb-3" />
        <h5 className="fw-bold">Unable to load Plans & Subscriptions</h5>
      </div>
    );
  }

  const stats = hub?.stats ?? {};
  const statusBreakdown = hub?.status_breakdown ?? {};
  const totalSubs = stats.total_subscriptions || 1;

  return (
    <div>
      <PageHeader
        title="Plans & Subscriptions"
        subtitle="Manage pricing tiers, monitor school subscriptions, and track recurring revenue"
        actions={null}
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-xl">
          <StatCard title="Active Plans" value={stats.active_plans ?? 0} icon={FiLayers} color="primary" />
        </div>
        <div className="col-6 col-xl">
          <StatCard title="Active Subscriptions" value={stats.active_subscriptions ?? 0} icon={FiTrendingUp} color="success" />
        </div>
        <div className="col-6 col-xl">
          <StatCard title="On Trial" value={stats.trial_subscriptions ?? 0} icon={FiClock} color="warning" />
        </div>
        <div className="col-6 col-xl">
          <StatCard title="MRR" value={formatCurrency(stats.mrr)} icon={FiDollarSign} prefix="$" color="secondary" />
        </div>
        <div className="col-6 col-xl">
          <StatCard title="ARR" value={formatCurrency(stats.arr)} icon={FiDollarSign} prefix="$" color="accent" />
        </div>
      </div>

      <ul className="nav nav-tabs mb-4">
        {TABS.map((t) => (
          <li className="nav-item" key={t}>
            <button
              type="button"
              className={`nav-link text-capitalize${tab === t ? ' active' : ''}`}
              onClick={() => {
                setTab(t);
                setSearchParams(t === 'overview' ? {} : { tab: t });
              }}
            >
              {t}
            </button>
          </li>
        ))}
      </ul>

      {tab === 'overview' && (
        <div className="row g-3">
          <div className="col-lg-5">
            <motion.div className="apex-card p-4 h-100" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <h5 className="fw-bold mb-3">Plan Distribution</h5>
              <DoughnutChart data={hub?.plan_distribution ?? EMPTY_CHART} height={220} />
            </motion.div>
          </div>
          <div className="col-lg-7">
            <motion.div className="apex-card p-4 h-100" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <h5 className="fw-bold mb-3">Subscription Status</h5>
              <div className="d-flex flex-column gap-3">
                {Object.entries(statusBreakdown).map(([status, count]) => (
                  <div key={status}>
                    <div className="d-flex justify-content-between small mb-1">
                      <span className="text-capitalize">{status.replace('_', ' ')}</span>
                      <span className="fw-semibold">{count}</span>
                    </div>
                    <ProgressBar value={(count / totalSubs) * 100} showValue={false} height={6} />
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
          <div className="col-12">
            <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <h5 className="fw-bold mb-3">Renewals Due Within 7 Days</h5>
              {(hub?.expiring_soon ?? []).length === 0 ? (
                <p className="text-muted mb-0">No subscriptions expiring in the next 7 days.</p>
              ) : (
                <div className="row g-2">
                  {hub.expiring_soon.map((item) => (
                    <div key={item.id} className="col-md-6 col-xl-4">
                      <div className="p-3 rounded-3" style={{ background: 'var(--apex-bg)' }}>
                        <div className="fw-semibold small">{item.school}</div>
                        <div className="text-muted small">{item.plan} · {formatDate(item.ends_at)}</div>
                        <StatusBadge status={item.status} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          </div>
          <div className="col-12">
            <h5 className="fw-bold mb-3">Plan Catalog</h5>
            <div className="row g-3">
              {(hub?.plan_cards ?? []).map((plan) => (
                <div key={plan.id} className="col-md-6 col-xl-3">
                  <div className="apex-card p-4 h-100 d-flex flex-column">
                    <div className="d-flex justify-content-between align-items-start mb-2">
                      <h6 className="fw-bold mb-0">{plan.name}</h6>
                      <StatusBadge status={plan.is_active ? 'active' : 'inactive'} />
                    </div>
                    <p className="text-muted small mb-2">{plan.subscriber_count} subscribers · {plan.feature_count ?? plan.features?.length ?? 0} features</p>
                    <p className="fw-bold mb-1">${plan.price_monthly}/mo · ${plan.price_yearly}/yr</p>
                    <p className="text-muted small mb-2">
                      {plan.max_branches ?? 1} branches · {plan.trial_days}d trial · {plan.grace_period_days ?? 7}d grace
                    </p>
                    {plan.features?.length > 0 && (
                      <p className="small text-muted mb-3 flex-grow-1">{plan.features.slice(0, 4).join(' · ')}{plan.features.length > 4 ? '…' : ''}</p>
                    )}
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-primary d-flex align-items-center gap-1 align-self-start"
                      onClick={() => openEditPlan(plan)}
                    >
                      <FiEdit2 size={14} /> Edit Plan & Features
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === 'plans' && (
        <DataTable
          compact
          showRowNumbers={false}
          columns={[
            { key: 'name', label: 'Plan', accessor: 'name', sortable: true, width: '22%' },
            { key: 'slug', label: 'Slug', accessor: 'slug', width: '12%' },
            { key: 'price_monthly', label: 'Monthly', width: '11%', render: (r) => `$${Number(r.price_monthly).toFixed(2)}` },
            { key: 'price_yearly', label: 'Yearly', width: '11%', render: (r) => `$${Number(r.price_yearly).toFixed(2)}` },
            { key: 'trial_days', label: 'Trial', accessor: 'trial_days', width: '7%' },
            { key: 'is_active', label: 'Status', width: '12%', truncate: false, render: (r) => <StatusBadge status={r.is_active ? 'active' : 'inactive'} /> },
            { key: 'features', label: 'Features', width: '14%', render: (r) => `${r.features?.length || 0} enabled` },
            {
              key: 'actions', label: '', width: '11%', truncate: false,
              render: (row) => (
                <div className="apex-table-row-actions">
                  <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => openEditPlan(row)} title="Edit plan"><FiEdit2 size={14} /></button>
                  <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => deletePlan(row)} title="Delete plan"><FiTrash2 size={14} /></button>
                </div>
              ),
            },
          ]}
          data={plans}
          loading={plansLoading}
          searchable
          pageSize={10}
        />
      )}

      {tab === 'subscriptions' && (
        <>
          <div className="d-flex gap-2 mb-3 flex-wrap">
            {['', 'active', 'trial', 'grace_period', 'expired', 'suspended'].map((s) => (
              <button
                key={s || 'all'}
                type="button"
                className={`btn btn-sm ${subFilter === s ? 'btn-primary' : 'btn-outline-secondary'}`}
                onClick={() => setSubFilter(s)}
              >
                {s ? s.replace('_', ' ') : 'All'}
              </button>
            ))}
          </div>
          <DataTable
            compact
            showRowNumbers={false}
            columns={[
              { key: 'school', label: 'School', accessor: 'school', sortable: true, width: '20%' },
              { key: 'plan', label: 'Plan', accessor: 'plan', width: '12%' },
              { key: 'amount', label: 'Amount', width: '10%', render: (r) => `$${Number(r.amount || 0).toFixed(2)}/mo` },
              { key: 'billing_cycle', label: 'Billing', accessor: 'billing_cycle', width: '9%' },
              { key: 'status', label: 'Status', width: '11%', truncate: false, render: (r) => <StatusBadge status={r.status} /> },
              { key: 'next_billing', label: 'Next Billing', width: '12%', render: (r) => formatDate(r.next_billing) },
              { key: 'auto_renew', label: 'Renew', width: '6%', render: (r) => (r.auto_renew ? 'Yes' : 'No') },
              {
                key: 'actions', label: 'Actions', width: '10%', truncate: false,
                render: (row) => (
                  <div className="apex-table-row-actions">
                    {row.status !== 'active' && (
                      <button type="button" className="btn btn-sm btn-outline-success" onClick={() => activateSubscription(row.id)}>Activate</button>
                    )}
                    {row.status === 'active' && (
                      <button type="button" className="btn btn-sm btn-outline-warning" onClick={() => suspendSubscription(row.id)}>Suspend</button>
                    )}
                  </div>
                ),
              },
            ]}
            data={subscriptions}
            loading={subsLoading}
            searchable
            pageSize={12}
          />
        </>
      )}

    </div>
  );
}

export default PlansAndSubscriptions;