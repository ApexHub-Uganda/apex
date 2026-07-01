import api from './api';

const unwrapData = (response) => {
  const data = response?.data ?? response;
  return data?.data ?? data;
};

export const registrationService = {
  register: (payload) =>
    api.post('/tenants/register/', payload).then((r) => r.data),

  getOnboarding: (tenantId) =>
    api.get(`/tenants/onboarding/${tenantId}/`).then((r) => unwrapData(r)),

  claimTrialEmail: (tenantId) =>
    api.post(`/tenants/onboarding/${tenantId}/claim-trial/`).then((r) => r.data),

  selectPlan: (tenantId, planSlug, billingCycle = 'monthly') =>
    api.post(`/tenants/onboarding/${tenantId}/select-plan/`, {
      plan_slug: planSlug,
      billing_cycle: billingCycle,
    }).then((r) => r.data),

  checkout: (tenantId, planSlug, billingCycle = 'monthly') =>
    api.post(`/tenants/onboarding/${tenantId}/checkout/`, {
      plan_slug: planSlug,
      billing_cycle: billingCycle,
    }).then((r) => r.data),

  getPublicSettings: () =>
    api.get('/platform/settings/public/').then((r) => unwrapData(r)),

  listPlans: () =>
    api.get('/subscriptions/plans/').then((r) => {
      const data = r.data;
      if (Array.isArray(data)) return data;
      if (Array.isArray(data?.results)) return data.results;
      return [];
    }),
};

export default registrationService;