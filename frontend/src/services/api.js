import axios from 'axios';
import { notify } from '../utils/notify';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
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

const AUTH_SKIP_PATHS = ['/auth/login/', '/auth/refresh/', '/auth/register/'];

const isAuthSkipRequest = (url = '') =>
  AUTH_SKIP_PATHS.some((path) => url.includes(path));

const isDemoToken = (token) =>
  !token || token === 'demo-access-token' || token === 'demo-refresh-token';

api.interceptors.request.use(
  (config) => {
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
    return config;
  },
  (error) => Promise.reject(error)
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
  }
);

export { api, API_BASE_URL, setStoredTokens, clearStoredTokens, getStoredTokens, dispatchAuthExpired };
export default api;