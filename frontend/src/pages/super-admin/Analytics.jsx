import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { FiAlertTriangle } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import { LineChart, BarChart, DoughnutChart } from '../../components/Charts';
import ProgressBar from '../../components/ProgressBar';
import StatCard from '../../components/StatCard';
import { PageSkeleton } from '../../components/LoadingSkeleton';
import { dashboardService } from '../../services/dashboardService';
import { FiGrid, FiUsers, FiDollarSign, FiTrendingUp } from 'react-icons/fi';

const EMPTY_CHART = { labels: [], datasets: [] };

export function Analytics() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['platform-analytics'],
    queryFn: () => dashboardService.getPlatformAnalytics(),
    refetchInterval: 120000,
  });

  if (isLoading) return <PageSkeleton />;

  if (isError) {
    return (
      <div className="apex-card p-5 text-center">
        <FiAlertTriangle size={32} className="text-warning mb-3" />
        <h5 className="fw-bold">Unable to load analytics</h5>
        <button className="btn btn-primary btn-sm mt-2" onClick={() => refetch()}>Retry</button>
      </div>
    );
  }

  const health = data?.platform_health ?? {};
  const summary = data?.summary ?? {};

  return (
    <div>
      <PageHeader title="Analytics" subtitle="Platform-wide performance insights" />

      <div className="row g-3 mb-4">
        <div className="col-sm-6 col-xl-3">
          <StatCard title="Total Schools" value={summary.total_schools ?? 0} icon={FiGrid} color="primary" />
        </div>
        <div className="col-sm-6 col-xl-3">
          <StatCard title="Active Subscriptions" value={summary.active_subscriptions ?? 0} icon={FiTrendingUp} color="success" />
        </div>
        <div className="col-sm-6 col-xl-3">
          <StatCard title="Platform Students" value={summary.total_students ?? 0} icon={FiUsers} color="accent" />
        </div>
        <div className="col-sm-6 col-xl-3">
          <StatCard title="MRR" value={summary.mrr ?? 0} icon={FiDollarSign} prefix="$" color="secondary" />
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-lg-8">
          <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h5 className="fw-bold mb-3">Monthly Recurring Revenue</h5>
            <LineChart data={data?.revenue_chart ?? EMPTY_CHART} height={320} />
          </motion.div>
        </div>
        <div className="col-lg-4">
          <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h5 className="fw-bold mb-3">Plan Distribution</h5>
            <DoughnutChart data={data?.plan_distribution ?? EMPTY_CHART} height={320} />
          </motion.div>
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-lg-6">
          <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h5 className="fw-bold mb-3">Payment Revenue (6 months)</h5>
            <LineChart data={data?.payment_revenue_chart ?? EMPTY_CHART} height={250} />
          </motion.div>
        </div>
        <div className="col-lg-6">
          <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h5 className="fw-bold mb-3">Enrollment Growth</h5>
            <LineChart data={data?.enrollment_chart ?? EMPTY_CHART} height={250} />
          </motion.div>
        </div>
      </div>

      <div className="row g-3">
        <div className="col-md-6">
          <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h5 className="fw-bold mb-3">School Growth (Quarterly)</h5>
            <BarChart data={data?.school_growth_chart ?? EMPTY_CHART} height={250} />
          </motion.div>
        </div>
        <div className="col-md-6">
          <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h5 className="fw-bold mb-3">Platform Health</h5>
            <div className="d-flex flex-column gap-3 mt-3">
              <ProgressBar label="Uptime" value={health.uptime ?? 0} />
              <ProgressBar label="Customer Satisfaction" value={health.customer_satisfaction ?? 0} color="var(--apex-secondary)" />
              <ProgressBar label="Feature Adoption" value={health.feature_adoption ?? 0} />
              <ProgressBar label="Support Resolution" value={health.support_resolution ?? 0} color="#059669" />
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

export default Analytics;