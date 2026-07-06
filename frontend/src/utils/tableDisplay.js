/** Table list display helpers — serial numbers, hide raw UUIDs, resolve FK labels. */

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/** Map common FK column keys to entity option loader keys. */
export const INFERRED_OPTION_FROM = {
  staff: 'staff',
  student: 'students',
  school_class: 'classes',
  subject: 'subjects',
  exam: 'exams',
  book: 'books',
  route: 'routes',
  room: 'rooms',
  hostel: 'hostels',
  item: 'items',
  payroll_run: 'payrollRuns',
  head: 'staff',
};

export function isUuid(value) {
  return typeof value === 'string' && UUID_RE.test(value.trim());
}

export function inferOptionsFromKey(columnKey) {
  if (!columnKey) return null;
  return INFERRED_OPTION_FROM[columnKey] || null;
}

/**
 * Resolve a human-friendly cell value for list tables.
 * Raw record UUIDs are hidden; show labels or em dash instead.
 */
export function formatTableCellValue(col, row, optionLookups = {}) {
  const key = col.accessor || col.key;
  if (!key || key === 'id' || key === 'actions' || key === '_rowNum') return null;

  const val = col.accessor ? row[col.accessor] : row[col.key];

  for (const suffix of ['_name', '_label', '_title', '_display', '_number']) {
    const companion = row[`${key}${suffix}`];
    if (companion != null && String(companion).trim() !== '') {
      return companion;
    }
  }

  const optionsKey = col.optionsFrom || inferOptionsFromKey(key);
  if (optionsKey && optionLookups[optionsKey] && val != null && val !== '') {
    const match = optionLookups[optionsKey].find(
      (opt) => String(opt.value) === String(val),
    );
    if (match?.label) return match.label;
  }

  if (val == null || val === '') return '—';
  if (isUuid(val)) return '—';
  return val;
}

export const ROW_NUMBER_COLUMN = {
  key: '_rowNum',
  label: '#',
  width: '2.75rem',
  truncate: false,
  sortable: false,
};