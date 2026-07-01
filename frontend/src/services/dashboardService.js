import api from './api';

export const dashboardService = {
  async getSuperAdminStats() {
    const { data } = await api.get('/analytics/dashboard/platform/');
    return data.data || data;
  },

  async getSchoolAdminStats() {
    const { data } = await api.get('/analytics/dashboard/school/');
    return data.data || data;
  },

  async getPlatformAnalytics() {
    const { data } = await api.get('/analytics/platform/');
    return data.data || data;
  },

  async getPlansSubscriptionsHub() {
    const { data } = await api.get('/analytics/plans-subscriptions/');
    return data.data || data;
  },

  async getBillingOperations() {
    const { data } = await api.get('/analytics/billing/');
    return data.data || data;
  },

  async getAnalytics(params = {}) {
    const { data } = await api.get('/analytics/enrollment/', { params });
    return data.data || data;
  },
};

export default dashboardService;