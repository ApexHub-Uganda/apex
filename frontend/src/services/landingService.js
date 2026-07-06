import api from './api';

const unwrap = (response) => {
  const data = response?.data ?? response;
  return data?.data ?? data;
};

export const landingService = {
  getMarketingCatalog: () =>
    api.get('/subscriptions/marketing/').then((r) => unwrap(r)),

  getTrustedSchools: (limit = 8) =>
    api.get('/subscriptions/marketing/trusted-schools/', { params: { limit } }).then((r) => unwrap(r)),

  getAdmissionVacancies: () =>
    api.get('/admissions/public/vacancies/').then((r) => {
      const data = unwrap(r);
      return data?.vacancies ?? [];
    }),
};

export const admissionPortalService = {
  getVacancies: () =>
    api.get('/admissions/portal/vacancies/').then((r) => {
      const data = unwrap(r);
      return data?.vacancies ?? [];
    }),
};

export default landingService;