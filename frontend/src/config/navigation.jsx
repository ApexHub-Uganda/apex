import {
  FiHome, FiGrid, FiUsers, FiBook, FiCalendar, FiDollarSign,
  FiBookOpen, FiTruck, FiPackage, FiBriefcase, FiCreditCard,
  FiBarChart2, FiSettings, FiMessageSquare, FiLayers,
  FiRadio, FiShield, FiBell,
} from 'react-icons/fi'; // FiHome used in MODULE_NAV_CATALOG via string icon keys
import { resolveFeatureIcon } from '../utils/featureIcons';

export const superAdminNav = [
  { path: '/super-admin', label: 'Dashboard', icon: <FiHome /> },
  { divider: true, label: 'Management' },
  { path: '/super-admin/notifications', label: 'Notifications & To-do', icon: <FiBell /> },
  { path: '/super-admin/schools', label: 'Schools', icon: <FiGrid /> },
  { path: '/super-admin/plans', label: 'Plans & Subscriptions', icon: <FiLayers /> },
  { path: '/super-admin/billing', label: 'Billing & Payments', icon: <FiCreditCard /> },
  { divider: true, label: 'Insights' },
  { path: '/super-admin/analytics', label: 'Analytics', icon: <FiBarChart2 /> },
  { path: '/super-admin/audit-logs', label: 'Audit Logs', icon: <FiShield /> },
  { path: '/super-admin/broadcast', label: 'Broadcast', icon: <FiRadio /> },
  { divider: true, label: 'System' },
  { path: '/super-admin/settings', label: 'Settings', icon: <FiSettings /> },
];

/** Fallback nav when API menu is empty but plan features are known */
export const MODULE_NAV_CATALOG = [
  { key: 'students', label: 'Students', path: '/school-admin/students', icon: 'FiUsers', feature_key: 'student_management' },
  { key: 'staff', label: 'Staff', path: '/school-admin/staff', icon: 'FiBriefcase', feature_key: 'staff_management' },
  { key: 'classes', label: 'Classes', path: '/school-admin/classes', icon: 'FiBook', feature_key: 'classes' },
  { key: 'attendance', label: 'Attendance', path: '/school-admin/attendance', icon: 'FiCalendar', feature_key: 'student_attendance' },
  { key: 'finance', label: 'Finance', path: '/school-admin/finance', icon: 'FiDollarSign', feature_key: 'student_billing' },
  { key: 'library', label: 'Library', path: '/school-admin/library', icon: 'FiBookOpen', feature_key: 'library_management' },
  { key: 'hostel', label: 'Hostel', path: '/school-admin/hostel', icon: 'FiHome', feature_key: 'hostel_management' },
  { key: 'transport', label: 'Transport', path: '/school-admin/transport', icon: 'FiTruck', feature_key: 'vehicles' },
  { key: 'inventory', label: 'Inventory', path: '/school-admin/inventory', icon: 'FiPackage', feature_key: 'inventory_items' },
  { key: 'hr', label: 'HR', path: '/school-admin/hr', icon: 'FiUsers', feature_key: 'hr_departments' },
  { key: 'payroll', label: 'Payroll', path: '/school-admin/payroll', icon: 'FiCreditCard', feature_key: 'payroll_runs' },
  { key: 'communication', label: 'Communication', path: '/school-admin/communication', icon: 'FiMessageSquare', feature_key: 'announcements' },
  { key: 'reports', label: 'Reports', path: '/school-admin/reports', icon: 'FiBarChart2', feature_key: 'reports' },
];

export const CORE_FEATURE_KEYS = ['dashboard_analytics', 'school_settings'];

export const FREE_TRIAL_FEATURE_KEYS = [
  'student_management', 'staff_management', 'classes', 'student_attendance',
  'student_billing', 'admissions', 'announcements', 'dashboard_analytics', 'school_settings',
];

export const buildNavigationFromFeatures = (enabledKeys = []) => {
  const keys = new Set([...enabledKeys, ...CORE_FEATURE_KEYS]);
  return MODULE_NAV_CATALOG.filter((item) => keys.has(item.feature_key));
};

export const buildSchoolAdminNav = (navigationMenu = []) => {
  const items = [
    { path: '/school-admin', label: 'Dashboard', icon: <FiHome />, featureKey: 'dashboard_analytics' },
  ];

  if (navigationMenu.length > 0) {
    items.push({ divider: true, label: 'Modules' });
    navigationMenu.forEach((item) => {
      const Icon = resolveFeatureIcon(item.icon);
      items.push({
        path: item.path,
        label: item.label,
        icon: <Icon />,
        featureKey: item.feature_key,
      });
    });
  }

  items.push(
    { divider: true, label: 'System' },
    { path: '/school-admin/settings', label: 'Settings', icon: <FiSettings />, featureKey: 'school_settings' },
  );

  return items;
};