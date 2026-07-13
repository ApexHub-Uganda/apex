import api from './api';

const unwrapData = (response) => {
  const data = response?.data ?? response;
  return data?.data ?? data;
};

const EXCEL_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

const downloadBlob = (response, fallbackName) => {
  const contentType = response.headers['content-type'] || EXCEL_CONTENT_TYPE;
  if (!response.data || response.data.size === 0) {
    throw new Error('Template file was empty. Try again.');
  }
  const blob = new Blob([response.data], { type: contentType });
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

const parseApiErrorMessage = async (error, fallback) => {
  const data = error?.response?.data;
  if (!data) return fallback;
  if (typeof data === 'string') return data;
  if (data instanceof Blob) {
    try {
      const text = await data.text();
      const parsed = JSON.parse(text);
      return parsed?.message || parsed?.detail || parsed?.error?.message || fallback;
    } catch {
      return fallback;
    }
  }
  return data?.message || data?.detail || data?.error?.message || fallback;
};

export function createBulkImportService(basePath, { withClassContext = false, templateFallback = 'import_template.xlsx' } = {}) {
  const normalized = basePath.endsWith('/') ? basePath : `${basePath}/`;
  return {
    downloadTemplate: async () => {
      try {
        const response = await api.get(`${normalized}import-template/?file_format=xlsx`, { responseType: 'blob' });
        const contentType = response.headers['content-type'] || '';
        if (contentType.includes('application/json')) {
          const text = await response.data.text();
          const parsed = JSON.parse(text);
          throw new Error(parsed?.message || parsed?.detail || 'Unable to download template.');
        }
        downloadBlob(response, templateFallback);
      } catch (error) {
        if (error?.message && !error?.response) throw error;
        const message = await parseApiErrorMessage(error, 'Unable to download template. Try again.');
        throw new Error(message);
      }
    },
    validate: (file, context = {}) => {
      const form = new FormData();
      form.append('file', file);
      if (withClassContext) {
        if (context.school_class) form.append('school_class', context.school_class);
        if (context.stream) form.append('stream', context.stream);
      }
      return api.post(`${normalized}validate-import/`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then((r) => {
        const body = r?.data ?? r;
        return { ...(body?.data ?? body), message: body?.message };
      });
    },
    commit: (rows, context = {}) =>
      api.post(`${normalized}commit-import/`, {
        rows,
        ...(withClassContext ? {
          school_class: context.school_class || undefined,
          stream: context.stream || undefined,
        } : {}),
      }).then((r) => {
        const body = r?.data ?? r;
        return { ...(unwrapData(r) ?? {}), message: body?.message, success: body?.success };
      }),
  };
}

export const studentBulkImport = createBulkImportService('/students', {
  withClassContext: true,
  templateFallback: 'students_import_template.xlsx',
});
export const parentBulkImport = createBulkImportService('/students/parents', {
  templateFallback: 'parents_import_template.xlsx',
});
export const staffBulkImport = createBulkImportService('/staff', {
  templateFallback: 'staff_import_template.xlsx',
});