import {
  FiHome, FiGrid, FiSettings, FiBell, FiLayers, FiCreditCard,
  FiBarChart2, FiShield, FiRadio, FiInbox, FiTrendingUp, FiBookOpen, FiAward, FiFileText, FiUsers,
  FiMapPin,
} from 'react-icons/fi';
import { resolveFeatureIcon } from '../utils/featureIcons';
import { SCHOOL_MODULES } from './schoolModules';

export const superAdminNav = [
  { path: '/super-admin', label: 'Dashboard', icon: <FiHome /> },
  { divider: true, label: 'Management' },
  {
    path: '/super-admin/notifications',
    label: 'Notifications',
    icon: <FiBell />,
    children: [
      { path: '/super-admin/notifications', label: 'Inbox', icon: <FiInbox /> },
      { path: '/super-admin/notifications/advertise', label: 'Advertise', icon: <FiTrendingUp /> },
    ],
  },
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

// Synthetic always-on keys for school portal chrome (not sellable plan modules).
export const CORE_FEATURE_KEYS = ['dashboard_analytics', 'school_settings', 'notifications'];

export const FREE_TRIAL_FEATURE_KEYS = [
  'student_management', 'parent_management', 'staff_management', 'user_accounts',
  'academic_years', 'terms', 'classes', 'subjects', 'admissions',
  'student_attendance', 'fee_structures', 'student_billing', 'payment_recording',
  'dashboard_analytics', 'announcements',
];

/**
 * Parent family-portal sidebar entries (child-scoped routes).
 * Top-level Academics / Results so parents do not dig through staff module hubs.
 */
export const buildParentPortalNavItems = () => ([
  {
    key: 'parent_academics',
    path: '/school-admin/parent/academics',
    label: 'Academics',
    icon: <FiBookOpen />,
    // Multi-key: visible if any academic read feature is granted (filter uses feature_keys).
    featureKey: 'timetables',
    feature_keys: ['timetables', 'homework', 'student_attendance', 'classes', 'terms'],
  },
  {
    key: 'parent_results',
    path: '/school-admin/parent/results',
    label: 'Results & progress',
    icon: <FiAward />,
    featureKey: 'report_cards',
    feature_keys: ['report_cards', 'examination_management'],
  },
  {
    key: 'parent_fee_statements',
    path: '/school-admin/finance/statements',
    label: 'Fee statements',
    icon: <FiFileText />,
    featureKey: 'parent_fee_statements',
    feature_keys: ['parent_fee_statements', 'student_billing'],
  },
]);

export const buildSchoolAdminNav = (
  moduleMenu = [],
  { isSchoolAdmin = true, isParent = false } = {},
) => {
  const items = [
    { path: '/school-admin', label: 'Dashboard', icon: <FiHome />, featureKey: 'dashboard_analytics' },
  ];

  // Parents get a dedicated family section first (child-scoped Academics / Results / Fees).
  if (isParent) {
    items.push({ divider: true, label: 'Family portal' });
    items.push(...buildParentPortalNavItems());
  }

  const modules = [...(moduleMenu.length > 0 ? moduleMenu : [])].sort(
    (a, b) => (a.sort_order ?? 99) - (b.sort_order ?? 99),
  );

  // For parents, skip generic finance/academics hub cards that dump staff tools —
  // they already have the family portal entries above. Still show other modules
  // (communication, events, etc.) if granted.
  const parentHiddenModuleKeys = new Set(['finance', 'academics', 'examinations', 'attendance']);

  if (modules.length > 0) {
    const visibleModules = isParent
      ? modules.filter((module) => !parentHiddenModuleKeys.has(module.key))
      : modules;

    if (visibleModules.length > 0) {
      items.push({ divider: true, label: 'Modules' });
      visibleModules.forEach((module) => {
        const Icon = resolveFeatureIcon(module.icon);
        items.push({
          key: module.key,
          path: module.path,
          label: module.label,
          icon: <Icon />,
          featureKey: module.children?.[0]?.feature_key || module.feature_key,
          children: (module.children || []).map((child) => ({
            ...child,
            icon: resolveFeatureIcon(child.icon),
          })),
          badge: module.enabled_count ?? module.children?.length ?? 0,
        });
      });
    }
  }

  if (isSchoolAdmin) {
    items.push({
      divider: true,
      label: 'System',
    });
    // Core school-admin surfaces — not gated by plan feature checkboxes.
    items.push({
      path: '/school-admin/settings',
      label: 'Settings',
      icon: <FiSettings />,
      children: [
        { path: '/school-admin/settings', label: 'School Settings', icon: <FiSettings /> },
        { path: '/school-admin/settings/permissions', label: 'Permission Settings', icon: <FiShield /> },
        { path: '/school-admin/settings/dual-roles', label: 'Dual Roles', icon: <FiUsers /> },
        { path: '/school-admin/settings/school-boundary', label: 'School Boundary', icon: <FiMapPin /> },
        { path: '/school-admin/settings/plans', label: 'Plans & Subscriptions', icon: <FiLayers /> },
      ],
    });
  }

  return items;
};

export const buildFallbackModuleMenu = (enabledKeys = []) => {
  const keySet = new Set([...enabledKeys, ...CORE_FEATURE_KEYS]);
  return SCHOOL_MODULES.filter((mod) => {
    const modKeys = mod.feature_keys || [];
    return modKeys.some((k) => keySet.has(k));
  }).map((mod) => {
    const children = (mod.children || []).filter((c) => keySet.has(c.feature_key));
    return {
      key: mod.key,
      label: mod.label,
      path: mod.path,
      icon: mod.icon,
      sort_order: mod.sort_order,
      feature_key: mod.feature_keys?.[0],
      enabled_count: children.length,
      total_count: mod.children?.length || 0,
      children,
    };
  });
};