import axios from 'axios';
import { notify } from '../utils/notify';
import { confirmMaintenanceAction } from '../utils/maintenanceConfirm';

const resolveApiBaseUrl = () => {
  const configured = import.meta.env.VITE_API_BASE_URL;
  const onTunnelHost = typeof window !== 'undefined'
    && /\.ngrok-free\.dev$|\.ngrok\.io$/.test(window.location.hostname);
  const onHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';

  // Relative base routes through the Vite dev proxy (required for ngrok / HTTPS tunnels).
  if (configured?.startsWith('/')) {
    return configured.endsWith('/') ? configured.slice(0, -1) : configured;
  }
  if (import.meta.env.DEV || onTunnelHost || onHttps) {
    return '/api/v1';
  }
  if (configured) {
    return configured.endsWith('/') ? configured.slice(0, -1) : configured;
  }
  return 'http://localhost:8000/api/v1';
};

const API_BASE_URL = resolveApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  if (
    typeof window !== 'undefined'
    && /\.ngrok-free\.dev$|\.ngrok\.io$/.test(window.location.hostname)
  ) {
    config.headers['ngrok-skip-browser-warning'] = '69420';
  }
  return config;
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

const getStoredTokens = () => ({
  access: localStorage.getItem('apex_access_token') || sessionStorage.getItem('apex_access_token'),
  refresh: localStorage.getItem('apex_refresh_token') || sessionStorage.getItem('apex_refresh_token'),
});

const setStoredTokens = (access, refresh, remember = true) => {
  const storage = remember ? localStorage : sessionStorage;
  const other = remember ? sessionStorage : localStorage;
  other.removeItem('apex_access_token');
  other.removeItem('apex_refresh_token');
  storage.setItem('apex_access_token', access);
  if (refresh) storage.setItem('apex_refresh_token', refresh);
};

const clearStoredTokens = () => {
  localStorage.removeItem('apex_access_token');
  localStorage.removeItem('apex_refresh_token');
  sessionStorage.removeItem('apex_access_token');
  sessionStorage.removeItem('apex_refresh_token');
};

// Public endpoints only — must NOT match longer authenticated paths
// (e.g. /subscriptions/plans/ must not strip auth from /subscriptions/plans/manage/).
const AUTH_SKIP_PATHS = [
  '/auth/login/',
  '/auth/refresh/',
  '/auth/register/',
  '/tenants/register/',
  '/platform/settings/public/',
  '/subscriptions/plans/',
];

const resolveRequestPath = (url = '') => {
  const raw = String(url || '').split('?')[0];
  try {
    if (raw.startsWith('http://') || raw.startsWith('https://')) {
      return new URL(raw).pathname;
    }
  } catch {
    // use raw path below
  }
  return raw;
};

const isAuthSkipRequest = (url = '') => {
  const path = resolveRequestPath(url);
  if (!path) return false;
  return AUTH_SKIP_PATHS.some((skip) => {
    const withSlash = skip.endsWith('/') ? skip : `${skip}/`;
    const noSlash = withSlash.slice(0, -1);
    // Exact match only (path may include /api/v1 prefix when absolute).
    return (
      path === withSlash
      || path === noSlash
      || path.endsWith(withSlash)
      || path.endsWith(noSlash)
    );
  });
};

const isDemoToken = (token) =>
  !token || token === 'demo-access-token' || token === 'demo-refresh-token';

api.interceptors.request.use(
  async (config) => {
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    }

    if (isAuthSkipRequest(config.url)) {
      delete config.headers.Authorization;
      return config;
    }

    const { access } = getStoredTokens();
    if (access) {
      config.headers.Authorization = `Bearer ${access}`;
    }
    const tenantId = localStorage.getItem('apex_tenant_id');
    if (tenantId) {
      config.headers['X-Tenant-ID'] = tenantId;
    }

    const allowed = await confirmMaintenanceAction(config);
    if (!allowed) {
      return Promise.reject(new axios.CanceledError('Action cancelled during maintenance mode.'));
    }

    return config;
  },
  (error) => Promise.reject(error),
);

const dispatchAuthExpired = () => {
  clearStoredTokens();
  localStorage.removeItem('apex_user_email');
  localStorage.removeItem('apex_tenant_id');
  window.dispatchEvent(new CustomEvent('apex:auth-expired'));
  notify.warning('Your session has expired. Please sign in again.');
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config || {};

    const maintenanceCode = error.response?.data?.error?.code;
    if (error.response?.status === 503 && maintenanceCode === 'maintenance_mode') {
      window.dispatchEvent(new CustomEvent('apex:maintenance-blocked'));
      return Promise.reject(error);
    }

    if (
      error.response?.status !== 401 ||
      originalRequest._retry ||
      isAuthSkipRequest(originalRequest.url)
    ) {
      return Promise.reject(error);
    }

    const { access, refresh } = getStoredTokens();

    if (isDemoToken(access) || isDemoToken(refresh)) {
      return Promise.reject(error);
    }

    if (!refresh) {
      dispatchAuthExpired();
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      })
        .then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        })
        .catch((err) => Promise.reject(err));
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const response = await axios.post(`${API_BASE_URL}/auth/refresh/`, { refresh });
      const { access: newAccess, refresh: newRefresh } = response.data;
      const remember = !!localStorage.getItem('apex_refresh_token');
      setStoredTokens(newAccess, newRefresh || refresh, remember);
      processQueue(null, newAccess);
      originalRequest.headers.Authorization = `Bearer ${newAccess}`;
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      dispatchAuthExpired();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

export { api, API_BASE_URL, setStoredTokens, clearStoredTokens, getStoredTokens, dispatchAuthExpired };
export default api;