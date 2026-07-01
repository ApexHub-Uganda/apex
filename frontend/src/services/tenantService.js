import api from './api';
import {
  CORE_FEATURE_KEYS,
  FREE_TRIAL_FEATURE_KEYS,
  buildNavigationFromFeatures,
} from '../config/navigation';

const unwrap = (data) => {
  if (!data) return null;
  if (data?.data && (data.data.id !== undefined || data.data.enabled_feature_keys)) return data.data;
  if (data?.enabled_feature_keys || data?.id) return data;
  if (data?.tenant) return data.tenant;
  return data;
};

const buildFallbackFromUser = (user) => ({
  id: user?.tenant || user?.tenant_id || null,
  name: user?.tenant_name || 'Your School',
  code: '',
  email: user?.email,
  status: user?.tenant_status || 'active',
  is_verified: user?.tenant_is_verified ?? true,
  enabled_feature_keys: [...FREE_TRIAL_FEATURE_KEYS],
  feature_flags: Object.fromEntries(FREE_TRIAL_FEATURE_KEYS.map((k) => [k, true])),
  navigation_menu: buildNavigationFromFeatures(FREE_TRIAL_FEATURE_KEYS),
  dashboard_widgets: [
    { key: 'students', label: 'Total Students', icon: 'FiUsers', feature_key: 'student_management' },
    { key: 'staff', label: 'Total Staff', icon: 'FiBriefcase', feature_key: 'staff_management' },
    { key: 'attendance', label: 'Attendance Today', icon: 'FiCalendar', feature_key: 'student_attendance' },
    { key: 'finance', label: 'Outstanding Fees', icon: 'FiDollarSign', feature_key: 'student_billing' },
  ],
  subscription: { plan_name: 'Free Trial', plan_slug: 'free_trial', status: 'trial' },
  primary_color: '#0F766E',
  secondary_color: '#FF7F50',
  accent_color: '#F5E6CA',
  _partial: true,
  _source: 'user_fallback',
});

const enrichContext = (payload) => {
  if (!payload) return null;
  const keys = [...new Set([...(payload.enabled_feature_keys || []), ...CORE_FEATURE_KEYS])];
  const flags = { ...(payload.feature_flags || {}) };
  keys.forEach((k) => { flags[k] = true; });

  let navigationMenu = payload.navigation_menu || [];
  if (!navigationMenu.length && keys.length) {
    navigationMenu = buildNavigationFromFeatures(keys);
  }

  return {
    ...payload,
    enabled_feature_keys: keys,
    feature_flags: flags,
    navigation_menu: navigationMenu,
  };
};

export const tenantService = {
  async getSchoolContext(user) {
    try {
      const { data } = await api.get('/tenants/context/');
      const payload = unwrap(data);
      if (payload?.id || payload?.enabled_feature_keys?.length) {
        return { ...enrichContext(payload), _partial: false, _source: 'context_api' };
      }
    } catch {
      // fall through
    }

    try {
      const { data } = await api.get('/tenants/current/');
      const payload = unwrap(data);
      if (payload?.id || payload?.enabled_feature_keys?.length) {
        return { ...enrichContext(payload), _partial: false, _source: 'current_api' };
      }
    } catch {
      // fall through
    }

    return buildFallbackFromUser(user);
  },

  async getCurrentTenant() {
    return tenantService.getSchoolContext();
  },

  async getSettings() {
    const { data } = await api.get('/tenants/context/');
    return unwrap(data);
  },

  async updateSettings(settings) {
    const tenantId = localStorage.getItem('apex_tenant_id');
    const { data } = await api.patch(`/tenants/${tenantId}/`, settings);
    return data;
  },

  async getCurrentSubscription() {
    try {
      const { data } = await api.get('/subscriptions/current/');
      return unwrap(data);
    } catch {
      return null;
    }
  },

  async getFeatureFlags() {
    const sub = await tenantService.getCurrentSubscription();
    return sub?.plan?.feature_flags || sub?.feature_flags || {};
  },
};

export default tenantService;