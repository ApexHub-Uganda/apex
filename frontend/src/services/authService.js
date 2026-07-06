import api, { setStoredTokens, clearStoredTokens } from './api';

export const authService = {
  async login(credentials) {
    const email = credentials.email?.trim();
    const password = credentials.password?.trim();
    const remember = credentials.remember ?? true;

    clearStoredTokens();
    localStorage.removeItem('apex_tenant_id');

    const { data } = await api.post('/auth/login/', { email, password });
    setStoredTokens(data.access, data.refresh, remember);
    const tenantId = data.user?.tenant || data.user?.tenant_id;
    if (tenantId) {
      localStorage.setItem('apex_tenant_id', tenantId);
    } else {
      localStorage.removeItem('apex_tenant_id');
    }
    return data;
  },

  async register(userData) {
    const { data } = await api.post('/auth/register/', userData);
    return data;
  },

  async logout() {
    try {
      const refresh = localStorage.getItem('apex_refresh_token') || sessionStorage.getItem('apex_refresh_token');
      if (refresh) {
        await api.post('/auth/logout/', { refresh });
      }
    } catch {
      // ignore logout errors
    } finally {
      clearStoredTokens();
      localStorage.removeItem('apex_tenant_id');
    }
  },

  async forgotPassword(email) {
    const { data } = await api.post('/auth/password/reset/', { email });
    return data;
  },

  async resetPassword(token, password) {
    const { data } = await api.post('/auth/password/reset/confirm/', {
      token,
      password,
    });
    return data;
  },

  async getProfile() {
    const { data } = await api.get('/auth/me/');
    return data?.data ?? data;
  },

  async updateProfile(profileData) {
    const { data } = await api.patch('/auth/me/', profileData);
    return data?.data ?? data;
  },

  async changePassword(passwords) {
    const { data } = await api.post('/auth/change-password/', passwords);
    return data;
  },

  async uploadAvatar(file) {
    const formData = new FormData();
    formData.append('avatar', file);
    const { data } = await api.post('/auth/me/avatar/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data?.data ?? data;
  },

  async deleteAvatar() {
    const { data } = await api.delete('/auth/me/avatar/');
    return data?.data ?? data;
  },
};

export default authService;