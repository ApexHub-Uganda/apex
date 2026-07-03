/** Staff role onboarding metadata (mirrors backend staff_roles.py). */

export const STAFF_CATEGORIES = [
  { value: 'management', label: 'Management' },
  { value: 'teaching', label: 'Teaching' },
  { value: 'administrative', label: 'Administrative' },
  { value: 'support', label: 'Support' },
  { value: 'finance', label: 'Finance' },
];

export const EMPLOYMENT_TYPES = [
  { value: 'full_time', label: 'Full Time' },
  { value: 'part_time', label: 'Part Time' },
  { value: 'contract', label: 'Contract' },
  { value: 'intern', label: 'Intern' },
];

export const GENDER_OPTIONS = [
  { value: '', label: 'Prefer not to say' },
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
];

export const FALLBACK_STAFF_ROLES = [
  { role: 'head_teacher', label: 'Head Teacher', category: 'management', default_designation: 'Head Teacher', requires_teacher_profile: false, portal_access_default: true, description: 'School-wide academic and operational leadership.' },
  { role: 'deputy_head_teacher', label: 'Deputy Head Teacher', category: 'management', default_designation: 'Deputy Head Teacher', requires_teacher_profile: false, portal_access_default: true, description: 'Assists head teacher with daily academic coordination.' },
  { role: 'director_of_studies', label: 'Director of Studies', category: 'management', default_designation: 'Director of Studies', requires_teacher_profile: false, portal_access_default: true, description: 'Oversees curriculum, examinations, and academic standards.' },
  { role: 'head_of_department', label: 'Head of Department', category: 'teaching', default_designation: 'Head of Department', requires_teacher_profile: true, portal_access_default: true, description: 'Leads an academic department and teaching staff.' },
  { role: 'teacher', label: 'Teacher', category: 'teaching', default_designation: 'Teacher', requires_teacher_profile: true, portal_access_default: true, description: 'Classroom instruction, attendance, and academics.' },
  { role: 'bursar', label: 'Bursar / Accountant', category: 'finance', default_designation: 'Bursar / Accountant', requires_teacher_profile: false, portal_access_default: true, description: 'Fees, billing, payroll, and financial reporting.' },
  { role: 'librarian', label: 'Librarian', category: 'support', default_designation: 'Librarian', requires_teacher_profile: false, portal_access_default: true, description: 'Library catalog, borrowing, and returns.' },
  { role: 'hr_manager', label: 'Human Resource Manager', category: 'administrative', default_designation: 'Human Resource Manager', requires_teacher_profile: false, portal_access_default: true, description: 'Staff records, leave, and performance management.' },
  { role: 'transport_manager', label: 'Transport Manager', category: 'support', default_designation: 'Transport Manager', requires_teacher_profile: false, portal_access_default: true, description: 'Fleet, routes, and student transport.' },
  { role: 'hostel_manager', label: 'Hostel Manager', category: 'support', default_designation: 'Hostel Manager', requires_teacher_profile: false, portal_access_default: true, description: 'Boarding, rooms, and allocations.' },
  { role: 'inventory_manager', label: 'Inventory Manager', category: 'support', default_designation: 'Inventory Manager', requires_teacher_profile: false, portal_access_default: true, description: 'Stock, suppliers, and purchase orders.' },
];

export default FALLBACK_STAFF_ROLES;