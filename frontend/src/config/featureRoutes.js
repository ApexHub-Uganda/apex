/** Maps school-admin route segments to primary subscription feature keys (must exist in DB). */
export const SCHOOL_ROUTE_FEATURES = {
  '': 'dashboard_analytics',
  students: 'student_management',
  staff: 'staff_management',
  classes: 'classes',
  attendance: 'student_attendance',
  finance: 'student_billing',
  library: 'library_management',
  hostel: 'hostel_management',
  transport: 'vehicles',
  inventory: 'inventory_items',
  hr: 'hr_departments',
  payroll: 'payroll_runs',
  reports: 'reports',
  communication: 'announcements',
  settings: 'school_settings',
};

export const getFeatureKeyForPath = (pathname) => {
  const segment = pathname.replace('/school-admin', '').replace(/^\//, '').split('/')[0];
  return SCHOOL_ROUTE_FEATURES[segment] || null;
};