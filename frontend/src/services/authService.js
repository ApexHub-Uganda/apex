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

  async requestPasswordResetOtp(email) {
    const { data } = await api.post('/auth/password-reset/', { email: email.trim() });
    return data;
  },

  async confirmPasswordReset({ email, otp, newPassword }) {
    const { data } = await api.post('/auth/password-reset/confirm/', {
      email: email.trim(),
      otp: otp.trim(),
      new_password: newPassword,
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

  /**
   * Download blank school letterhead (staff only).
   * @param {number} pages 1–50
   */
  async downloadHeadedPaper(pages = 1) {
    const count = Math.max(1, Math.min(Number(pages) || 1, 50));
    const response = await api.get('/auth/me/headed-paper.pdf', {
      params: { pages: count },
      responseType: 'blob',
    });
    const blob = response.data;
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `headed-paper-${count}p.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    return true;
  },

  /**
   * Switch active portal role (dual-role users). Re-issues JWT tokens.
   * @param {string} role
   */
  async switchRole(role) {
    const { data } = await api.post('/auth/switch-role/', { role });
    const payload = data?.data ?? data;
    if (payload?.access) {
      const remember = !!localStorage.getItem('apex_refresh_token');
      setStoredTokens(payload.access, payload.refresh, remember);
    }
    return payload;
  },
};

const unwrap = (r) => {
  const body = r?.data ?? r;
  return body?.data ?? body;
};

export const dualRolesService = {
  options: () => api.get('/auth/dual-roles/options/').then((r) => unwrap(r)),
  candidates: (params = {}) => api.get('/auth/dual-roles/candidates/', { params }).then((r) => unwrap(r)),
  grant: (payload) => api.post('/auth/dual-roles/grant/', payload).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message };
  }),
  revoke: (payload) => api.post('/auth/dual-roles/revoke/', payload).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message };
  }),
};

export default authService;