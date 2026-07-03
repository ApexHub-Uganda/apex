/** Frontend mirror of backend 15 school-admin module bundles (fallback when API unavailable). */
export const SCHOOL_MODULES = [
  {
    key: 'core_management',
    label: 'Core Management',
    icon: 'FiGrid',
    path: '/school-admin/core',
    sort_order: 0,
    feature_keys: [
      'student_management', 'parent_management', 'staff_management',
      'user_accounts', 'roles_permissions', 'school_settings', 'multi_campus_support',
    ],
    children: [
      { feature_key: 'student_management', label: 'Students', path: '/school-admin/students', icon: 'FiUsers' },
      { feature_key: 'parent_management', label: 'Parents & Guardians', path: '/school-admin/students', icon: 'FiUsers' },
      { feature_key: 'staff_management', label: 'Staff', path: '/school-admin/staff', icon: 'FiBriefcase' },
      { feature_key: 'user_accounts', label: 'User Accounts', path: '/school-admin/settings', icon: 'FiUser' },
      { feature_key: 'roles_permissions', label: 'Roles & Permissions', path: '/school-admin/settings', icon: 'FiShield' },
      { feature_key: 'school_settings', label: 'School Settings', path: '/school-admin/settings', icon: 'FiSettings' },
      { feature_key: 'multi_campus_support', label: 'Multi-campus', path: '/school-admin/settings', icon: 'FiMapPin' },
    ],
  },
  {
    key: 'academics',
    label: 'Academics',
    icon: 'FiBook',
    path: '/school-admin/academics',
    sort_order: 1,
    feature_keys: [
      'academic_years', 'terms', 'classes', 'streams', 'departments', 'subjects',
      'subject_assignment', 'grading', 'student_promotion', 'homework', 'assignments',
      'timetables', 'periods', 'classrooms',
    ],
    children: [
      { feature_key: 'academic_years', label: 'Academic Years', path: '/school-admin/academics/years', icon: 'FiCalendar' },
      { feature_key: 'terms', label: 'Terms', path: '/school-admin/academics/terms', icon: 'FiCalendar' },
      { feature_key: 'classes', label: 'Classes', path: '/school-admin/classes', icon: 'FiBook' },
      { feature_key: 'streams', label: 'Streams', path: '/school-admin/academics/streams', icon: 'FiLayers' },
      { feature_key: 'subjects', label: 'Subjects', path: '/school-admin/academics/subjects', icon: 'FiBookOpen' },
      { feature_key: 'subject_assignment', label: 'Subject Assignment', path: '/school-admin/academics/assignments', icon: 'FiLink' },
      { feature_key: 'grading', label: 'Grading', path: '/school-admin/academics/grading', icon: 'FiAward' },
      { feature_key: 'homework', label: 'Homework', path: '/school-admin/academics/homework', icon: 'FiEdit' },
      { feature_key: 'assignments', label: 'Assignments', path: '/school-admin/academics/assignments', icon: 'FiFileText' },
      { feature_key: 'timetables', label: 'Timetables', path: '/school-admin/academics/timetable', icon: 'FiClock' },
      { feature_key: 'periods', label: 'Periods', path: '/school-admin/academics/periods', icon: 'FiClock' },
      { feature_key: 'classrooms', label: 'Classrooms', path: '/school-admin/academics/classrooms', icon: 'FiHome' },
    ],
  },
  {
    key: 'admissions',
    label: 'Admissions',
    icon: 'FiUserPlus',
    path: '/school-admin/admissions',
    sort_order: 2,
    feature_keys: ['admissions', 'student_documents', 'medical_records'],
    children: [
      { feature_key: 'admissions', label: 'Applications', path: '/school-admin/admissions', icon: 'FiUserPlus' },
      { feature_key: 'student_documents', label: 'Student Documents', path: '/school-admin/admissions/documents', icon: 'FiFile' },
      { feature_key: 'medical_records', label: 'Medical Records', path: '/school-admin/admissions/medical', icon: 'FiHeart' },
    ],
  },
  {
    key: 'attendance',
    label: 'Attendance',
    icon: 'FiCalendar',
    path: '/school-admin/attendance',
    sort_order: 3,
    feature_keys: ['student_attendance', 'staff_attendance', 'attendance_sessions'],
    children: [
      { feature_key: 'student_attendance', label: 'Student Attendance', path: '/school-admin/attendance', icon: 'FiCalendar' },
      { feature_key: 'staff_attendance', label: 'Staff Attendance', path: '/school-admin/attendance/staff', icon: 'FiBriefcase' },
      { feature_key: 'attendance_sessions', label: 'Attendance Sessions', path: '/school-admin/attendance/sessions', icon: 'FiClock' },
    ],
  },
  {
    key: 'examinations',
    label: 'Examinations',
    icon: 'FiAward',
    path: '/school-admin/examinations',
    sort_order: 4,
    feature_keys: [
      'examination_management', 'marks_entry', 'result_processing',
      'report_cards', 'grade_calculation',
    ],
    children: [
      { feature_key: 'examination_management', label: 'Examinations', path: '/school-admin/examinations', icon: 'FiAward' },
      { feature_key: 'marks_entry', label: 'Marks Entry', path: '/school-admin/examinations/marks', icon: 'FiEdit' },
      { feature_key: 'result_processing', label: 'Result Processing', path: '/school-admin/examinations/results', icon: 'FiCheckCircle' },
      { feature_key: 'report_cards', label: 'Report Cards', path: '/school-admin/examinations/report-cards', icon: 'FiFileText' },
      { feature_key: 'grade_calculation', label: 'Grade Calculation', path: '/school-admin/examinations/grades', icon: 'FiPercent' },
    ],
  },
  {
    key: 'finance',
    label: 'Finance',
    icon: 'FiDollarSign',
    path: '/school-admin/finance',
    sort_order: 5,
    feature_keys: [
      'fee_structures', 'fee_categories', 'discounts', 'student_billing',
      'invoice_generation', 'payment_recording', 'expenses', 'financial_reports',
      'salary_structures', 'payroll_runs', 'payslips',
    ],
    children: [
      { feature_key: 'fee_structures', label: 'Fee Structures', path: '/school-admin/finance/structures', icon: 'FiList' },
      { feature_key: 'student_billing', label: 'Billing & Invoices', path: '/school-admin/finance', icon: 'FiDollarSign' },
      { feature_key: 'payment_recording', label: 'Payments', path: '/school-admin/finance/payments', icon: 'FiCreditCard' },
      { feature_key: 'expenses', label: 'Expenses', path: '/school-admin/finance/expenses', icon: 'FiTrendingDown' },
      { feature_key: 'financial_reports', label: 'Financial Reports', path: '/school-admin/finance/reports', icon: 'FiBarChart2' },
      { feature_key: 'salary_structures', label: 'Salary Structures', path: '/school-admin/finance/payroll/structures', icon: 'FiLayers' },
      { feature_key: 'payroll_runs', label: 'Payroll Runs', path: '/school-admin/payroll', icon: 'FiCreditCard' },
      { feature_key: 'payslips', label: 'Payslips', path: '/school-admin/finance/payroll/payslips', icon: 'FiFileText' },
    ],
  },
  {
    key: 'library',
    label: 'Library',
    icon: 'FiBookOpen',
    path: '/school-admin/library',
    sort_order: 6,
    feature_keys: [
      'library_management', 'book_categories', 'borrowing',
      'returns', 'reservations', 'library_fines',
    ],
    children: [
      { feature_key: 'library_management', label: 'Catalog', path: '/school-admin/library', icon: 'FiBookOpen' },
      { feature_key: 'borrowing', label: 'Borrowing', path: '/school-admin/library/borrowing', icon: 'FiBook' },
      { feature_key: 'returns', label: 'Returns', path: '/school-admin/library/returns', icon: 'FiRotateCcw' },
      { feature_key: 'reservations', label: 'Reservations', path: '/school-admin/library/reservations', icon: 'FiBookmark' },
    ],
  },
  {
    key: 'hostel',
    label: 'Hostels',
    icon: 'FiHome',
    path: '/school-admin/hostel',
    sort_order: 7,
    feature_keys: ['hostel_management', 'rooms', 'room_allocation'],
    children: [
      { feature_key: 'hostel_management', label: 'Hostels', path: '/school-admin/hostel', icon: 'FiHome' },
      { feature_key: 'rooms', label: 'Rooms', path: '/school-admin/hostel/rooms', icon: 'FiGrid' },
      { feature_key: 'room_allocation', label: 'Allocations', path: '/school-admin/hostel/allocations', icon: 'FiUsers' },
    ],
  },
  {
    key: 'transport',
    label: 'Transport',
    icon: 'FiTruck',
    path: '/school-admin/transport',
    sort_order: 8,
    feature_keys: ['vehicles', 'routes', 'stops', 'student_transport_assignment'],
    children: [
      { feature_key: 'vehicles', label: 'Vehicles', path: '/school-admin/transport', icon: 'FiTruck' },
      { feature_key: 'routes', label: 'Routes', path: '/school-admin/transport/routes', icon: 'FiMap' },
      { feature_key: 'student_transport_assignment', label: 'Student Assignments', path: '/school-admin/transport/assignments', icon: 'FiUsers' },
    ],
  },
  {
    key: 'inventory',
    label: 'Inventory',
    icon: 'FiPackage',
    path: '/school-admin/inventory',
    sort_order: 9,
    feature_keys: [
      'inventory_categories', 'inventory_items', 'suppliers',
      'purchase_orders', 'stock_movement',
    ],
    children: [
      { feature_key: 'inventory_items', label: 'Items', path: '/school-admin/inventory', icon: 'FiPackage' },
      { feature_key: 'suppliers', label: 'Suppliers', path: '/school-admin/inventory/suppliers', icon: 'FiTruck' },
      { feature_key: 'purchase_orders', label: 'Purchase Orders', path: '/school-admin/inventory/orders', icon: 'FiShoppingCart' },
      { feature_key: 'stock_movement', label: 'Stock Movement', path: '/school-admin/inventory/movements', icon: 'FiTrendingUp' },
    ],
  },
  {
    key: 'human_resource',
    label: 'Human Resource',
    icon: 'FiUsers',
    path: '/school-admin/hr',
    sort_order: 10,
    feature_keys: [
      'hr_departments', 'positions', 'leave_types',
      'leave_requests', 'performance_reviews',
    ],
    children: [
      { feature_key: 'hr_departments', label: 'Departments', path: '/school-admin/hr', icon: 'FiLayers' },
      { feature_key: 'leave_requests', label: 'Leave Requests', path: '/school-admin/hr/leave', icon: 'FiCalendar' },
      { feature_key: 'performance_reviews', label: 'Performance Reviews', path: '/school-admin/hr/reviews', icon: 'FiStar' },
    ],
  },
  {
    key: 'communication',
    label: 'Communication',
    icon: 'FiMessageSquare',
    path: '/school-admin/communication',
    sort_order: 11,
    feature_keys: [
      'announcements', 'notifications', 'email_templates',
      'sms_communication', 'broadcast_messaging',
    ],
    children: [
      { feature_key: 'announcements', label: 'Announcements', path: '/school-admin/communication', icon: 'FiMessageSquare' },
      { feature_key: 'notifications', label: 'Notifications', path: '/school-admin/notifications', icon: 'FiBell' },
      { feature_key: 'email_templates', label: 'Email Templates', path: '/school-admin/communication/emails', icon: 'FiMail' },
      { feature_key: 'sms_communication', label: 'SMS', path: '/school-admin/communication/sms', icon: 'FiSmartphone' },
      { feature_key: 'broadcast_messaging', label: 'Broadcast', path: '/school-admin/communication/broadcast', icon: 'FiRadio' },
    ],
  },
  {
    key: 'events',
    label: 'Events & Calendar',
    icon: 'FiCalendar',
    path: '/school-admin/events',
    sort_order: 12,
    feature_keys: ['event_management', 'event_registration'],
    children: [
      { feature_key: 'event_management', label: 'Events', path: '/school-admin/events', icon: 'FiCalendar' },
      { feature_key: 'event_registration', label: 'Registrations', path: '/school-admin/events/registrations', icon: 'FiUserCheck' },
    ],
  },
  {
    key: 'analytics',
    label: 'Analytics',
    icon: 'FiBarChart2',
    path: '/school-admin/analytics',
    sort_order: 13,
    feature_keys: ['dashboard_analytics', 'reports', 'statistics', 'data_snapshots'],
    children: [
      { feature_key: 'dashboard_analytics', label: 'Dashboard Analytics', path: '/school-admin', icon: 'FiHome' },
      { feature_key: 'reports', label: 'Reports', path: '/school-admin/reports', icon: 'FiFileText' },
      { feature_key: 'statistics', label: 'Statistics', path: '/school-admin/analytics/statistics', icon: 'FiBarChart2' },
      { feature_key: 'data_snapshots', label: 'Data Snapshots', path: '/school-admin/analytics/snapshots', icon: 'FiDatabase' },
    ],
  },
  {
    key: 'support',
    label: 'Support',
    icon: 'FiLifeBuoy',
    path: '/school-admin/support',
    sort_order: 14,
    feature_keys: ['support_tickets', 'ticket_replies'],
    children: [
      { feature_key: 'support_tickets', label: 'Support Tickets', path: '/school-admin/support', icon: 'FiLifeBuoy' },
      { feature_key: 'ticket_replies', label: 'Ticket Replies', path: '/school-admin/support/replies', icon: 'FiMessageCircle' },
    ],
  },
];

export const getModuleByKey = (key) => SCHOOL_MODULES.find((m) => m.key === key);

/** Flatten child paths → feature_key for FeatureGate routing. */
export const buildRouteFeatureMap = () => {
  const map = {
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
    'settings/plans': 'school_settings',
    notifications: 'notifications',
    core: 'student_management',
    academics: 'academic_years',
    admissions: 'admissions',
    examinations: 'examination_management',
    events: 'event_management',
    analytics: 'dashboard_analytics',
    support: 'support_tickets',
  };

  SCHOOL_MODULES.forEach((mod) => {
    (mod.children || []).forEach((child) => {
      const segment = child.path.replace('/school-admin/', '');
      if (segment) map[segment] = child.feature_key;
    });
  });

  return map;
};