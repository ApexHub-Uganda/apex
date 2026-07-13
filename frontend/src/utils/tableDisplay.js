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

/** Tight column widths for short-value fields (desktop tables stay within viewport). */
export const COL_WIDTH = {
  rowNum: '1.35rem',
  code: '4rem',
  shortCode: '3.25rem',
  admission: '4.5rem',
  employeeId: '4rem',
  nameMin: '7rem',
  nameMax: '14rem',
  class: '3.75rem',
  stream: '3.25rem',
  role: '5.25rem',
  department: '5.5rem',
  phone: '5.5rem',
  email: '8rem',
  status: '3.5rem',
  badge: '3rem',
  count: '2.5rem',
  date: '5.25rem',
  amount: '5.25rem',
  actions: '2.5rem',
};

/** Keys that hold person or record titles — absorb remaining table width. */
const NAME_COLUMN_KEYS = new Set([
  'full_name',
  'name',
  'title',
  'subject',
  'head_name',
  'student_name',
  'staff_name',
  'parent_name',
  'teacher_name',
  'recipient_name',
  'author_name',
]);

/** Short categorical values — fixed narrow width, may truncate with tooltip. */
const SHORT_COLUMN_KEYS = new Set([
  'class_name',
  'stream_name',
  'department_name',
  'portal_role',
  'designation',
  'staff_category',
  'gender',
  'status',
  'children_count',
  'admission_number',
  'employee_id',
  'code',
  'phone',
  'profile',
]);

const BUSINESS_ID_KEYS = new Set([
  'employee_id',
  'admission_number',
  'ticket_number',
  'upi_number',
  'sku',
  'isbn',
  'invoice_number',
  'receipt_number',
  'code',
  'registration_number',
]);

const SECONDARY_LIST_KEYS = new Set([
  'description',
  'notes',
  'details',
  'metadata',
  'created_at',
  'updated_at',
  'modified_at',
  'deleted_at',
  'tenant',
  'tenant_id',
  'is_deleted',
  'address',
  'city',
  'county',
  'sub_county',
  'country',
  'postal_code',
  'alternate_email',
  'alternate_phone',
  'mpesa_phone',
  'qualification_summary',
  'emergency_contact',
  'emergency_phone',
  'parent_names',
  'children_names',
  'personal_email',
  'national_id',
  'nationality',
]);

const WIDTH_BY_KEY = {
  admission_number: COL_WIDTH.admission,
  employee_id: COL_WIDTH.employeeId,
  code: COL_WIDTH.shortCode,

  email: COL_WIDTH.email,
  phone: COL_WIDTH.phone,
  class_name: COL_WIDTH.class,
  stream_name: COL_WIDTH.stream,
  portal_role: COL_WIDTH.role,
  department_name: COL_WIDTH.department,
  designation: COL_WIDTH.role,
  staff_category: COL_WIDTH.badge,
  status: COL_WIDTH.status,
  gender: COL_WIDTH.badge,
  children_count: COL_WIDTH.count,
  start_date: COL_WIDTH.date,
  end_date: COL_WIDTH.date,
  due_date: COL_WIDTH.date,
  exam_date: COL_WIDTH.date,
  payment_date: COL_WIDTH.date,
  amount: COL_WIDTH.amount,
  amount_paid: COL_WIDTH.amount,
  actions: COL_WIDTH.actions,
  _rowNum: COL_WIDTH.rowNum,
};

export function isUuid(value) {
  return typeof value === 'string' && UUID_RE.test(value.trim());
}

export function inferOptionsFromKey(columnKey) {
  if (!columnKey) return null;
  return INFERRED_OPTION_FROM[columnKey] || null;
}

function columnKey(col) {
  return String(col.accessor || col.key || '');
}

export function isNameColumn(col) {
  if (!col) return false;
  if (col.isNameColumn || col.cellType === 'name') return true;
  return NAME_COLUMN_KEYS.has(columnKey(col));
}

export function isShortColumn(col) {
  if (!col || isNameColumn(col)) return false;
  if (col.cellType === 'short' || col.compact) return true;
  const key = columnKey(col);
  if (SHORT_COLUMN_KEYS.has(key)) return true;
  if (col.width && String(col.width).endsWith('rem')) return true;
  return false;
}

export function nameColumn(def) {
  return applyColumnLayout({
    ...def,
    isNameColumn: true,
    minWidth: def.minWidth || COL_WIDTH.nameMin,
    maxWidth: def.maxWidth || COL_WIDTH.nameMax,
  });
}

export function isHiddenListColumn(col) {
  if (col.listPriority === 'primary' || col.primary) return false;
  if (col.hideInList) return true;

  const key = columnKey(col);
  if (!key || key === 'actions' || key === '_rowNum') return false;
  if (key === 'id') return true;
  if (SECONDARY_LIST_KEYS.has(key)) return true;
  if (BUSINESS_ID_KEYS.has(key)) return false;
  if (key.endsWith('_id')) return true;
  return false;
}

export function applyColumnLayout(col) {
  if (isNameColumn(col)) {
    const { width: _width, ...rest } = col;
    return {
      truncate: false,
      isNameColumn: true,
      ...rest,
      minWidth: col.minWidth || COL_WIDTH.nameMin,
      maxWidth: col.maxWidth || COL_WIDTH.nameMax,
    };
  }

  const key = columnKey(col);
  const width = col.width || WIDTH_BY_KEY[key];
  const isShort = isShortColumn({ ...col, width });
  const minWidth = col.minWidth || (width && String(width).endsWith('rem') ? width : undefined);

  return {
    truncate: col.truncate ?? (!col.render && isShort),
    compact: isShort,
    ...col,
    ...(width ? { width } : {}),
    ...(minWidth ? { minWidth } : {}),
  };
}

/**
 * Prepare registry/list columns for dense professional tables.
 * Strips raw IDs and low-value detail fields from list views.
 */
export function sanitizeListColumns(columns = []) {
  return columns
    .filter((col) => !isHiddenListColumn(col))
    .map((col) => applyColumnLayout(col));
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
  width: COL_WIDTH.rowNum,
  truncate: false,
  sortable: false,
};

export function formatClassStream(row) {
  const parts = [row.class_name, row.stream_name].filter(Boolean);
  return parts.length ? parts.join(' · ') : '—';
}