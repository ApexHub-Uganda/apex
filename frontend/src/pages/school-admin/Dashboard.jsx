import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FiAlertTriangle, FiArrowRight, FiClock, FiLayers, FiLock, FiTrendingUp,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import StatCard from '../../components/StatCard';
import { LineChart, BarChart, DoughnutChart } from '../../components/Charts';
import ProgressBar from '../../components/ProgressBar';
import StatusBadge from '../../components/StatusBadge';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { PageSkeleton } from '../../components/LoadingSkeleton';
import { dashboardService } from '../../services/dashboardService';
import { useTenant } from '../../hooks/useTenant';
import { resolveFeatureIcon } from '../../utils/featureIcons';
import {
  MODULE_HIGHLIGHTS,
  WIDGET_STAT_MAP,
  formatStatValue,
  getPlanMeta,
} from '../../config/schoolDashboard';

const EMPTY_CHART = { labels: [], datasets: [] };

const sectionMotion = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.3 },
};

function PlanBanner({ subscription, planUsage, enabledCount, navigationCount }) {
  if (!subscription) return null;

  const meta = getPlanMeta(subscription.plan_slug);
  const trialEnd = subscription.trial_ends_at ? new Date(subscription.trial_ends_at) : null;
  const daysLeft = trialEnd
    ? Math.max(0, Math.ceil((trialEnd - Date.now()) / (1000 * 60 * 60 * 24)))
    : null;

  return (
    <motion.div className="school-plan-banner mb-4" {...sectionMotion}>
      <div className="d-flex flex-wrap align-items-start justify-content-between gap-3">
        <div>
          <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
            <span className={`school-plan-badge ${meta.badgeClass}`}>
              <FiLayers size={14} className="me-1" />
              {subscription.plan_name || meta.label}
            </span>
            <StatusBadge status={subscription.status} />
            {subscription.status === 'trial' && daysLeft !== null && (
              <span className="school-plan-trial small">
                <FiClock size={13} className="me-1" />
                {daysLeft} day{daysLeft === 1 ? '' : 's'} left in trial
              </span>
            )}
          </div>
          <p className="text-muted small mb-0">{meta.description}</p>
        </div>
        <div className="school-plan-summary text-end">
          <div className="small text-muted">Active modules</div>
          <div className="fw-bold" style={{ fontSize: '1.25rem' }}>
            {navigationCount}
            <span className="text-muted fw-normal small ms-1">/ {enabledCount} features</span>
          </div>
        </div>
      </div>

      {planUsage?.students && (
        <div className="row g-3 mt-3 pt-3 border-top">
          <div className="col-md-6">
            <ProgressBar
              label={`Students (${planUsage.students.used} / ${planUsage.students.limit})`}
              value={planUsage.students.percent}
              color={planUsage.students.percent >= 90 ? '#DC2626' : 'var(--apex-primary)'}
            />
          </div>
          <div className="col-md-6">
            <ProgressBar
              label={`Staff (${planUsage.staff.used} / ${planUsage.staff.limit})`}
              value={planUsage.staff.percent}
              color={planUsage.staff.percent >= 90 ? '#DC2626' : 'var(--apex-secondary)'}
            />
          </div>
        </div>
      )}
    </motion.div>
  );
}

function ModuleHighlightCard({ module, stats }) {
  const Icon = resolveFeatureIcon(module.icon);
  const moduleStats = stats?.[module.key] || {};

  return (
    <motion.div className="school-module-card h-100" whileHover={{ y: -3 }}>
      <div className="d-flex align-items-center justify-content-between mb-3">
        <div className="d-flex align-items-center gap-2">
          <span className="school-module-icon">
            <Icon size={18} />
          </span>
          <h6 className="fw-bold mb-0">{module.label}</h6>
        </div>
        <Link to={module.path} className="btn btn-sm btn-link p-0 text-decoration-none">
          Open <FiArrowRight size={14} />
        </Link>
      </div>
      <div className="row g-2">
        {module.metrics.map((metric) => (
          <div key={metric.field} className="col-4">
            <div className="school-module-metric">
              <div className={`fw-bold ${metric.warn && moduleStats[metric.field] > 0 ? 'text-warning' : ''}`}>
                {moduleStats[metric.field] ?? 0}{metric.suffix || ''}
              </div>
              <div className="text-muted" style={{ fontSize: '0.7rem' }}>{metric.label}</div>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function UpgradePanel({ suggestions, planSlug }) {
  if (!suggestions?.length) return null;

  const isTopTier = planSlug === 'premium_plus';

  return (
    <motion.div className="apex-card p-4 h-100 school-upgrade-panel" {...sectionMotion}>
      <div className="d-flex align-items-center gap-2 mb-2">
        <FiLock style={{ color: '#D97706' }} />
        <h5 className="fw-bold mb-0">
          {isTopTier ? 'Explore More' : 'Unlock More Modules'}
        </h5>
      </div>
      <p className="text-muted small mb-3">
        {isTopTier
          ? 'Browse additional platform capabilities available to your school.'
          : 'Upgrade your plan to access these modules and expand school operations.'}
      </p>
      <div className="d-flex flex-column gap-2">
        {suggestions.map((item) => {
          const Icon = resolveFeatureIcon(item.icon);
          return (
            <div key={item.feature_key} className="school-upgrade-item">
              <span className="school-upgrade-item-icon">
                <Icon size={15} />
              </span>
              <span className="small fw-medium flex-grow-1">{item.label}</span>
              <FiLock size={13} className="text-muted" />
            </div>
          );
        })}
      </div>
      <button type="button" className="btn btn-outline-primary btn-sm w-100 mt-3" disabled>
        <FiTrendingUp className="me-1" /> Request Plan Upgrade
      </button>
    </motion.div>
  );
}

export function SchoolAdminDashboard() {
  const { tenant, dashboardWidgets, navigationMenu, enabledFeatureKeys } = useTenant();

  const { data, isLoading } = useQuery({
    queryKey: ['school-admin-dashboard', tenant?.id],
    queryFn: () => dashboardService.getSchoolAdminStats(),
    refetchInterval: 60000,
    retry: 1,
  });

  const resolvedSections = useMemo(() => {
    const base = data?.sections ?? {};
    if (Object.keys(base).length) return base;
    const out = {};
    MODULE_HIGHLIGHTS.forEach((m) => {
      const enabled = navigationMenu.some((n) => n.path === m.path)
        || enabledFeatureKeys.some((k) => k.includes(m.key) || k === m.sectionKey);
      out[m.sectionKey] = enabled;
    });
    out.attendance = enabledFeatureKeys.includes('student_attendance');
    out.finance = enabledFeatureKeys.includes('student_billing');
    out.enrollment = enabledFeatureKeys.includes('admissions');
    out.classes = enabledFeatureKeys.includes('classes');
    out.reports = enabledFeatureKeys.includes('reports');
    return out;
  }, [data?.sections, enabledFeatureKeys, navigationMenu]);

  const stats = data?.stats ?? {};
  const widgets = useMemo(() => {
    const apiWidgets = data?.widgets?.length ? data.widgets : dashboardWidgets;
    return apiWidgets?.length ? apiWidgets : [];
  }, [data?.widgets, dashboardWidgets]);

  const activeModules = useMemo(
    () => MODULE_HIGHLIGHTS.filter((m) => resolvedSections[m.sectionKey]),
    [resolvedSections],
  );

  if (isLoading && !data) return <PageSkeleton />;

  const subscription = data?.subscription ?? tenant?.subscription;
  const planSlug = subscription?.plan_slug;
  const showAttendance = resolvedSections.attendance;
  const showFinance = resolvedSections.finance;
  const showEnrollment = resolvedSections.enrollment;
  const showClassChart = resolvedSections.classes;
  const hasChartData = data?.attendance_chart || data?.finance_chart || data?.enrollment_chart || data?.class_chart;
  const hasCharts = showAttendance || showFinance || showEnrollment || showClassChart;
  const statsAreEmpty = !stats.total_students && !stats.total_staff && widgets.length > 0;
  const statColClass = widgets.length > 4 ? 'col-sm-6 col-lg-4 col-xl-2' : 'col-sm-6 col-xl-3';

  return (
    <div className="school-dashboard">
      <PageHeader
        title={`${tenant?.name || 'School'} Dashboard`}
        subtitle="Plan-aware overview — modules and insights match your subscription"
      />

      <PlanBanner
        subscription={subscription}
        planUsage={data?.plan_usage}
        enabledCount={enabledFeatureKeys.length}
        navigationCount={navigationMenu.length}
      />

      <AnimatePresence mode="popLayout">
        {widgets.length > 0 && (
          <motion.div className="row g-3 mb-4" key="stat-widgets" {...sectionMotion}>
            {widgets.map((widget, idx) => {
              const map = WIDGET_STAT_MAP[widget.key] || { field: widget.key, color: 'primary' };
              const Icon = resolveFeatureIcon(widget.icon);
              const rawValue = stats[map.field] ?? 0;
              const displayValue = map.format === 'currency'
                ? formatStatValue(rawValue, map)
                : rawValue;
              const prefix = map.format === 'currency' && rawValue > 0 ? '$' : (map.prefix || '');

              return (
                <div className={statColClass} key={widget.key || widget.feature_key}>
                  <StatCard
                    title={widget.label || map.fallbackLabel || widget.key}
                    value={displayValue}
                    icon={Icon}
                    color={map.color}
                    suffix={map.suffix || ''}
                    prefix={prefix}
                    delay={idx * 0.06}
                    trendLabel={
                      widget.key === 'finance' && stats.fee_collected_mtd
                        ? `$${formatStatValue(stats.fee_collected_mtd, { format: 'currency' })} collected MTD`
                        : widget.key === 'analytics'
                          ? 'Class capacity utilization'
                          : undefined
                    }
                  />
                </div>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>

      {statsAreEmpty && (
        <div className="apex-card mb-4">
          <ModuleEmptyState
            title="Your school dashboard is ready"
            message="Statistics will appear once you add students, staff, and start recording attendance and fees. Use the quick links below or the sidebar to create your first records."
            actionLabel="Add students"
            actionHref="/school-admin/students"
          />
        </div>
      )}

      <AnimatePresence mode="popLayout">
        {showAttendance && (
          <motion.div className="row g-3 mb-4" key="attendance-row" {...sectionMotion}>
            <div className="col-lg-8">
              <div className="apex-card p-4 h-100">
                <h5 className="fw-bold mb-1">Weekly Attendance</h5>
                <p className="text-muted small mb-3">Student presence over the last 5 school days</p>
                {data?.attendance_chart ? (
                  <BarChart data={data.attendance_chart} height={280} />
                ) : (
                  <ModuleEmptyState
                    title="No attendance recorded yet"
                    message="Mark student attendance to see weekly trends here."
                    actionLabel="Record attendance"
                    actionHref="/school-admin/attendance"
                  />
                )}
              </div>
            </div>
            <div className="col-lg-4">
              <div className="apex-card p-4 h-100">
                <h5 className="fw-bold mb-3">Quick Stats</h5>
                <div className="d-flex flex-column gap-3 mt-2">
                  <ProgressBar label="Attendance Rate" value={stats.attendance_rate ?? 0} />
                  {showFinance && (
                    <ProgressBar
                      label="Fee Collection"
                      value={stats.fee_collection ?? 0}
                      color="var(--apex-secondary)"
                    />
                  )}
                  {resolvedSections.classes && (
                    <ProgressBar label="Class Capacity" value={stats.class_capacity ?? 0} />
                  )}
                  {resolvedSections.staff_attendance && (
                    <div className="small text-muted pt-1">
                      Staff attendance tracking is enabled on your plan.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence mode="popLayout">
        {(showFinance || showEnrollment || showClassChart) && (
          <motion.div className="row g-3 mb-4" key="analytics-row" {...sectionMotion}>
            {showFinance && (
              <div className={showEnrollment || showClassChart ? 'col-lg-6' : 'col-12'}>
                <div className="apex-card p-4 h-100">
                  <h5 className="fw-bold mb-1">Fee Collection Trend</h5>
                  <p className="text-muted small mb-3">Monthly collections — last 6 months</p>
                  {data?.finance_chart ? (
                    <LineChart data={data.finance_chart} height={250} />
                  ) : (
                    <ModuleEmptyState
                      title="No fee collections yet"
                      message="Record fee payments to track collection trends."
                      actionLabel="Open finance"
                      actionHref="/school-admin/finance"
                    />
                  )}
                </div>
              </div>
            )}
            {showEnrollment && (
              <div className={showFinance ? 'col-lg-6' : 'col-lg-8'}>
                <div className="apex-card p-4 h-100">
                  <h5 className="fw-bold mb-1">Enrollment Growth</h5>
                  <p className="text-muted small mb-3">New student registrations per month</p>
                  {data?.enrollment_chart ? (
                    <LineChart data={data.enrollment_chart} height={250} />
                  ) : (
                    <ModuleEmptyState
                      title="No enrollments yet"
                      message="Admit students to see enrollment growth over time."
                      actionLabel="Add students"
                      actionHref="/school-admin/students"
                    />
                  )}
                </div>
              </div>
            )}
            {showClassChart && (
              <div className={showFinance && showEnrollment ? 'col-12' : showFinance || showEnrollment ? 'col-lg-6' : 'col-lg-4'}>
                <div className="apex-card p-4 h-100">
                  <h5 className="fw-bold mb-1">Students by Class</h5>
                  <p className="text-muted small mb-3">Enrollment distribution</p>
                  {data?.class_chart?.labels?.length ? (
                    <DoughnutChart data={data.class_chart} height={showFinance && showEnrollment ? 220 : 250} />
                  ) : (
                    <ModuleEmptyState
                      title="No class assignments yet"
                      message="Create classes and assign students to see distribution."
                      actionLabel="Manage classes"
                      actionHref="/school-admin/classes"
                    />
                  )}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence mode="popLayout">
        {resolvedSections.reports && (
          <motion.div className="row g-3 mb-4" key="reports-row" {...sectionMotion}>
            <div className="col-12">
              <div className="apex-card p-4 d-flex flex-wrap align-items-center justify-content-between gap-3">
                <div>
                  <h5 className="fw-bold mb-1">Reports & Analytics</h5>
                  <p className="text-muted small mb-0">
                    Your plan includes advanced reporting — generate attendance, finance, and academic reports.
                  </p>
                </div>
                <Link to="/school-admin/reports" className="btn btn-primary btn-sm">
                  View Reports <FiArrowRight className="ms-1" />
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence mode="popLayout">
        {activeModules.length > 0 && (
          <motion.div key="module-highlights" {...sectionMotion}>
            <h5 className="fw-bold mb-3">Module Highlights</h5>
            <div className="row g-3 mb-4">
              {activeModules.map((module, idx) => (
                <div className="col-sm-6 col-lg-4 col-xl-3" key={module.key}>
                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                  >
                    <ModuleHighlightCard module={module} stats={data?.module_stats} />
                  </motion.div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence mode="popLayout">
        <motion.div className="row g-3" key="activity-row" {...sectionMotion}>
          <div className={data?.upgrade_suggestions?.length ? 'col-lg-8' : 'col-12'}>
            <div className="apex-card p-4 h-100">
              <h5 className="fw-bold mb-3">Recent Activity</h5>
              <div className="d-flex flex-column gap-3">
                {(data?.recent_activities ?? []).length === 0 ? (
                  <p className="text-muted small mb-0">No recent activity recorded.</p>
                ) : (
                  (data?.recent_activities ?? []).map((act) => (
                    <div key={act.id} className="d-flex justify-content-between align-items-start">
                      <div>
                        <div className="small fw-medium">{act.message}</div>
                        <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                          {new Date(act.time).toLocaleString()}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
          {data?.upgrade_suggestions?.length > 0 && (
            <div className="col-lg-4">
              <UpgradePanel suggestions={data.upgrade_suggestions} planSlug={planSlug} />
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {!hasCharts && !hasChartData && widgets.length === 0 && activeModules.length === 0 && (
        <div className="apex-card p-5 text-center mt-4">
          <FiLayers size={32} className="text-muted mb-3" />
          <h5 className="fw-bold">Dashboard loading your plan features</h5>
          <p className="text-muted mb-0">
            Modules will appear here once your subscription is fully configured.
          </p>
        </div>
      )}
    </div>
  );
}

export default SchoolAdminDashboard;