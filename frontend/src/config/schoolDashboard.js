/** Plan metadata and dashboard widget/stat mappings for school-admin dashboard. */

export const PLAN_META = {
  free_trial: {
    label: 'Free Trial',
    badgeClass: 'school-plan-badge--trial',
    description: 'Core modules to get your school started. Upgrade to unlock advanced operations.',
  },
  basic: {
    label: 'Basic',
    badgeClass: 'school-plan-badge--basic',
    description: 'Expanded academics, finance, and reporting for growing schools.',
  },
  premium: {
    label: 'Premium',
    badgeClass: 'school-plan-badge--premium',
    description: 'Full operations suite — library, hostel, transport, HR, and payroll.',
  },
  premium_plus: {
    label: 'Premium Plus',
    badgeClass: 'school-plan-badge--plus',
    description: 'Every module unlocked with maximum capacity and platform support.',
  },
};

export const WIDGET_STAT_MAP = {
  students: { field: 'total_students', color: 'primary' },
  staff: { field: 'total_staff', color: 'secondary' },
  classes: { field: 'active_classes', color: 'accent' },
  attendance: { field: 'attendance_rate', color: 'success', suffix: '%' },
  finance: { field: 'pending_fees', color: 'warning', format: 'currency' },
  analytics: { field: 'class_capacity', color: 'primary', suffix: '%', fallbackLabel: 'Capacity Utilization' },
};

export const MODULE_HIGHLIGHTS = [
  {
    key: 'library',
    sectionKey: 'library',
    label: 'Library',
    icon: 'FiBookOpen',
    path: '/school-admin/library',
    metrics: [
      { label: 'Books', field: 'total_books' },
      { label: 'Borrowed', field: 'borrowed' },
      { label: 'Overdue', field: 'overdue', warn: true },
    ],
  },
  {
    key: 'hostel',
    sectionKey: 'hostel',
    label: 'Hostel',
    icon: 'FiHome',
    path: '/school-admin/hostel',
    metrics: [
      { label: 'Hostels', field: 'hostels' },
      { label: 'Occupied', field: 'occupied' },
      { label: 'Occupancy', field: 'occupancy_rate', suffix: '%' },
    ],
  },
  {
    key: 'transport',
    sectionKey: 'transport',
    label: 'Transport',
    icon: 'FiTruck',
    path: '/school-admin/transport',
    metrics: [
      { label: 'Vehicles', field: 'vehicles' },
      { label: 'Routes', field: 'routes' },
      { label: 'Students', field: 'students_assigned' },
    ],
  },
  {
    key: 'inventory',
    sectionKey: 'inventory',
    label: 'Inventory',
    icon: 'FiPackage',
    path: '/school-admin/inventory',
    metrics: [
      { label: 'Items', field: 'items' },
      { label: 'Low Stock', field: 'low_stock', warn: true },
    ],
  },
  {
    key: 'hr',
    sectionKey: 'hr',
    label: 'Human Resources',
    icon: 'FiUsers',
    path: '/school-admin/hr',
    metrics: [
      { label: 'Pending Leave', field: 'pending_leave', warn: true },
      { label: 'Approved', field: 'approved_leave' },
    ],
  },
  {
    key: 'payroll',
    sectionKey: 'payroll',
    label: 'Payroll',
    icon: 'FiCreditCard',
    path: '/school-admin/payroll',
    metrics: [
      { label: 'Runs (YTD)', field: 'runs_this_year' },
      { label: 'Pending', field: 'pending_runs', warn: true },
    ],
  },
  {
    key: 'communication',
    sectionKey: 'communication',
    label: 'Communication',
    icon: 'FiMessageSquare',
    path: '/school-admin/communication',
    metrics: [
      { label: 'Announcements', field: 'announcements' },
      { label: 'Published', field: 'published' },
    ],
  },
];

export const formatStatValue = (value, config = {}) => {
  const num = Number(value) || 0;
  if (config.format === 'currency') {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  return num;
};

export const getPlanMeta = (slug) => PLAN_META[slug] || {
  label: slug?.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) || 'Current Plan',
  badgeClass: 'school-plan-badge--basic',
  description: 'Your school subscription plan.',
};