import {
  FiHome, FiGrid, FiSettings, FiBell, FiLayers, FiCreditCard,
  FiBarChart2, FiShield, FiRadio, FiInbox, FiTrendingUp,
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

export const CORE_FEATURE_KEYS = ['dashboard_analytics', 'school_settings', 'notifications'];

export const FREE_TRIAL_FEATURE_KEYS = [
  'student_management', 'parent_management', 'staff_management', 'user_accounts',
  'school_settings', 'academic_years', 'terms', 'classes', 'subjects', 'admissions',
  'student_attendance', 'fee_structures', 'student_billing', 'payment_recording',
  'dashboard_analytics', 'announcements',
];

export const buildSchoolAdminNav = (moduleMenu = [], { isSchoolAdmin = true } = {}) => {
  const items = [
    { path: '/school-admin', label: 'Dashboard', icon: <FiHome />, featureKey: 'dashboard_analytics' },
  ];

  const modules = [...(moduleMenu.length > 0 ? moduleMenu : [])].sort(
    (a, b) => (a.sort_order ?? 99) - (b.sort_order ?? 99),
  );

  if (modules.length > 0) {
    items.push({ divider: true, label: 'Modules' });
    modules.forEach((module) => {
      const Icon = resolveFeatureIcon(module.icon);
      items.push({
        path: module.path,
        label: module.label,
        icon: <Icon />,
        featureKey: module.feature_key || module.children?.[0]?.feature_key,
        children: (module.children || []).map((child) => ({
          ...child,
          icon: resolveFeatureIcon(child.icon),
        })),
        badge: module.enabled_count,
      });
    });
  }

  if (isSchoolAdmin) {
    items.push({
      divider: true,
      label: 'System',
    });
    items.push({
      path: '/school-admin/settings',
      label: 'Settings',
      icon: <FiSettings />,
      featureKey: 'school_settings',
      children: [
        { path: '/school-admin/settings', label: 'School Settings', icon: <FiSettings />, featureKey: 'school_settings' },
        { path: '/school-admin/settings/permissions', label: 'Permission Settings', icon: <FiShield />, featureKey: 'roles_permissions' },
        { path: '/school-admin/settings/plans', label: 'Plans & Subscriptions', icon: <FiLayers />, featureKey: 'school_settings' },
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