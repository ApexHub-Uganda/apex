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

const unwrapListWithMeta = (response) => {
  const data = response?.data ?? response;
  return {
    records: unwrapList(response),
    meta: data?.meta ?? data?.data?.meta ?? null,
  };
};

const createCrudService = (basePath) => ({
  list: (params = {}) => api.get(basePath, { params: { page_size: 100, ...params } }).then((r) => unwrapList(r)),
  listWithMeta: (params = {}) => api.get(basePath, { params: { page_size: 100, ...params } }).then((r) => unwrapListWithMeta(r)),
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
  broadcast: (id) => api.post(`/platform/plan-advertisements/${id}/broadcast/`).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message };
  }),
  pause: (id) => api.post(`/platform/plan-advertisements/${id}/pause/`).then((r) => unwrapData(r)),
  end: (id) => api.post(`/platform/plan-advertisements/${id}/end/`).then((r) => unwrapData(r)),
};

export const plansService = {
  ...createCrudService('/subscriptions/plans/manage/'),
  getDeletionPreview: (id) =>
    api.get(`/subscriptions/plans/manage/${id}/deletion-preview/`).then((r) => unwrapData(r)),
  delete: (id, params = {}) =>
    api.delete(`/subscriptions/plans/manage/${id}/`, { params }).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message };
    }),
};

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

const readBlobText = async (blob) => {
  if (!blob) return '';
  if (typeof blob.text === 'function') return blob.text();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(reader.error || new Error('Unable to read download payload.'));
    reader.readAsText(blob);
  });
};

const assertDownloadableBlob = async (response, expectedKinds = []) => {
  const raw = response?.data;
  const headerType = String(response?.headers?.['content-type'] || '').toLowerCase();
  const blob = raw instanceof Blob
    ? raw
    : new Blob([raw], { type: headerType || 'application/octet-stream' });

  // API errors still arrive as blobs when responseType is "blob".
  const looksLikeJson = headerType.includes('application/json')
    || headerType.includes('text/html')
    || headerType.includes('text/plain');
  if (looksLikeJson || blob.size < 8) {
    const text = (await readBlobText(blob)).trim();
    if (text.startsWith('{') || text.startsWith('<') || text.toLowerCase().includes('not authenticated')) {
      let message = 'Download failed.';
      try {
        const parsed = JSON.parse(text);
        message = parsed?.error?.message || parsed?.message || parsed?.detail || message;
      } catch {
        if (text) message = text.slice(0, 200);
      }
      throw new Error(message);
    }
  }

  if (expectedKinds.includes('pdf')) {
    const head = new Uint8Array(await blob.slice(0, 5).arrayBuffer());
    const magic = String.fromCharCode(...head);
    if (magic !== '%PDF-') {
      const text = (await readBlobText(blob.slice(0, 400))).trim();
      let message = 'Downloaded file is not a valid PDF.';
      try {
        const parsed = JSON.parse(text);
        message = parsed?.error?.message || parsed?.message || parsed?.detail || message;
      } catch {
        /* keep default */
      }
      throw new Error(message);
    }
  }

  return blob;
};

const downloadBlob = async (response, fallbackName, expectedKinds = []) => {
  const blob = await assertDownloadableBlob(response, expectedKinds);
  const contentType = response.headers?.['content-type']
    || (expectedKinds.includes('pdf') ? 'application/pdf' : blob.type)
    || 'application/octet-stream';
  const typedBlob = blob.type ? blob : new Blob([blob], { type: contentType });
  const disposition = response.headers?.['content-disposition'] || '';
  const match = disposition.match(/filename\*?=(?:UTF-8''|")?([^\";]+)"?/i);
  const filename = decodeURIComponent((match?.[1] || fallbackName).replace(/["']/g, ''));
  const url = window.URL.createObjectURL(typedBlob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

/** Authenticated file download — never use window.open (no JWT). */
const downloadAuthenticatedFile = async (path, params = {}, fallbackName = 'download.bin', expectedKinds = []) => {
  const response = await api.get(path, { params, responseType: 'blob' });
  await downloadBlob(response, fallbackName, expectedKinds);
  return true;
};

const createReportsService = (basePath, prefix) => ({
  get: (params = {}) => api.get(basePath, { params }).then((r) => unwrapData(r)),
  downloadCsv: (params = {}) => downloadAuthenticatedFile(
    basePath,
    { ...params, format: 'csv' },
    `${prefix}-${params.type || 'report'}.csv`,
    ['csv'],
  ),
});

export const auditLogsService = {
  list: (params) => api.get('/audit/logs/', { params }).then((r) => unwrapList(r)),
  get: (id) => api.get(`/audit/logs/${id}/`).then((r) => unwrapData(r)),
  filterOptions: () => api.get('/audit/logs/filter-options/').then((r) => unwrapData(r)),
  exportPdf: (id) =>
    api.get(`/audit/logs/${id}/export-pdf/`, { responseType: 'blob' }).then((r) => (
      downloadBlob(r, `audit-log-${id}.pdf`, ['pdf'])
    )),
  exportListPdf: (params) =>
    api.get('/audit/logs/export-pdf/', { params, responseType: 'blob' }).then((r) => (
      downloadBlob(r, 'audit-logs-export.pdf', ['pdf'])
    )),
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

export const studentsService = {
  ...createCrudService('/students/'),
  getImportContext: () => api.get('/students/import-context/').then((r) => unwrapData(r)),
};
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
export const usersService = createCrudService('/auth/users/');
export const campusesService = createCrudService('/tenants/campuses/');
export const academicYearsService = createCrudService('/academics/years/');
export const termsService = createCrudService('/academics/terms/');
export const streamsService = {
  ...createCrudService('/academics/streams/'),
  formOptions: () =>
    api.get('/academics/streams/form-options/').then((r) => unwrapData(r)),
};
export const subjectsService = createCrudService('/academics/subjects/');
export const homeworkService = createCrudService('/academics/homework/');
export const assignmentsService = createCrudService('/academics/assignments/');

export const teachingAssignmentsService = {
  ...createCrudService('/academics/teaching-assignments/'),
  formOptions: () =>
    api.get('/academics/teaching-assignments/form-options/').then((r) => unwrapData(r)),
  bulkAssign: (payload) =>
    api.post('/academics/teaching-assignments/bulk-assign/', payload).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message };
    }),
  syncAssign: (payload) =>
    api.post('/academics/teaching-assignments/sync-assign/', payload).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message };
    }),
  syncTeacher: (payload) =>
    api.post('/academics/teaching-assignments/sync-teacher/', payload).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message };
    }),
};
export const timetablesService = createCrudService('/academics/timetables/');
export const timetableWizardService = {
  // Class-by-class grid builder (primary wizard)
  getWizardContext: () => api.get('/academics/timetables/wizard/context/').then((r) => unwrapData(r)),
  syncPeriods: (periods) => api.post('/academics/timetables/wizard/periods/', { periods }).then((r) => unwrapData(r)),
  getClassGrid: (params = {}) => api.get('/academics/timetables/wizard/grid/', { params }).then((r) => unwrapData(r)),
  saveClassGrid: (payload) => api.post('/academics/timetables/wizard/grid/', payload).then((r) => unwrapData(r)),
  validateGrid: (payload) => api.post('/academics/timetables/wizard/validate/', payload).then((r) => unwrapData(r)),
  defaultTeacher: (params = {}) => api.get('/academics/timetables/wizard/default-teacher/', { params }).then((r) => unwrapData(r)),
  publish: (payload = {}) => api.post('/academics/timetables/wizard/publish/', payload).then((r) => unwrapData(r)),
  unpublish: (payload = {}) => api.post('/academics/timetables/wizard/unpublish/', payload).then((r) => unwrapData(r)),
  createDraft: (payload = {}) => api.post('/academics/timetables/wizard/create-draft/', payload).then((r) => unwrapData(r)),
  printPdf: async (params = {}) => {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v == null || v === '') return;
      if (Array.isArray(v)) v.forEach((item) => search.append(k, item));
      else search.append(k, v);
    });
    const r = await api.get(`/academics/timetables/print.pdf?${search.toString()}`, { responseType: 'blob' });
    // Guard: API may return JSON error with blob content-type mishandled
    if (r.data instanceof Blob && r.data.type && r.data.type.includes('application/json')) {
      const text = await r.data.text();
      let msg = 'Print failed.';
      try { msg = JSON.parse(text)?.message || msg; } catch { /* ignore */ }
      throw new Error(msg);
    }
    return r.data;
  },
  // Legacy auto-generator (still available)
  getContext: () => api.get('/academics/timetables/generate/context/').then((r) => unwrapData(r)),
  generate: (payload) => api.post('/academics/timetables/generate/', payload).then((r) => unwrapData(r)),
  getDraft: (id) => api.get(`/academics/timetables/generate/${id}/`).then((r) => unwrapData(r)),
  regenerate: (id) => api.post(`/academics/timetables/generate/${id}/`, { action: 'regenerate' }).then((r) => unwrapData(r)),
  apply: (id) => api.post(`/academics/timetables/generate/${id}/`, { action: 'apply' }).then((r) => unwrapData(r)),
  listSchedules: (params = {}) => api.get('/academics/timetable-schedules/', { params }).then((r) => {
    const body = r?.data ?? r;
    const data = body?.data ?? body;
    const list = Array.isArray(data) ? data : (data?.results || []);
    return {
      results: list,
      summary: body?.summary || { total: list.length, drafts: 0, published: 0 },
    };
  }),
  getSchedule: (id) => api.get(`/academics/timetable-schedules/${id}/`).then((r) => unwrapData(r)),
  deleteSchedule: (id) => api.delete(`/academics/timetable-schedules/${id}/`).then((r) => unwrapData(r)),
  // Examination timetable (date + time, free invigilator pick)
  getExamContext: () => api.get('/academics/timetables/exam/context/').then((r) => unwrapData(r)),
  createExamDraft: (payload = {}) => api.post('/academics/timetables/exam/create-draft/', payload).then((r) => unwrapData(r)),
  getExamSlots: (params = {}) => api.get('/academics/timetables/exam/slots/', { params }).then((r) => unwrapData(r)),
  saveExamSlots: (payload) => api.post('/academics/timetables/exam/slots/', payload).then((r) => unwrapData(r)),
  validateExamSlots: (payload) => api.post('/academics/timetables/exam/validate/', payload).then((r) => unwrapData(r)),
  publishExam: (payload = {}) => api.post('/academics/timetables/exam/publish/', payload).then((r) => unwrapData(r)),
  printExamPdf: async (params = {}) => {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v == null || v === '') return;
      search.append(k, v);
    });
    const r = await api.get(`/academics/timetables/exam/print.pdf?${search.toString()}`, { responseType: 'blob' });
    if (r.data instanceof Blob && r.data.type && r.data.type.includes('application/json')) {
      const text = await r.data.text();
      let msg = 'Print failed.';
      try { msg = JSON.parse(text)?.message || msg; } catch { /* ignore */ }
      throw new Error(msg);
    }
    return r.data;
  },
};
export const feeCategoriesService = createCrudService('/finance/fee-categories/');
export const feeStructuresService = createCrudService('/finance/fee-structures/');
export const studentFeeBalancesService = createCrudService('/finance/balances/');
export const feePaymentsService = {
  ...createCrudService('/finance/payments/'),
  receipt: (id) => api.get(`/finance/payments/${id}/receipt/`).then((r) => unwrapData(r)),
  approve: (id) => api.post(`/finance/payments/${id}/approve/`).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message, success: body?.success };
  }),
  reverse: (id, payload = {}) => api.post(`/finance/payments/${id}/reverse/`, payload).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message, success: body?.success };
  }),
};
export const invoicesService = createCrudService('/finance/invoices/');
export const feeDiscountsService = {
  ...createCrudService('/finance/discounts/'),
  approve: (id) => api.post(`/finance/discounts/${id}/approve/`).then((r) => unwrapData(r)),
};
export const refundsService = {
  ...createCrudService('/finance/refunds/'),
  approve: (id) => api.post(`/finance/refunds/${id}/approve/`).then((r) => unwrapData(r)),
};
export const miscIncomeService = createCrudService('/finance/misc-income/');
export const financeNotesService = createCrudService('/finance/notes/');
export const financialAccountsService = createCrudService('/finance/accounts/');
export const budgetsService = createCrudService('/finance/budgets/');
export const accountingPeriodsService = {
  ...createCrudService('/finance/periods/'),
  close: (id) => api.post(`/finance/periods/${id}/close/`).then((r) => unwrapData(r)),
  reopen: (id) => api.post(`/finance/periods/${id}/reopen/`).then((r) => unwrapData(r)),
};
export const accountingService = createCrudService('/finance/accounting/');
export const financeWorkspaceService = {
  get: () => api.get('/finance/workspace/').then((r) => unwrapData(r)),
};
export const financeApprovalService = {
  getQueue: () => api.get('/finance/approval-queue/').then((r) => unwrapData(r)),
};
export const financeAnalyticsService = {
  get: () => api.get('/finance/analytics/').then((r) => unwrapData(r)),
};
export const financeReportsService = createReportsService('/finance/reports/', 'finance');
export const hostelReportsService = createReportsService('/hostel/reports/', 'hostel');
export const libraryReportsService = createReportsService('/library/reports/', 'library');
export const hrReportsService = createReportsService('/hr/reports/', 'hr');
export const parentFeeStatementsService = {
  get: (params = {}) => api.get('/finance/parent-statements/', { params }).then((r) => unwrapData(r)),
};
export const resultsAccessService = {
  get: () => api.get('/finance/results-access-policy/').then((r) => unwrapData(r)),
  updateSchool: (payload) => api.put('/finance/results-access-policy/', payload).then((r) => unwrapData(r)),
  updateClass: (classId, payload) => api.put(`/finance/results-access-policy/classes/${classId}/`, payload).then((r) => unwrapData(r)),
};
export const parentPortalService = {
  overview: () => api.get('/students/portal/overview/').then((r) => unwrapData(r)),
  finance: (params = {}) => api.get('/students/portal/finance/', { params }).then((r) => unwrapData(r)),
  academics: (params = {}) => api.get('/students/portal/academics/', { params }).then((r) => unwrapData(r)),
};
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
export const gradingSchemesService = {
  ...createCrudService('/examinations/grading-schemes/'),
  sync: (payload) =>
    api.post('/examinations/grading-schemes/sync/', payload).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message };
    }),
};
export const gradeCalculationService = {
  getOptions: (params = {}) =>
    api.get('/examinations/grade-calculation/options/', { params }).then((r) => unwrapData(r)),
  apply: (payload) =>
    api.post('/examinations/grade-calculation/apply/', payload).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message };
    }),
};
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
export const assignmentMarksService = {
  getOptions: (params = {}) =>
    api.get('/academics/assignment-marks/options/', { params }).then((r) => unwrapData(r)),
  createAssessment: (payload) =>
    api.post('/academics/assignment-marks/create/', payload).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message, success: body?.success };
    }),
  saveBulk: (payload) =>
    api.post('/academics/assignment-marks/bulk/', payload).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message, success: body?.success };
    }),
};
export const assignmentGradeService = {
  getOptions: (params = {}) =>
    api.get('/academics/assignment-grades/options/', { params }).then((r) => unwrapData(r)),
  apply: (payload) =>
    api.post('/academics/assignment-grades/apply/', payload).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message };
    }),
};

export const promotionService = {
  context: () => api.get('/academics/promotion/context/').then((r) => unwrapData(r)),
  preview: (payload) => api.post('/academics/promotion/preview/', payload).then((r) => unwrapData(r)),
  commit: (batchId) => api.post(`/academics/promotion/${batchId}/commit/`).then((r) => unwrapData(r)),
  undo: (batchId) => api.post(`/academics/promotion/${batchId}/undo/`).then((r) => unwrapData(r)),
};
export const academicReportCardsService = {
  latest: (params = {}) => api.get('/academics/report-cards/latest/', { params }).then((r) => unwrapData(r)),
  generate: (payload) => api.post('/academics/report-cards/generate/', payload).then((r) => unwrapData(r)),
  publish: (payload) => api.post('/academics/report-cards/publish/', payload).then((r) => unwrapData(r)),
  pdf: (id) => api.get(`/academics/report-cards/${id}/pdf/`, { responseType: 'blob' }).then(async (r) => {
    const blob = r.data;
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report-card-${id}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  }),
  broadsheet: (params = {}) => api.get('/academics/report-cards/broadsheet.pdf', { params, responseType: 'blob' }).then(async (r) => {
    const blob = r.data;
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'class-broadsheet.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  }),
};
export const reportCardsService = createCrudService('/examinations/report-cards/');

export const dosOpsService = {
  performance: (params = {}) => api.get('/academics/dos/performance/', { params }).then((r) => unwrapData(r)),
  completeness: (params = {}) => api.get('/academics/dos/marks-completeness/', { params }).then((r) => unwrapData(r)),
  teacherLoad: () => api.get('/academics/dos/teacher-load/').then((r) => unwrapData(r)),
  reportStatus: (params = {}) => api.get('/academics/dos/report-status/', { params }).then((r) => unwrapData(r)),
  seedUganda: () => api.post('/academics/uganda-seed/').then((r) => unwrapData(r)),
  unebCsv: async (params = {}) => {
    const r = await api.get('/academics/dos/uneb-candidates.csv', { params, responseType: 'blob' });
    return r.data;
  },
};

export const assessmentSchemesService = createCrudService('/academics/assessment-schemes/');
export const subjectCombinationsService = createCrudService('/academics/subject-combinations/');
export const subjectRegistrationsService = createCrudService('/academics/subject-registrations/');

export const academicCertificatesService = {
  leaving: async (studentId, params = {}) => {
    const r = await api.get(`/academics/certificates/${studentId}/leaving.pdf`, { params, responseType: 'blob' });
    return r.data;
  },
  transcript: async (studentId) => {
    const r = await api.get(`/academics/certificates/${studentId}/transcript.pdf`, { responseType: 'blob' });
    return r.data;
  },
};
export const examsService = {
  ...createCrudService('/examinations/exams/'),
  publish: (id) => api.post(`/examinations/exams/${id}/publish/`).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message, success: body?.success };
  }),
  archive: (id) => api.post(`/examinations/exams/${id}/archive/`).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message, success: body?.success };
  }),
  submitMarks: (id) => api.post(`/examinations/exams/${id}/submit-marks/`).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message, success: body?.success };
  }),
  approveMarks: (id) => api.post(`/examinations/exams/${id}/approve-marks/`).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message, success: body?.success };
  }),
  lockMarks: (id) => api.post(`/examinations/exams/${id}/lock-marks/`).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message, success: body?.success };
  }),
  reopenMarks: (id, payload = {}) => api.post(`/examinations/exams/${id}/reopen-marks/`, payload).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message, success: body?.success };
  }),
};
export const examinationSessionsService = createCrudService('/examinations/sessions/');
export const classNoticesService = {
  ...createCrudService('/academics/class-notices/'),
  publish: (id) => api.post(`/academics/class-notices/${id}/publish/`).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message, success: body?.success };
  }),
};
export const disciplineRemarksService = createCrudService('/academics/discipline-remarks/');
export const lessonAttendanceSessionsService = createCrudService('/attendance/lesson-sessions/');
export const lessonAttendanceEntriesService = createCrudService('/attendance/lesson-entries/');
export const academicWorkspaceService = {
  get: () => api.get('/academics/workspace/').then((r) => unwrapData(r)),
};
export const marksApprovalService = {
  getQueue: () => api.get('/examinations/marks-approval/queue/').then((r) => unwrapData(r)),
  bulkAction: (payload) => api.post('/examinations/workflow/bulk/', payload).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message, success: body?.success };
  }),
};
export const lessonAttendanceBulkService = {
  save: (payload) => api.post('/attendance/lesson-sessions/bulk/', payload).then((r) => {
    const body = r?.data ?? r;
    return { ...(body?.data ?? body), message: body?.message, success: body?.success };
  }),
};
export const classAttendanceService = {
  getOptions: (params = {}) =>
    api.get('/attendance/class-marking/options/', { params }).then((r) => unwrapData(r)),
  saveBulk: (payload) =>
    api.post('/attendance/class-marking/bulk/', payload).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message, success: body?.success };
    }),
};
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
  formOptions: () =>
    api.get('/academics/classes/form-options/').then((r) => unwrapData(r)),
  listOverview: () =>
    api.get('/academics/classes/overview/').then((r) => unwrapData(r)),
  getHub: (classId, params = {}) =>
    api.get(`/academics/classes/${classId}/hub/`, { params }).then((r) => unwrapData(r)),
  listPrefects: (classId, params = {}) =>
    api.get(`/academics/classes/${classId}/prefects/`, { params }).then((r) => unwrapData(r)),
  addPrefect: (classId, payload) =>
    api.post(`/academics/classes/${classId}/prefects/`, payload).then((r) => {
      const body = r?.data ?? r;
      return { ...(body?.data ?? body), message: body?.message };
    }),
    removePrefect: (classId, prefectId) =>
      api.post(`/academics/classes/${classId}/prefects/remove/`, { prefect_id: prefectId }).then((r) => {
        const body = r?.data ?? r;
        return { ...(body?.data ?? body), message: body?.message };
      }),
    getDeletionPreview: (classId) =>
      api.get(`/academics/classes/${classId}/deletion-preview/`).then((r) => unwrapData(r)),
    listStreams: (classId) => streamsService.list({ school_class: classId }),
};
export const attendanceService = createCrudService('/attendance/');

export const financeBillingService = {
  billClass: (payload) => api.post('/finance/billing/bill-class/', payload).then((r) => unwrapData(r)),
  billStudent: (payload) => api.post('/finance/billing/bill-student/', payload).then((r) => unwrapData(r)),
};
export const financeDocumentsService = {
  paymentReceiptPdf: (id) =>
    api.get(`/finance/payments/${id}/receipt.pdf`, { responseType: 'blob' }).then(async (r) => {
      const blob = r.data;
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `receipt-${id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    }),
  invoicePdf: (id) =>
    api.get(`/finance/invoices/${id}/pdf/`, { responseType: 'blob' }).then(async (r) => {
      const blob = r.data;
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `invoice-${id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    }),
  statementPdf: (studentId) =>
    api.get(`/finance/statements/${studentId}/pdf/`, { responseType: 'blob' }).then(async (r) => {
      const blob = r.data;
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `statement-${studentId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    }),
};
export const onlinePaymentsService = {
  listGateways: () => api.get('/finance/online-payments/').then((r) => unwrapData(r)),
  initiate: (payload) => api.post('/finance/online-payments/', payload).then((r) => r.data),
};
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


