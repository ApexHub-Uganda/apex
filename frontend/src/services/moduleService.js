import api from './api';

const unwrapList = (response) => {
  const data = response?.data ?? response;
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.data?.results)) return data.data.results;
  if (Array.isArray(data?.data)) return data.data;
  return [];
};

const unwrapData = (response) => {
  const data = response?.data ?? response;
  return data?.data ?? data;
};

const createCrudService = (basePath) => ({
  list: (params = {}) => api.get(basePath, { params: { page_size: 100, ...params } }).then((r) => unwrapList(r)),
  get: (id) => api.get(`${basePath}${id}/`).then((r) => unwrapData(r)),
  create: (payload) => api.post(basePath, payload).then((r) => unwrapData(r)),
  update: (id, payload) => api.patch(`${basePath}${id}/`, payload).then((r) => unwrapData(r)),
  delete: (id) => api.delete(`${basePath}${id}/`).then((r) => unwrapData(r)),
  deleteAll: () => api.post(`${basePath}delete_all/`).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message };
  }),
});

export const schoolsService = {
  ...createCrudService('/tenants/'),
  getDetail: (id) => api.get(`/analytics/school/${id}/`).then((r) => unwrapData(r)),
  verify: (id) => api.post(`/tenants/${id}/verify/`).then((r) => unwrapData(r)),
  suspend: (id, reason = '') => api.post(`/tenants/${id}/suspend/`, { reason }).then((r) => unwrapData(r)),
  unsuspend: (id) => api.post(`/tenants/${id}/unsuspend/`).then((r) => unwrapData(r)),
  getDeletionPreview: (id) => api.get(`/tenants/${id}/deletion-preview/`).then((r) => unwrapData(r)),
  changePlan: (id, payload) => api.post(`/tenants/${id}/change-plan/`, payload).then((r) => unwrapData(r)),
  permanentDelete: (id, payload) => api.post(`/tenants/${id}/permanent-delete/`, payload).then((r) => unwrapData(r)),
};

export const platformNotificationsService = {
  list: (params) => api.get('/platform/notifications/', { params }).then((r) => unwrapList(r)),
  getSummary: () => api.get('/platform/notifications/summary/').then((r) => unwrapData(r)),
  approve: (id) => api.post(`/platform/notifications/${id}/approve/`).then((r) => unwrapData(r)),
  dismiss: (id) => api.post(`/platform/notifications/${id}/dismiss/`).then((r) => unwrapData(r)),
  markRead: (id) => api.post(`/platform/notifications/${id}/mark_read/`).then((r) => unwrapData(r)),
  markAllRead: () => api.post('/platform/notifications/mark_all_read/').then((r) => unwrapData(r)),
  delete: (id) => api.post(`/platform/notifications/${id}/delete_notification/`).then((r) => unwrapData(r)),
  deleteAll: () => api.post('/platform/notifications/delete_all/').then((r) => unwrapData(r)),
};

export const planAdvertisementService = {
  list: (params) => api.get('/platform/plan-advertisements/', { params }).then((r) => unwrapList(r)),
  get: (id) => api.get(`/platform/plan-advertisements/${id}/`).then((r) => unwrapData(r)),
  create: (payload) => api.post('/platform/plan-advertisements/', payload).then((r) => unwrapData(r)),
  update: (id, payload) => api.patch(`/platform/plan-advertisements/${id}/`, payload).then((r) => unwrapData(r)),
  delete: (id) => api.delete(`/platform/plan-advertisements/${id}/`).then((r) => unwrapData(r)),
  getPlanOptions: () => api.get('/platform/plan-advertisements/plan_options/').then((r) => unwrapData(r)),
  getDefaults: (params) => api.get('/platform/plan-advertisements/defaults/', { params }).then((r) => unwrapData(r)),
  broadcast: (id) => api.post(`/platform/plan-advertisements/${id}/broadcast/`).then((r) => unwrapData(r)),
  pause: (id) => api.post(`/platform/plan-advertisements/${id}/pause/`).then((r) => unwrapData(r)),
  end: (id) => api.post(`/platform/plan-advertisements/${id}/end/`).then((r) => unwrapData(r)),
};

export const plansService = createCrudService('/subscriptions/plans/manage/');

export const featuresService = {
  getCatalog: () =>
    api.get('/subscriptions/features/catalog/').then((r) => {
      const data = unwrapData(r);
      return data?.categories ?? [];
    }),
  listCategories: () => api.get('/subscriptions/features/categories/').then((r) => unwrapList(r)),
  createCategory: (payload) => api.post('/subscriptions/features/categories/', payload).then((r) => unwrapData(r)),
  updateCategory: (id, payload) => api.patch(`/subscriptions/features/categories/${id}/`, payload).then((r) => unwrapData(r)),
  listFeatures: (params) => api.get('/subscriptions/features/manage/', { params }).then((r) => unwrapList(r)),
  createFeature: (payload) => api.post('/subscriptions/features/manage/', payload).then((r) => unwrapData(r)),
  updateFeature: (id, payload) => api.patch(`/subscriptions/features/manage/${id}/`, payload).then((r) => unwrapData(r)),
};

export const subscriptionsService = {
  ...createCrudService('/subscriptions/'),
  activate: (id, periodDays = 30) =>
    api.post(`/subscriptions/${id}/activate/`, { period_days: periodDays }).then((r) => unwrapData(r)),
  suspend: (id) => api.post(`/subscriptions/${id}/suspend/`).then((r) => unwrapData(r)),
};

export const planUpgradeService = {
  getCatalog: () => api.get('/subscriptions/upgrade/catalog/').then((r) => unwrapData(r)),
  checkout: (payload) =>
    api.post('/subscriptions/upgrade/checkout/', payload).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message };
    }).catch((err) => {
      const body = err?.response?.data;
      if (err?.response?.status === 402 && body?.data) {
        return { ...body.data, message: body.message };
      }
      throw err;
    }),
};

export const billingService = {
  listTransactions: (params) =>
    api.get('/subscriptions/payments/transactions/', { params }).then((r) => unwrapList(r)),
  listProviders: () =>
    api.get('/subscriptions/payments/providers/', { page_size: 20 }).then((r) => unwrapList(r)),
};

const downloadBlob = (response, fallbackName) => {
  const blob = new Blob([response.data], { type: response.headers['content-type'] || 'application/pdf' });
  const disposition = response.headers['content-disposition'] || '';
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] || fallbackName;
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export const auditLogsService = {
  list: (params) => api.get('/audit/logs/', { params }).then((r) => unwrapList(r)),
  get: (id) => api.get(`/audit/logs/${id}/`).then((r) => unwrapData(r)),
  filterOptions: () => api.get('/audit/logs/filter-options/').then((r) => unwrapData(r)),
  exportPdf: (id) =>
    api.get(`/audit/logs/${id}/export-pdf/`, { responseType: 'blob' }).then((r) => {
      downloadBlob(r, `audit-log-${id}.pdf`);
    }),
  exportListPdf: (params) =>
    api.get('/audit/logs/export-pdf/', { params, responseType: 'blob' }).then((r) => {
      downloadBlob(r, 'audit-logs-export.pdf');
    }),
};

export const broadcastService = {
  list: (params) => api.get('/platform/broadcasts/', { params }).then((r) => unwrapList(r)),
  get: (id) => api.get(`/platform/broadcasts/${id}/`).then((r) => unwrapData(r)),
  create: (payload) => api.post('/platform/broadcasts/', payload).then((r) => unwrapData(r)),
  update: (id, payload) => api.patch(`/platform/broadcasts/${id}/`, payload).then((r) => unwrapData(r)),
  delete: (id) => api.delete(`/platform/broadcasts/${id}/`).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message };
  }),
  deleteBroadcast: (id) => api.post(`/platform/broadcasts/${id}/delete_broadcast/`).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message };
  }),
  preview: (payload) => api.post('/platform/broadcasts/preview/', payload).then((r) => unwrapData(r)),
  send: (id) => api.post(`/platform/broadcasts/${id}/send/`).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message };
  }),
  schedule: (id, payload = {}) => api.post(`/platform/broadcasts/${id}/schedule/`, payload).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message };
  }),
  cancel: (id) => api.post(`/platform/broadcasts/${id}/cancel/`).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message };
  }),
  duplicate: (id) => api.post(`/platform/broadcasts/${id}/duplicate/`).then((r) => unwrapData(r)),
  deliveries: (id, params) => api.get(`/platform/broadcasts/${id}/deliveries/`, { params }).then((r) => unwrapList(r)),
  getChannelStatus: () => api.get('/platform/broadcasts/channel_status/').then((r) => unwrapData(r)),
};

export const settingsService = {
  get: () => api.get('/platform/settings/general/').then((r) => unwrapData(r)),
  update: (payload) => api.patch('/platform/settings/general/', payload).then((r) => unwrapData(r)),
};

export const platformService = {
  getHealth: () => api.get('/platform/health/').then((r) => r?.data ?? r),
};

export const studentsService = createCrudService('/students/');
export const parentsService = {
  ...createCrudService('/students/parents/'),
  linkStudent: (parentId, studentId) =>
    api.post(`/students/parents/${parentId}/link-student/`, { student_id: studentId }).then((r) => unwrapData(r)),
  unlinkStudent: (parentId, studentId) =>
    api.post(`/students/parents/${parentId}/unlink-student/`, { student_id: studentId }).then((r) => unwrapData(r)),
  setChildren: (parentId, childIds) =>
    api.post(`/students/parents/${parentId}/set-children/`, { child_ids: childIds }).then((r) => unwrapData(r)),
  getMatchingSummary: () =>
    api.get('/students/parents/matching-summary/').then((r) => unwrapData(r)),
};
export const academicYearsService = createCrudService('/academics/years/');
export const termsService = createCrudService('/academics/terms/');
export const streamsService = createCrudService('/academics/streams/');
export const subjectsService = createCrudService('/academics/subjects/');
export const homeworkService = createCrudService('/academics/homework/');
export const assignmentsService = createCrudService('/academics/assignments/');
export const timetablesService = createCrudService('/academics/timetables/');
export const feeStructuresService = createCrudService('/finance/fee-structures/');
export const feePaymentsService = createCrudService('/finance/payments/');
export const invoicesService = createCrudService('/finance/invoices/');
export const accountingService = createCrudService('/finance/accounting/');
const admissionApplicationsBase = '/admissions/applications/';
export const admissionApplicationsService = {
  ...createCrudService(admissionApplicationsBase),
  admit: (id, payload = {}) =>
    api.post(`${admissionApplicationsBase}${id}/admit/`, payload).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message };
    }),
  reject: (id, payload = {}) =>
    api.post(`${admissionApplicationsBase}${id}/reject/`, payload).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message };
    }),
};
export const admittedStudentsService = createCrudService('/admissions/admitted/');
export const admissionVacanciesService = {
  ...createCrudService('/admissions/vacancies/'),
  publish: (id) =>
    api.post(`/admissions/vacancies/${id}/publish/`).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message };
    }),
};
/** @deprecated Use admissionApplicationsService */
export const admissionsService = admissionApplicationsService;
export const medicalRecordsService = createCrudService('/students/medical-records/');
export const periodsService = createCrudService('/academics/periods/');
export const classroomsService = createCrudService('/academics/classrooms/');
export const gradingScalesService = createCrudService('/examinations/grading-scales/');
export const gradesService = createCrudService('/examinations/grades/');
export const subjectPapersService = createCrudService('/academics/subject-papers/');
export const examinationReferenceService = {
  get: () => api.get('/examinations/reference/').then((r) => unwrapData(r)),
};
export const marksEntryService = {
  getOptions: (params = {}) =>
    api.get('/examinations/marks-entry/options/', { params }).then((r) => unwrapData(r)),
  saveBulk: (payload) =>
    api.post('/examinations/marks-entry/bulk/', payload).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message, success: body?.success };
    }),
};
export const reportCardsService = createCrudService('/examinations/report-cards/');
export const examsService = createCrudService('/examinations/exams/');
export const booksService = createCrudService('/library/books/');
export const borrowsService = createCrudService('/library/borrows/');
export const routesService = createCrudService('/transport/routes/');
export const vehiclesService = createCrudService('/transport/vehicles/');
export const studentTransportService = createCrudService('/transport/student-assignments/');
export const roomsService = createCrudService('/hostel/rooms/');
export const allocationsService = createCrudService('/hostel/allocations/');
export const inventoryItemsService = createCrudService('/inventory/items/');
export const stockMovementsService = createCrudService('/inventory/movements/');
export const procurementsService = createCrudService('/inventory/procurements/');
export const leavesService = createCrudService('/hr/leaves/');
export const performanceReviewsService = createCrudService('/hr/performance-reviews/');
export const payrollRunsService = createCrudService('/payroll/runs/');
export const payslipsService = createCrudService('/payroll/payslips/');
export const salaryStructuresService = createCrudService('/payroll/salary-structures/');
export const announcementsService = {
  ...createCrudService('/communication/announcements/'),
  publish: (id, payload = {}) =>
    api.post(`/communication/announcements/${id}/publish/`, payload).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message };
    }),
};
export const smsService = createCrudService('/communication/sms/');
export const emailsService = {
  ...createCrudService('/communication/emails/'),
  send: (id) =>
    api.post(`/communication/emails/${id}/send/`).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message };
    }),
};
export const broadcastsService = {
  ...createCrudService('/communication/broadcasts/'),
  send: (id) =>
    api.post(`/communication/broadcasts/${id}/send/`).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message };
    }),
};
export const supportTicketsService = createCrudService('/communication/support-tickets/');
export const ticketRepliesService = createCrudService('/communication/ticket-replies/');
export const eventsService = createCrudService('/events/');
export const eventRegistrationsService = createCrudService('/events/registrations/');
export const staffService = {
  ...createCrudService('/staff/'),
  list: (params = {}) => api.get('/staff/', { params: { page_size: 100, ...params } }).then((r) => {
    const body = r?.data ?? r;
    if (Array.isArray(body?.data)) return body.data;
    return unwrapList(r);
  }),
  get: (id) => api.get(`/staff/${id}/`).then((r) => {
    const body = r?.data ?? r;
    return body?.data ?? body;
  }),
  create: (payload) => api.post('/staff/', payload).then((r) => {
    const body = r?.data ?? r;
    return {
      ...(body?.data ?? body),
      temporary_password: body?.temporary_password,
      message: body?.message,
    };
  }),
  update: (id, payload) => api.patch(`/staff/${id}/`, payload).then((r) => {
    const body = r?.data ?? r;
    return body?.data ?? body;
  }),
  getRoleOptions: () => api.get('/staff/role-options/').then((r) => {
    const body = r?.data ?? r;
    return body?.data ?? unwrapData(r) ?? [];
  }),
  getRolePreview: (role) => api.get('/staff/role-preview/', { params: { role } }).then((r) => unwrapData(r)),
};
export const departmentsService = createCrudService('/academics/departments/');
export const classesService = {
  ...createCrudService('/academics/classes/'),
  listStreams: (classId) => streamsService.list({ school_class: classId }),
};
export const attendanceService = createCrudService('/attendance/');
export const financeService = feePaymentsService;
export const libraryService = booksService;
export const hostelService = createCrudService('/hostel/');
export const transportService = routesService;
export const inventoryService = inventoryItemsService;
export const hrService = leavesService;
export const payrollService = payrollRunsService;
export const reportsService = {
  list: (params) => api.get('/school-admin/reports/', { params }).then((r) => unwrapList(r)),
  generate: (payload) => api.post('/school-admin/reports/generate/', payload).then((r) => unwrapData(r)),
};
export const communicationService = createCrudService('/school-admin/communication/');
export const notificationFeedService = {
  getFeed: () => api.get('/auth/notifications/feed/').then((r) => unwrapData(r)),
  markAllRead: () => api.post('/auth/notifications/feed/', { action: 'mark_all_read' }).then((r) => unwrapData(r)),
  deleteOne: (itemId) => api.post('/auth/notifications/feed/', { action: 'delete_one', item_id: itemId }).then((r) => unwrapData(r)),
  deleteAll: () => api.post('/auth/notifications/feed/', { action: 'delete_all' }).then((r) => unwrapData(r)),
};

export const notificationsService = {
  list: (params) => api.get('/communication/notifications/', { params }).then((r) => unwrapList(r)),
  markRead: (id) => api.post(`/communication/notifications/${id}/mark_read/`).then((r) => unwrapData(r)),
  markAllRead: () => api.post('/communication/notifications/mark_all_read/').then((r) => unwrapData(r)),
  delete: (id) => api.post(`/communication/notifications/${id}/delete_notification/`).then((r) => unwrapData(r)),
  deleteAll: () => api.post('/communication/notifications/delete_all/').then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message };
  }),
  getSummary: () => api.get('/communication/notifications/summary/').then((r) => unwrapData(r)),
};

export default {
  schoolsService,
  platformNotificationsService,
  plansService,
  subscriptionsService,
  auditLogsService,
  broadcastService,
  settingsService,
  studentsService,
  staffService,
  classesService,
  attendanceService,
  financeService,
  libraryService,
  hostelService,
  transportService,
  inventoryService,
  hrService,
  payrollService,
  reportsService,
  communicationService,
  notificationsService,
  notificationFeedService,
};