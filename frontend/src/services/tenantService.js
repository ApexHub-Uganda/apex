import api from './api';
import { CORE_FEATURE_KEYS, buildFallbackModuleMenu } from '../config/navigation';

const unwrap = (data) => {
  if (!data) return null;
  if (data?.data && typeof data.data === 'object') {
    return data.data;
  }
  if (data?.enabled_feature_keys || data?.module_menu || data?.id) return data;
  if (data?.tenant) return data.tenant;
  return data;
};

const isNetworkError = (err) => !err?.response && (
  err?.code === 'ERR_NETWORK'
  || err?.message?.includes('Network Error')
  || err?.message?.includes('ECONNREFUSED')
);

const isUsableContext = (payload) => {
  if (!payload?.id) return false;
  const moduleCount = payload.module_menu?.length || 0;
  const keyCount = payload.enabled_feature_keys?.length || 0;
  return moduleCount > 0 || keyCount > CORE_FEATURE_KEYS.length;
};

const enrichContext = (payload) => {
  if (!payload) return null;

  const apiKeys = payload.enabled_feature_keys || [];
  const keys = [...new Set([...apiKeys, ...CORE_FEATURE_KEYS])];
  const flags = { ...(payload.feature_flags || {}) };
  apiKeys.forEach((k) => { flags[k] = true; });
  CORE_FEATURE_KEYS.forEach((k) => { flags[k] = true; });

  let moduleMenu = payload.module_menu;
  if (!moduleMenu?.length) {
    if (payload.navigation_menu?.length) {
      moduleMenu = payload.navigation_menu;
    } else if (keys.length > CORE_FEATURE_KEYS.length) {
      moduleMenu = buildFallbackModuleMenu(keys);
    } else {
      moduleMenu = [];
    }
  }

  return {
    ...payload,
    enabled_feature_keys: keys,
    feature_flags: flags,
    module_menu: moduleMenu,
    navigation_menu: payload.navigation_menu?.length ? payload.navigation_menu : moduleMenu,
  };
};

export const tenantService = {
  async getSchoolContext(user) {
    let lastError = null;
    let backendUnreachable = false;

    try {
      const { data } = await api.get('/tenants/context/', {
        params: { _ts: Date.now() },
      });
      const payload = unwrap(data);
      if (isUsableContext(payload)) {
        return { ...enrichContext(payload), _partial: false, _source: 'context_api' };
      }
      lastError = new Error('School context returned no plan modules from database.');
    } catch (err) {
      lastError = err;
      backendUnreachable = isNetworkError(err);
    }

    if (!backendUnreachable) {
      try {
        const { data } = await api.get('/tenants/current/', {
          params: { _ts: Date.now() },
        });
        const payload = unwrap(data);
        if (isUsableContext(payload)) {
          return { ...enrichContext(payload), _partial: false, _source: 'current_api' };
        }
        if (payload?.id) {
          return {
            ...enrichContext(payload),
            _partial: true,
            _source: 'current_api_partial',
            _error: lastError?.message || 'Partial tenant profile only.',
          };
        }
      } catch (err) {
        lastError = err;
      }
    }

    const fallback = {
      id: user?.tenant || user?.tenant_id || null,
      name: user?.tenant_name || 'Your School',
      code: '',
      email: user?.email,
      status: user?.tenant_status || 'active',
      is_verified: user?.tenant_is_verified ?? true,
      enabled_feature_keys: [...CORE_FEATURE_KEYS],
      feature_flags: Object.fromEntries(CORE_FEATURE_KEYS.map((k) => [k, true])),
      navigation_menu: [],
      module_menu: [],
      dashboard_widgets: [],
      subscription: null,
      primary_color: '#0F766E',
      secondary_color: '#FF7F50',
      accent_color: '#F5E6CA',
      _partial: true,
      _source: 'api_unreachable',
      _error: lastError?.message || 'Cannot reach school context API.',
    };
    return fallback;
  },

  async getCurrentTenant() {
    return tenantService.getSchoolContext();
  },

  async getSettings() {
    const { data } = await api.get('/tenants/settings/');
    return unwrap(data) || data?.data || data;
  },

  /**
   * Persist school profile + branding.
   * Accepts plain object (JSON) or FormData (logo upload).
   */
  async updateSettings(settings) {
    const isFormData = typeof FormData !== 'undefined' && settings instanceof FormData;
    const { data } = await api.patch('/tenants/settings/', settings, {
      // Let the browser set multipart boundary; force JSON only for plain objects.
      headers: isFormData ? { 'Content-Type': undefined } : undefined,
      transformRequest: isFormData
        ? [(body, headers) => {
          if (headers && typeof headers === 'object') {
            delete headers['Content-Type'];
          }
          return body;
        }]
        : undefined,
    });
    return unwrap(data) || data?.data || data;
  },

  /** Download A4 branded PDF template preview. */
  async downloadPdfPreview() {
    const response = await api.get('/tenants/pdf-preview/', { responseType: 'blob' });
    const blob = response.data instanceof Blob
      ? response.data
      : new Blob([response.data], { type: 'application/pdf' });
    const head = new Uint8Array(await blob.slice(0, 5).arrayBuffer());
    const magic = String.fromCharCode(...head);
    if (magic !== '%PDF-') {
      const text = await blob.slice(0, 400).text();
      let message = 'PDF preview failed.';
      try {
        const parsed = JSON.parse(text);
        message = parsed?.error?.message || parsed?.message || message;
      } catch {
        /* keep default */
      }
      throw new Error(message);
    }
    const disposition = response.headers?.['content-disposition'] || '';
    const match = disposition.match(/filename\*?=(?:UTF-8''|")?([^\";]+)"?/i);
    const filename = decodeURIComponent((match?.[1] || 'pdf-template-preview.pdf').replace(/["']/g, ''));
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    return true;
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

  async getRolePermissionMatrix() {
    const { data } = await api.get('/tenants/role-permissions/');
    return data?.data || data;
  },

  async saveRolePermissions(permissions) {
    const { data } = await api.put('/tenants/role-permissions/', { permissions });
    return data?.data || data;
  },

  async resetRolePermissions({ role, password, acknowledge_risk }) {
    const { data } = await api.post('/tenants/role-permissions/', {
      ...(role ? { role } : {}),
      password,
      acknowledge_risk,
    });
    return data?.data || data;
  },
};

export default tenantService;