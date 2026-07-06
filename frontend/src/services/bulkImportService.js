import api from './api';

const unwrapData = (response) => {
  const data = response?.data ?? response;
  return data?.data ?? data;
};

const downloadBlob = (response, fallbackName) => {
  const blob = new Blob([response.data], { type: response.headers['content-type'] || 'text/csv' });
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

export function createBulkImportService(basePath) {
  const normalized = basePath.endsWith('/') ? basePath : `${basePath}/`;
  return {
    downloadTemplate: () =>
      api.get(`${normalized}import-template/`, { responseType: 'blob' }).then((r) => {
        downloadBlob(r, 'import_template.csv');
      }),
    validate: (file) => {
      const form = new FormData();
      form.append('file', file);
      return api.post(`${normalized}validate-import/`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then((r) => {
        const body = r?.data ?? r;
        return { ...(body?.data ?? body), message: body?.message };
      });
    },
    commit: (rows) =>
      api.post(`${normalized}commit-import/`, { rows }).then((r) => {
        const body = r?.data ?? r;
        return { ...(unwrapData(r) ?? {}), message: body?.message, success: body?.success };
      }),
  };
}

export const studentBulkImport = createBulkImportService('/students');
export const parentBulkImport = createBulkImportService('/students/parents');
export const staffBulkImport = createBulkImportService('/staff');