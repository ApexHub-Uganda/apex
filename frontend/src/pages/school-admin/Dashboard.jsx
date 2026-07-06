import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FiAlertTriangle, FiArrowRight, FiLayers, FiLock, FiTrendingUp,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import SchoolNameWithBadge from '../../components/SchoolNameWithBadge';
import StatCard from '../../components/StatCard';
import { LineChart, BarChart, DoughnutChart } from '../../components/Charts';
import ProgressBar from '../../components/ProgressBar';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { PageSkeleton } from '../../components/LoadingSkeleton';
import { dashboardService } from '../../services/dashboardService';
import { admissionPortalService } from '../../services/landingService';
import { useTenant } from '../../hooks/useTenant';
import { resolveFeatureIcon } from '../../utils/featureIcons';
import {
  WIDGET_STAT_MAP,
  formatStatValue,
} from '../../config/schoolDashboard';
import { getModuleEntryPath } from '../../utils/navAccess';

const EMPTY_CHART = { labels: [], datasets: [] };

const sectionMotion = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.3 },
};

function ModuleGridCard({ module, entryPath }) {
  const Icon = resolveFeatureIcon(module.icon);
  const allowedChildren = module.children || [];
  const childCount = module.enabled_count ?? allowedChildren.length;
  const openPath = entryPath || getModuleEntryPath(module);

  return (
    <motion.div className="school-module-card h-100" whileHover={{ y: -3 }}>
      <div className="d-flex align-items-center justify-content-between mb-2">
        <div className="d-flex align-items-center gap-2">
          <span className="school-module-icon">
            <Icon size={18} />
          </span>
          <h6 className="fw-bold mb-0">{module.label}</h6>
        </div>
        {openPath && (
          <Link to={openPath} className="btn btn-sm btn-link p-0 text-decoration-none">
            Open <FiArrowRight size={14} />
          </Link>
        )}
      </div>
      <p className="text-muted small mb-2">
        {childCount} allowed feature{childCount === 1 ? '' : 's'}
      </p>
      {allowedChildren.slice(0, 4).map((child) => (
        <Link
          key={child.feature_key}
          to={child.path}
          className="d-block small text-decoration-none text-muted mb-1"
        >
          · {child.label}
        </Link>
      ))}
      {(module.children || []).length > 4 && (
        <span className="small text-muted">+{(module.children || []).length - 4} more</span>
      )}
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
      <Link to="/school-admin/upgrade" className="btn btn-outline-primary btn-sm w-100 mt-3">
        <FiTrendingUp className="me-1" /> Upgrade Plan
      </Link>
    </motion.div>
  );
}

export function SchoolAdminDashboard() {
  const {
    tenant, dashboardWidgets, moduleMenu, enabledFeatureKeys, roleProfile, isSchoolAdmin,
  } = useTenant();

  const { data, isLoading } = useQuery({
    queryKey: ['school-admin-dashboard', tenant?.id],
    queryFn: () => dashboardService.getSchoolAdminStats(),
    refetchInterval: 60000,
    retry: 1,
  });

  const resolvedSections = useMemo(() => {
    const base = data?.sections ?? {};
    if (Object.keys(base).length) return base;
    return {
      attendance: enabledFeatureKeys.includes('student_attendance'),
      finance: enabledFeatureKeys.includes('student_billing'),
      enrollment: enabledFeatureKeys.includes('admissions'),
      classes: enabledFeatureKeys.includes('classes'),
      reports: enabledFeatureKeys.includes('reports'),
      staff_attendance: enabledFeatureKeys.includes('staff_attendance'),
    };
  }, [data?.sections, enabledFeatureKeys]);

  const stats = data?.stats ?? {};
  const widgets = useMemo(() => {
    const apiWidgets = data?.widgets?.length ? data.widgets : dashboardWidgets;
    return apiWidgets?.length ? apiWidgets : [];
  }, [data?.widgets, dashboardWidgets]);

  const activeModules = useMemo(() => moduleMenu || [], [moduleMenu]);

  const moduleEntryPaths = useMemo(() => {
    const paths = {};
    activeModules.forEach((module) => {
      paths[module.key] = getModuleEntryPath(module);
    });
    return paths;
  }, [activeModules]);

  const isParent = roleProfile?.role === 'parent';
  const showAdmissionVacancies = isParent && enabledFeatureKeys.includes('admission_vacancies');

  const { data: portalVacancies = [] } = useQuery({
    queryKey: ['portal-admission-vacancies', tenant?.id],
    queryFn: () => admissionPortalService.getVacancies(),
    enabled: showAdmissionVacancies,
    staleTime: 60_000,
  });

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

  const dashboardTitle = roleProfile?.title || (isSchoolAdmin ? 'School Admin Dashboard' : 'Dashboard');
  const dashboardSubtitle = roleProfile?.subtitle
    || 'Overview of school operations, statistics, and module activity';
  const quickActions = roleProfile?.quick_actions || [];

  return (
    <div className="school-dashboard">
      <PageHeader
        centered={isSchoolAdmin}
        title={isSchoolAdmin ? (
          <SchoolNameWithBadge
            name={tenant?.name || 'School'}
            planSlug={planSlug}
            size="lg"
          />
        ) : dashboardTitle}
        subtitle={dashboardSubtitle}
      />

      {showAdmissionVacancies && portalVacancies.length > 0 && (
        <motion.div className="apex-card p-4 mb-4" {...sectionMotion}>
          <h5 className="fw-bold mb-1">Open Admissions</h5>
          <p className="text-muted small mb-3">Grade vacancies published by your school</p>
          <div className="row g-3">
            {portalVacancies.map((vacancy) => (
              <div className="col-md-6 col-lg-4" key={vacancy.id}>
                <div className="border rounded-3 p-3 h-100 bg-light-subtle">
                  <h6 className="fw-bold mb-1">{vacancy.title}</h6>
                  {vacancy.grade_levels && (
                    <div className="small text-muted mb-2">{vacancy.grade_levels}</div>
                  )}
                  {vacancy.description && (
                    <p className="small text-muted mb-2">{vacancy.description}</p>
                  )}
                  <div className="small">
                    <span className="badge text-bg-primary-subtle border text-primary me-1">
                      {vacancy.remaining_openings} opening{vacancy.remaining_openings === 1 ? '' : 's'}
                    </span>
                    {vacancy.application_deadline && (
                      <span className="badge text-bg-light border">
                        Deadline: {vacancy.application_deadline}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {quickActions.length > 0 && (
        <motion.div className="row g-2 mb-4" {...sectionMotion}>
          {quickActions.map((action) => {
            const ActionIcon = resolveFeatureIcon('FiZap');
            return (
              <div className="col-sm-6 col-md-4 col-lg-3" key={action.path}>
                <Link
                  to={action.path}
                  className="role-quick-action-card d-flex align-items-center gap-2 text-decoration-none"
                >
                  <span className="role-quick-action-icon"><ActionIcon size={16} /></span>
                  <span className="small fw-semibold">{action.label}</span>
                  <FiArrowRight size={14} className="ms-auto text-muted" />
                </Link>
              </div>
            );
          })}
        </motion.div>
      )}

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
            <h5 className="fw-bold mb-3">Your Modules</h5>
            <div className="row g-3 mb-4">
              {activeModules.map((module, idx) => (
                <div className="col-sm-6 col-lg-4 col-xl-3" key={module.key}>
                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                  >
                    <ModuleGridCard
                    module={module}
                    entryPath={moduleEntryPaths[module.key]}
                  />
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