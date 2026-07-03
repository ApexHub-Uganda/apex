import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  FiCreditCard, FiDollarSign, FiAlertTriangle, FiCheckCircle,
  FiClock, FiTrendingUp,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import StatCard from '../../components/StatCard';
import StatusBadge from '../../components/StatusBadge';
import DataTable from '../../components/DataTable';
import { LineChart, BarChart } from '../../components/Charts';
import ProgressBar from '../../components/ProgressBar';
import { PageSkeleton } from '../../components/LoadingSkeleton';
import { dashboardService } from '../../services/dashboardService';
import { billingService } from '../../services/moduleService';

const EMPTY_CHART = { labels: [], datasets: [] };

const formatDate = (v) => (v ? new Date(v).toLocaleString() : '—');
const formatMoney = (v, currency = 'USD') => {
  const n = Number(v) || 0;
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(n);
};

export function BillingOperations() {
  const [statusFilter, setStatusFilter] = useState('');

  const { data: hub, isLoading: hubLoading, isError: hubError, refetch } = useQuery({
    queryKey: ['billing-operations'],
    queryFn: () => dashboardService.getBillingOperations(),
    refetchInterval: 120000,
  });

  const { data: transactions = [], isLoading: txnLoading } = useQuery({
    queryKey: ['billing-transactions', statusFilter],
    queryFn: () => billingService.listTransactions({
      page_size: 100,
      ordering: '-created_at',
      ...(statusFilter ? { status: statusFilter } : {}),
    }),
  });

  if (hubLoading) return <PageSkeleton />;

  if (hubError) {
    return (
      <div className="apex-card p-5 text-center">
        <FiAlertTriangle size={32} className="text-warning mb-3" />
        <h5 className="fw-bold">Unable to load Billing & Payments</h5>
        <button className="btn btn-primary btn-sm mt-2" onClick={() => refetch()}>Retry</button>
      </div>
    );
  }

  const stats = hub?.stats ?? {};
  const statusBreakdown = hub?.status_breakdown ?? {};
  const totalTxn = Object.values(statusBreakdown).reduce((a, b) => a + b, 0) || 1;

  return (
    <div>
      <PageHeader
        title="Billing & Payments"
        subtitle="Monitor revenue collection, failed payments, providers, and transaction ledger"
      />

      <div className="row g-3 mb-4">
        <div className="col-6 col-xl">
          <StatCard title="Total Revenue" value={formatMoney(stats.revenue_total)} icon={FiDollarSign} color="primary" />
        </div>
        <div className="col-6 col-xl">
          <StatCard title="Revenue MTD" value={formatMoney(stats.revenue_mtd)} icon={FiTrendingUp} color="success" />
        </div>
        <div className="col-6 col-xl">
          <StatCard title="Failed (30d)" value={stats.failed_count_30d ?? 0} icon={FiAlertTriangle} color="warning" />
        </div>
        <div className="col-6 col-xl">
          <StatCard title="Success Rate" value={`${stats.success_rate ?? 0}%`} icon={FiCheckCircle} color="accent" />
        </div>
        <div className="col-6 col-xl">
          <StatCard title="Pending" value={stats.pending_count ?? 0} icon={FiClock} color="secondary" />
        </div>
        <div className="col-6 col-xl">
          <StatCard title="Active Providers" value={stats.active_providers ?? 0} icon={FiCreditCard} color="primary" />
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-lg-7">
          <motion.div className="apex-card p-4 h-100" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h5 className="fw-bold mb-3">Collected Revenue (6 months)</h5>
            <LineChart data={hub?.revenue_chart ?? EMPTY_CHART} height={280} />
          </motion.div>
        </div>
        <div className="col-lg-5">
          <motion.div className="apex-card p-4 h-100" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h5 className="fw-bold mb-3">Transaction Status</h5>
            <div className="d-flex flex-column gap-3">
              {Object.entries(statusBreakdown).map(([status, count]) => (
                <div key={status}>
                  <div className="d-flex justify-content-between small mb-1">
                    <span className="text-capitalize">{status}</span>
                    <span className="fw-semibold">{count}</span>
                  </div>
                  <ProgressBar value={(count / totalTxn) * 100} showValue={false} height={6} />
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-lg-6">
          <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h5 className="fw-bold mb-3">Failed Payments (6 months)</h5>
            <BarChart data={hub?.failed_chart ?? EMPTY_CHART} height={240} />
          </motion.div>
        </div>
        <div className="col-lg-6">
          <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h5 className="fw-bold mb-3">Payment Providers</h5>
            {(hub?.providers ?? []).length === 0 ? (
              <p className="text-muted mb-0">No payment providers configured.</p>
            ) : (
              <div className="row g-2">
                {hub.providers.map((provider) => (
                  <div key={provider.id} className="col-md-6">
                    <div className="p-3 rounded-3 h-100" style={{ background: 'var(--apex-bg)' }}>
                      <div className="d-flex justify-content-between align-items-start mb-1">
                        <span className="fw-semibold small">{provider.name}</span>
                        <StatusBadge status={provider.is_active ? 'active' : 'inactive'} />
                      </div>
                      <div className="text-muted small">
                        {provider.slug}
                        {provider.method_type && (
                          <span className="ms-2 text-capitalize">
                            · {(provider.method_type || 'card').replace('_', ' ')}
                          </span>
                        )}
                      </div>
                      {provider.is_sandbox && (
                        <span className="badge bg-warning-subtle text-warning mt-2">Sandbox</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </div>
      </div>

      <motion.div className="apex-card p-4 mb-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <h5 className="fw-bold mb-3">Failed Payment Recovery Queue</h5>
        {(hub?.failed_queue ?? []).length === 0 ? (
          <p className="text-muted mb-0">No failed payments in the last 30 days.</p>
        ) : (
          <DataTable
            compact
            columns={[
              { key: 'school', label: 'School', accessor: 'school', width: '22%' },
              { key: 'amount', label: 'Amount', width: '14%', render: (r) => formatMoney(r.amount, r.currency) },
              { key: 'provider', label: 'Provider', accessor: 'provider', width: '16%' },
              { key: 'reference', label: 'Reference', accessor: 'reference', width: '22%' },
              { key: 'created_at', label: 'Failed At', width: '18%', render: (r) => formatDate(r.created_at) },
            ]}
            data={hub.failed_queue}
            pageSize={5}
          />
        )}
      </motion.div>

      <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <h5 className="fw-bold mb-3">Transaction Ledger</h5>
        <div className="d-flex gap-2 mb-3 flex-wrap">
          {['', 'completed', 'failed', 'pending', 'refunded'].map((s) => (
            <button
              key={s || 'all'}
              type="button"
              className={`btn btn-sm ${statusFilter === s ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => setStatusFilter(s)}
            >
              {s ? s.charAt(0).toUpperCase() + s.slice(1) : 'All'}
            </button>
          ))}
        </div>
        <DataTable
          compact
          columns={[
            { key: 'school', label: 'School', accessor: 'school', sortable: true, width: '18%' },
            { key: 'amount', label: 'Amount', width: '12%', render: (r) => formatMoney(r.amount, r.currency) },
            { key: 'status', label: 'Status', width: '12%', render: (r) => <StatusBadge status={r.status} /> },
            { key: 'provider_name', label: 'Provider', accessor: 'provider_name', width: '14%' },
            { key: 'reference', label: 'Reference', accessor: 'reference', width: '18%' },
            { key: 'created_at', label: 'Date', width: '16%', render: (r) => formatDate(r.created_at) },
          ]}
          data={transactions}
          loading={txnLoading}
          searchable
          pageSize={12}
        />
      </motion.div>
    </div>
  );
}

export default BillingOperations;