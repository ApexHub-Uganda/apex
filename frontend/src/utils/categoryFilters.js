/** Shared category filter helpers for directory tables. */

export function buildSelectOptions(rows, field, labelMap = {}, optionLabelField) {
  const seen = new Map();

  rows.forEach((row) => {
    const value = row?.[field];
    if (value == null || value === '') return;
    const key = String(value);
    if (seen.has(key)) return;
    const label = labelMap[value]
      || (optionLabelField && row[optionLabelField])
      || String(value).replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    seen.set(key, label);
  });

  return [...seen.entries()]
    .sort((a, b) => String(a[1]).localeCompare(String(b[1])))
    .map(([value, label]) => ({ value, label }));
}

export function applyCategoryFilters(rows, filterDefs, values = {}) {
  if (!rows?.length) return rows || [];

  return rows.filter((row) => filterDefs.every((def) => {
    const selected = values[def.key];
    if (!selected) return true;
    const rowValue = def.getValue ? def.getValue(row) : row[def.field];
    if (rowValue == null || rowValue === '') return false;
    return String(rowValue) === String(selected);
  }));
}

export const STUDENT_STATUS_LABELS = {
  active: 'Active',
  graduated: 'Graduated',
  transferred: 'Transferred',
  suspended: 'Suspended',
  withdrawn: 'Withdrawn',
};

export const STUDENT_GENDER_LABELS = {
  male: 'Male',
  female: 'Female',
  other: 'Other',
};

export const STUDENT_BOARDING_LABELS = {
  day: 'Day Scholar',
  boarding: 'Boarding',
  weekly: 'Weekly Boarding',
};

export const STAFF_CATEGORY_LABELS = {
  management: 'Management',
  teaching: 'Teaching',
  administrative: 'Administrative',
  support: 'Support',
  finance: 'Finance',
};

export const STAFF_EMPLOYMENT_LABELS = {
  full_time: 'Full Time',
  part_time: 'Part Time',
  contract: 'Contract',
  intern: 'Intern',
};

export const STAFF_STATUS_LABELS = {
  active: 'Active',
  on_leave: 'On Leave',
  suspended: 'Suspended',
  terminated: 'Terminated',
};

export const PARENT_RELATIONSHIP_LABELS = {
  father: 'Father',
  mother: 'Mother',
  guardian: 'Guardian',
  sponsor: 'Sponsor',
  other: 'Other',
};

export const PARENT_CONTACT_LABELS = {
  email: 'Email',
  phone: 'Phone',
  sms: 'SMS',
  whatsapp: 'WhatsApp',
};