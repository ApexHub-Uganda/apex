/** Frontend mirror of backend 15 school-admin module bundles (fallback when API unavailable). */
export const SCHOOL_MODULES = [
  {
    key: 'core_management',
    label: 'Core Management',
    icon: 'FiGrid',
    path: '/school-admin/core',
    sort_order: 0,
    // School Settings, Roles & Permissions, Delete User are core platform capabilities
    // (not plan-sellable modules) — see CORE_FEATURE_KEYS / school-admin settings nav.
    feature_keys: [
      'student_management', 'parent_management', 'staff_management', 'departments',
      'user_accounts', 'multi_campus_support',
    ],
    children: [
      { feature_key: 'student_management', label: 'Students', path: '/school-admin/students', icon: 'FiUsers' },
      { feature_key: 'parent_management', label: 'Parents & Guardians', path: '/school-admin/parents', icon: 'FiUsers' },
      { feature_key: 'staff_management', label: 'Staff', path: '/school-admin/staff', icon: 'FiBriefcase' },
      { feature_key: 'departments', label: 'Departments', path: '/school-admin/core/departments', icon: 'FiLayers' },
      { feature_key: 'user_accounts', label: 'User Accounts', path: '/school-admin/core/user-accounts', icon: 'FiUser' },
      { feature_key: 'multi_campus_support', label: 'Multi-campus', path: '/school-admin/core/campuses', icon: 'FiMapPin' },
    ],
  },
  {
    key: 'academics',
    label: 'Academics',
    icon: 'FiBook',
    path: '/school-admin/academics',
    sort_order: 1,
    feature_keys: [
      'teacher_workspace', 'academic_years', 'terms', 'classes', 'streams', 'departments',
      'subjects', 'subject_assignment', 'grading', 'student_promotion', 'homework',
      'assignments', 'timetables', 'periods', 'classrooms', 'class_teacher_tools',
      'hod_workspace', 'dos_workspace', 'teacher_assignments', 'class_notices',
      'discipline_remarks',
    ],
    children: [
      { feature_key: 'teacher_workspace', label: 'Teacher Workspace', path: '/school-admin/academics/teacher', icon: 'FiBookOpen' },
      { feature_key: 'academic_years', label: 'Academic Years', path: '/school-admin/academics/years', icon: 'FiCalendar' },
      { feature_key: 'terms', label: 'Terms', path: '/school-admin/academics/terms', icon: 'FiCalendar' },
      { feature_key: 'classes', label: 'Classes', path: '/school-admin/classes', icon: 'FiBook' },
      { feature_key: 'departments', label: 'Departments', path: '/school-admin/core/departments', icon: 'FiLayers' },
      { feature_key: 'subjects', label: 'Subjects', path: '/school-admin/academics/subjects', icon: 'FiBookOpen' },
      { feature_key: 'subject_assignment', label: 'Subject Assignments', path: '/school-admin/academics/subject-assignments', icon: 'FiUserCheck' },
      { feature_key: 'grading', label: 'Grading', path: '/school-admin/academics/grading', icon: 'FiAward' },
      { feature_key: 'student_promotion', label: 'Student Promotion', path: '/school-admin/academics/promotion', icon: 'FiTrendingUp' },
      { feature_key: 'report_cards', label: 'Report Cards', path: '/school-admin/academics/report-cards', icon: 'FiFileText' },
      { feature_key: 'class_report_cards', label: 'Class Broadsheets', path: '/school-admin/academics/report-cards', icon: 'FiFileText' },
      { feature_key: 'result_processing', label: 'Results', path: '/school-admin/examinations/results', icon: 'FiCheckCircle' },
      { feature_key: 'homework', label: 'Homework', path: '/school-admin/academics/homework', icon: 'FiEdit' },
      { feature_key: 'assignments', label: 'Assignments', path: '/school-admin/academics/assignments', icon: 'FiFileText' },
      { feature_key: 'timetables', label: 'Timetables', path: '/school-admin/academics/timetable/wizard', icon: 'FiClock' },
      { feature_key: 'periods', label: 'Periods', path: '/school-admin/academics/periods', icon: 'FiClock' },
      { feature_key: 'classrooms', label: 'Classrooms', path: '/school-admin/academics/classrooms', icon: 'FiHome' },
      { feature_key: 'class_teacher_tools', label: 'Class Teacher', path: '/school-admin/academics/class-teacher', icon: 'FiUsers' },
      { feature_key: 'hod_workspace', label: 'HoD Workspace', path: '/school-admin/academics/hod', icon: 'FiLayers' },
      { feature_key: 'dos_workspace', label: 'DoS Workspace', path: '/school-admin/academics/dos', icon: 'FiAward' },
      { feature_key: 'dos_workspace', label: 'DoS Analytics & UNEB', path: '/school-admin/academics/dos-ops', icon: 'FiBarChart2' },
      { feature_key: 'teacher_assignments', label: 'Teacher Assignments', path: '/school-admin/academics/subject-assignments', icon: 'FiUserCheck' },
      { feature_key: 'class_notices', label: 'Class Notices', path: '/school-admin/academics/class-notices', icon: 'FiBell' },
      { feature_key: 'discipline_remarks', label: 'Discipline Remarks', path: '/school-admin/academics/discipline', icon: 'FiAlertCircle' },
    ],
  },
  {
    key: 'admissions',
    label: 'Admissions',
    icon: 'FiUserPlus',
    path: '/school-admin/admissions',
    sort_order: 2,
    feature_keys: [
      'admissions', 'admitted_students', 'admission_vacancies',
      'student_documents', 'medical_records',
    ],
    children: [
      { feature_key: 'admissions', label: 'Applications', path: '/school-admin/admissions/applications', icon: 'FiUserPlus' },
      { feature_key: 'admitted_students', label: 'Admitted Students', path: '/school-admin/admissions/admitted', icon: 'FiCheckCircle' },
      { feature_key: 'admission_vacancies', label: 'Advertise', path: '/school-admin/admissions/advertise', icon: 'FiRadio' },
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
    feature_keys: ['student_attendance', 'lesson_attendance', 'staff_attendance', 'attendance_sessions'],
    children: [
      { feature_key: 'student_attendance', label: 'Student Attendance', path: '/school-admin/attendance', icon: 'FiCalendar' },
      { feature_key: 'lesson_attendance', label: 'Lesson Attendance', path: '/school-admin/attendance/lessons', icon: 'FiCheckSquare' },
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
      'examination_management', 'assessment_management', 'marks_entry', 'marks_approval',
      'result_processing', 'report_cards', 'class_report_cards', 'grade_calculation',
      'examination_sessions',
    ],
    children: [
      { feature_key: 'examination_management', label: 'Examinations', path: '/school-admin/examinations', icon: 'FiAward' },
      { feature_key: 'assessment_management', label: 'Assessments', path: '/school-admin/examinations/assessments', icon: 'FiClipboard' },
      { feature_key: 'marks_entry', label: 'Marks Entry', path: '/school-admin/examinations/marks', icon: 'FiEdit' },
      { feature_key: 'grade_calculation', label: 'Grade Calculation', path: '/school-admin/examinations/grades', icon: 'FiPercent' },
      { feature_key: 'result_processing', label: 'Results', path: '/school-admin/examinations/results', icon: 'FiCheckCircle' },
      { feature_key: 'report_cards', label: 'Report Cards', path: '/school-admin/academics/report-cards', icon: 'FiFileText' },
      { feature_key: 'class_report_cards', label: 'Class Broadsheets', path: '/school-admin/academics/report-cards', icon: 'FiFileText' },
      { feature_key: 'marks_approval', label: 'Marks Approval', path: '/school-admin/examinations/approval', icon: 'FiCheckCircle' },
      { feature_key: 'examination_sessions', label: 'Exam Sessions', path: '/school-admin/examinations/sessions', icon: 'FiCalendar' },
    ],
  },
  {
    key: 'finance',
    label: 'Finance',
    icon: 'FiDollarSign',
    path: '/school-admin/finance',
    sort_order: 5,
    feature_keys: [
      'bursar_workspace', 'assistant_bursar_workspace',
      'fee_structures', 'fee_categories', 'discounts', 'student_billing',
      'invoice_generation', 'payment_recording', 'misc_income', 'refunds',
      'debtor_management', 'finance_notes', 'expenses', 'financial_reports',
      'transaction_approval', 'budget_management', 'financial_accounts',
      'accounting_periods', 'finance_analytics', 'parent_fee_statements',
      'salary_structures', 'payroll_runs', 'payslips',
    ],
    children: [
      { feature_key: 'bursar_workspace', label: 'Bursar Workspace', path: '/school-admin/finance/bursar', icon: 'FiDollarSign' },
      { feature_key: 'assistant_bursar_workspace', label: 'Assistant Bursar', path: '/school-admin/finance/assistant', icon: 'FiCreditCard' },
      { feature_key: 'fee_structures', label: 'Fee Structures', path: '/school-admin/finance/structures', icon: 'FiList' },
      { feature_key: 'fee_categories', label: 'Fee Categories', path: '/school-admin/finance/categories', icon: 'FiTag' },
      { feature_key: 'student_billing', label: 'Billing & Invoices', path: '/school-admin/finance', icon: 'FiDollarSign' },
      { feature_key: 'invoice_generation', label: 'Invoices', path: '/school-admin/finance/invoices', icon: 'FiFileText' },
      { feature_key: 'payment_recording', label: 'Payments', path: '/school-admin/finance/payments', icon: 'FiCreditCard' },
      { feature_key: 'debtor_management', label: 'Debtors', path: '/school-admin/finance/debtors', icon: 'FiUsers' },
      { feature_key: 'discounts', label: 'Discounts & Waivers', path: '/school-admin/finance/discounts', icon: 'FiPercent' },
      { feature_key: 'refunds', label: 'Refunds', path: '/school-admin/finance/refunds', icon: 'FiRotateCcw' },
      { feature_key: 'misc_income', label: 'Misc Income', path: '/school-admin/finance/income', icon: 'FiTrendingUp' },
      { feature_key: 'finance_notes', label: 'Finance Notes', path: '/school-admin/finance/notes', icon: 'FiMessageSquare' },
      { feature_key: 'transaction_approval', label: 'Approvals', path: '/school-admin/finance/approval', icon: 'FiCheckCircle' },
      { feature_key: 'expenses', label: 'Expenses', path: '/school-admin/finance/expenses', icon: 'FiTrendingDown' },
      { feature_key: 'budget_management', label: 'Budgets', path: '/school-admin/finance/budgets', icon: 'FiPieChart' },
      { feature_key: 'financial_accounts', label: 'Accounts', path: '/school-admin/finance/accounts', icon: 'FiBook' },
      { feature_key: 'accounting_periods', label: 'Accounting Periods', path: '/school-admin/finance/periods', icon: 'FiCalendar' },
      { feature_key: 'financial_reports', label: 'Financial Reports', path: '/school-admin/finance/reports', icon: 'FiBarChart2' },
      { feature_key: 'finance_analytics', label: 'Finance Analytics', path: '/school-admin/finance/analytics', icon: 'FiActivity' },
      { feature_key: 'parent_fee_statements', label: 'Fee Statements', path: '/school-admin/finance/statements', icon: 'FiFileText' },
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
      'staff_management', 'hr_departments', 'positions', 'leave_types',
      'leave_requests', 'performance_reviews',
    ],
    children: [
      { feature_key: 'staff_management', label: 'Staffs', path: '/school-admin/hr/staffs', icon: 'FiBriefcase' },
      { feature_key: 'hr_departments', label: 'Departments', path: '/school-admin/hr/departments', icon: 'FiLayers' },
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

export const getModuleKeyForFeature = (featureKey) => {
  if (!featureKey) return null;
  const mod = SCHOOL_MODULES.find((m) => (m.feature_keys || []).includes(featureKey));
  return mod?.key || null;
};

/** Flatten child paths → feature_key for FeatureGate routing. */
export const buildRouteFeatureMap = () => {
  const map = {
    '': 'dashboard_analytics',
    students: 'student_management',
    parents: 'parent_management',
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
    // settings / permissions / plans are core school-admin surfaces (not plan SKUs)
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
