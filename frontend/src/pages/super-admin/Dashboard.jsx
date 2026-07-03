import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  FiGrid, FiUsers, FiDollarSign, FiTrendingUp, FiActivity,
  FiAlertTriangle, FiClock, FiServer, FiLayers, FiGlobe,
  FiUserCheck, FiBriefcase, FiPercent,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import StatCard from '../../components/StatCard';
import { LineChart, BarChart, DoughnutChart } from '../../components/Charts';
import DataTable from '../../components/DataTable';
import StatusBadge from '../../components/StatusBadge';
import ProgressBar from '../../components/ProgressBar';
import ActivityFeed from '../../components/ActivityFeed';
import SchoolNameWithBadge from '../../components/SchoolNameWithBadge';
import { PageSkeleton } from '../../components/LoadingSkeleton';
import { dashboardService } from '../../services/dashboardService';

const EMPTY_CHART = { labels: [], datasets: [] };

const formatCurrency = (value) => {
  const num = Number(value) || 0;
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toLocaleString();
};

export function SuperAdminDashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['super-admin-dashboard'],
    queryFn: () => dashboardService.getSuperAdminStats(),
    refetchInterval: 60000,
  });

  if (isLoading) return <PageSkeleton />;

  if (isError) {
    return (
      <div className="apex-card p-5 text-center">
        <FiAlertTriangle size={32} className="text-warning mb-3" />
        <h5 className="fw-bold">Unable to load dashboard</h5>
        <p className="text-muted mb-0">Check your connection and try refreshing the page.</p>
      </div>
    );
  }

  const stats = data?.stats ?? {};
  const health = data?.system_health ?? {};
  const storagePercent = health.storage_cap_mb
    ? (Number(health.storage_used_mb) / Number(health.storage_cap_mb)) * 100
    : 0;
  const topSchools = data?.top_schools ?? [];
  const maxStudents = topSchools[0]?.students ?? 1;

  return (
    <div>
      <PageHeader
        title="Platform Dashboard"
        subtitle="Real-time overview of schools, revenue, subscriptions, and system health"
      />

      <div className="row g-3 mb-4">
        <div className="col-sm-6 col-xl-3">
          <StatCard
            title="Total Schools"
            value={stats.total_schools ?? 0}
            icon={FiGrid}
            trend={stats.growth_rate ?? 0}
            trendLabel="vs last month"
            color="primary"
            delay={0}
          />
        </div>
        <div className="col-sm-6 col-xl-3">
          <StatCard
            title="Monthly Recurring Revenue"
            value={formatCurrency(stats.monthly_revenue)}
            icon={FiDollarSign}
            prefix="$"
            color="secondary"
            delay={0.05}
            trendLabel={`ARR $${formatCurrency(stats.arr)}`}
          />
        </div>
        <div className="col-sm-6 col-xl-3">
          <StatCard
            title="Active Subscriptions"
            value={stats.active_subscriptions ?? 0}
            icon={FiTrendingUp}
            color="success"
            delay={0.1}
            trendLabel={`${stats.trial_subscriptions ?? 0} on trial`}
          />
        </div>
        <div className="col-sm-6 col-xl-3">
          <StatCard
            title="Platform Students"
            value={stats.total_students ?? 0}
            icon={FiUsers}
            color="accent"
            delay={0.15}
            trendLabel={`${stats.total_staff ?? 0} staff across schools`}
          />
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-6 col-md-4 col-xl-2">
          <StatCard title="Active Schools" value={stats.active_schools ?? 0} icon={FiUserCheck} color="success" delay={0.2} />
        </div>
        <div className="col-6 col-md-4 col-xl-2">
          <StatCard title="Trial Schools" value={stats.trial_subscriptions ?? 0} icon={FiClock} color="warning" delay={0.22} />
        </div>
        <div className="col-6 col-md-4 col-xl-2">
          <StatCard title="Pending Review" value={stats.pending_schools ?? 0} icon={FiAlertTriangle} color="warning" delay={0.24} />
        </div>
        <div className="col-6 col-md-4 col-xl-2">
          <StatCard title="Active Users (24h)" value={stats.active_users_24h ?? 0} icon={FiActivity} color="primary" delay={0.26} />
        </div>
        <div className="col-6 col-md-4 col-xl-2">
          <StatCard title="Churn Rate" value={stats.churn_rate ?? 0} icon={FiPercent} suffix="%" color="secondary" delay={0.28} />
        </div>
        <div className="col-6 col-md-4 col-xl-2">
          <StatCard
            title="Revenue MTD"
            value={formatCurrency(stats.revenue_mtd)}
            icon={FiBriefcase}
            prefix="$"
            color="primary"
            delay={0.3}
          />
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-lg-4">
          <motion.div
            className="apex-card p-4 h-100"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <div className="d-flex align-items-center gap-2 mb-3">
              <FiServer style={{ color: 'var(--apex-primary)' }} />
              <h5 className="fw-bold mb-0">System Health</h5>
            </div>
            <div className="d-flex flex-column gap-3">
              <div className="d-flex justify-content-between align-items-center">
                <span className="small text-muted">API Status</span>
                <StatusBadge status={health.api_status ?? 'unknown'} />
              </div>
              <div className="d-flex justify-content-between align-items-center">
                <span className="small text-muted">Database</span>
                <StatusBadge status={health.database ?? 'unknown'} />
              </div>
              <div className="d-flex justify-content-between align-items-center">
                <span className="small text-muted">Platform Uptime</span>
                <span className="small fw-semibold text-success">{health.uptime_percent ?? 0}%</span>
              </div>
              <div className="d-flex justify-content-between align-items-center">
                <span className="small text-muted">Active Sessions</span>
                <span className="small fw-semibold">{health.active_sessions ?? 0}</span>
              </div>
              <ProgressBar
                label="Storage Utilization"
                value={storagePercent}
                color="var(--apex-primary)"
              />
              <p className="text-muted small mb-0">
                {health.storage_used_mb ?? 0} MB of {health.storage_cap_mb ?? 0} MB allocated
              </p>
            </div>
          </motion.div>
        </div>

        <div className="col-lg-4">
          <motion.div
            className="apex-card p-4 h-100"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
          >
            <div className="d-flex align-items-center gap-2 mb-3">
              <FiLayers style={{ color: 'var(--apex-secondary)' }} />
              <h5 className="fw-bold mb-0">Subscription Mix</h5>
            </div>
            <DoughnutChart
              data={data?.subscription_chart ?? EMPTY_CHART}
              height={200}
            />
            <div className="mt-3 d-flex flex-column gap-2">
              {(data?.plan_breakdown ?? []).length === 0 ? (
                <p className="text-muted small mb-0">No active subscriptions yet.</p>
              ) : (
                (data?.plan_breakdown ?? []).map((plan) => (
                  <div key={plan.plan} className="d-flex justify-content-between small">
                    <span className="text-muted">{plan.plan}</span>
                    <span className="fw-semibold">{plan.count} ({plan.percent}%)</span>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        </div>

        <div className="col-lg-4">
          <motion.div
            className="apex-card p-4 h-100"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <div className="d-flex align-items-center gap-2 mb-3">
              <FiTrendingUp style={{ color: 'var(--apex-primary)' }} />
              <h5 className="fw-bold mb-0">Growth Metrics</h5>
            </div>
            <div className="d-flex flex-column gap-4">
              <ProgressBar
                label="Trial → Paid Conversion"
                value={stats.conversion_rate ?? 0}
                color="var(--apex-primary)"
              />
              <ProgressBar
                label="School Activation Rate"
                value={stats.total_schools ? (stats.active_schools / stats.total_schools) * 100 : 0}
                color="#059669"
              />
              <ProgressBar
                label="Subscription Retention"
                value={Math.max(0, 100 - (stats.churn_rate ?? 0))}
                color="var(--apex-secondary)"
              />
              <div className="row g-2 text-center">
                <div className="col-4">
                  <p className="text-muted small mb-0">Suspended</p>
                  <p className="fw-bold mb-0 text-danger">{stats.suspended_schools ?? 0}</p>
                </div>
                <div className="col-4">
                  <p className="text-muted small mb-0">Grace Period</p>
                  <p className="fw-bold mb-0 text-warning">{stats.grace_period_subscriptions ?? 0}</p>
                </div>
                <div className="col-4">
                  <p className="text-muted small mb-0">Failed Payments</p>
                  <p className="fw-bold mb-0">{stats.failed_payments_30d ?? 0}</p>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-lg-8">
          <motion.div
            className="apex-card p-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35 }}
          >
            <h5 className="fw-bold mb-1">Revenue Trend</h5>
            <p className="text-muted small mb-3">Completed payment transactions — last 6 months</p>
            <LineChart data={data?.revenue_chart ?? EMPTY_CHART} height={280} />
          </motion.div>
        </div>
        <div className="col-lg-4">
          <motion.div
            className="apex-card p-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <h5 className="fw-bold mb-1">New School Signups</h5>
            <p className="text-muted small mb-3">Monthly registrations</p>
            <BarChart data={data?.schools_chart ?? EMPTY_CHART} height={280} />
          </motion.div>
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-lg-6">
          <motion.div
            className="apex-card p-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.45 }}
          >
            <h5 className="fw-bold mb-1">Enrollment Growth</h5>
            <p className="text-muted small mb-3">New students onboarded platform-wide</p>
            <LineChart data={data?.enrollment_chart ?? EMPTY_CHART} height={240} />
          </motion.div>
        </div>
        <div className="col-lg-6">
          <motion.div
            className="apex-card p-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <div className="d-flex align-items-center gap-2 mb-1">
              <FiGlobe style={{ color: 'var(--apex-primary)' }} />
              <h5 className="fw-bold mb-0">Geographic Distribution</h5>
            </div>
            <p className="text-muted small mb-3">Schools by country</p>
            <BarChart data={data?.country_chart ?? EMPTY_CHART} height={240} />
          </motion.div>
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-lg-8">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.55 }}>
            <h5 className="fw-bold mb-3">Recently Registered Schools</h5>
            <DataTable
              columns={[
                {
                  key: 'name',
                  label: 'School',
                  accessor: 'name',
                  sortable: true,
                  render: (row) => (
                    <SchoolNameWithBadge
                      name={row.name}
                      planSlug={row.plan_slug}
                      size="sm"
                    />
                  ),
                },
                { key: 'plan', label: 'Plan', accessor: 'plan' },
                { key: 'country', label: 'Country', accessor: 'country' },
                { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
                { key: 'students', label: 'Students', accessor: 'students', sortable: true },
              ]}
              data={data?.recent_schools ?? []}
              searchable={false}
            />
          </motion.div>
        </div>
        <div className="col-lg-4">
          <motion.div
            className="apex-card p-4 h-100"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
          >
            <h5 className="fw-bold mb-3">Live Activity Feed</h5>
            <ActivityFeed items={data?.recent_activity ?? []} />
          </motion.div>
        </div>
      </div>

      <motion.div
        className="apex-card p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.65 }}
      >
        <h5 className="fw-bold mb-3">Top Schools by Enrollment</h5>
        {topSchools.length === 0 ? (
          <p className="text-muted mb-0">No schools registered yet.</p>
        ) : (
          <div className="row g-3">
            {topSchools.map((school, index) => (
              <div key={school.id} className="col-md-6 col-xl-4">
                <div className="p-3 rounded-3" style={{ background: 'var(--apex-bg)' }}>
                  <div className="d-flex justify-content-between align-items-center mb-2">
                    <span className="fw-semibold small">
                      <span className="text-muted me-2">#{index + 1}</span>
                      <SchoolNameWithBadge
                        name={school.name}
                        planSlug={school.plan_slug}
                        size="sm"
                      />
                    </span>
                    <span className="badge rounded-pill" style={{ background: 'var(--apex-primary)', color: '#fff' }}>
                      {school.students}
                    </span>
                  </div>
                  <ProgressBar
                    value={school.students}
                    max={maxStudents || 1}
                    showValue={false}
                    color="var(--apex-primary)"
                    height={6}
                  />
                  <p className="text-muted small mb-0 mt-1">{school.country}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}

export default SuperAdminDashboard;