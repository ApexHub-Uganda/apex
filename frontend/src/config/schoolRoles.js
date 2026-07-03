/** Canonical school portal roles (none exceed school admin). */

export const SCHOOL_PORTAL_ROLES = [
  'school_admin',
  'head_teacher',
  'deputy_head_teacher',
  'director_of_studies',
  'head_of_department',
  'teacher',
  'parent',
  'bursar',
  'finance_officer',
  'librarian',
  'hr_manager',
  'hr_officer',
  'transport_manager',
  'transport_officer',
  'hostel_manager',
  'hostel_warden',
  'inventory_manager',
  'inventory_officer',
];

export const LEGACY_ROLE_ALIASES = {
  finance_officer: 'bursar',
  hr_officer: 'hr_manager',
  transport_officer: 'transport_manager',
  hostel_warden: 'hostel_manager',
  inventory_officer: 'inventory_manager',
};

export const ROLE_LABELS = {
  school_admin: 'School Admin',
  head_teacher: 'Head Teacher',
  deputy_head_teacher: 'Deputy Head Teacher',
  director_of_studies: 'Director of Studies',
  head_of_department: 'Head of Department',
  teacher: 'Teacher',
  parent: 'Parent',
  bursar: 'Bursar / Accountant',
  librarian: 'Librarian',
  hr_manager: 'Human Resource Manager',
  transport_manager: 'Transport Manager',
  hostel_manager: 'Hostel Manager',
  inventory_manager: 'Inventory Manager / Store Keeper',
  finance_officer: 'Finance Officer',
  hr_officer: 'HR Officer',
  transport_officer: 'Transport Officer',
  hostel_warden: 'Hostel Warden',
  inventory_officer: 'Inventory Officer',
};

export const normalizeRole = (role) => LEGACY_ROLE_ALIASES[role] || role || 'teacher';

export const getRoleLabel = (role) => ROLE_LABELS[role] || ROLE_LABELS[normalizeRole(role)]
  || role?.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  || 'User';

export const isSchoolPortalRole = (role) => SCHOOL_PORTAL_ROLES.includes(role);

export const isSchoolAdminRole = (role) => role === 'school_admin';

export default SCHOOL_PORTAL_ROLES;