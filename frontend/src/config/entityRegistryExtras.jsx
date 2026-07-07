/**
 * Supplemental entity configs for school-admin feature keys not in entityRegistry.jsx.
 * Merged by getEntityConfig — extras override base entries where keys collide.
 */
import {
  periodsService,
  classroomsService,
  gradingScalesService,

  reportCardsService,
  borrowsService,
  roomsService,
  allocationsService,
  stockMovementsService,
  procurementsService,
  performanceReviewsService,
  payslipsService,
  smsService,
  emailsService,
  broadcastsService,
  supportTicketsService,
  ticketRepliesService,
  eventsService,
  eventRegistrationsService,
  routesService,
  studentTransportService,
  invoicesService,
  feeCategoriesService,
  studentFeeBalancesService,
  feeDiscountsService,
  refundsService,
  miscIncomeService,
  financeNotesService,
  financialAccountsService,
  budgetsService,
  accountingPeriodsService,
  notificationsService,
  booksService,
  assignmentsService,
  attendanceService,
  classNoticesService,
  disciplineRemarksService,
  examinationSessionsService,
  leavesService,
  payrollRunsService,
} from '../services/moduleService';

const yesNo = (v) => (v ? 'Yes' : '—');

const redirectEntry = (redirectTo, subtitle, backLink = null) => ({
  subtitle,
  ...(backLink ? { backLink } : {}),
  columns: [],
  formFields: [],
  emptyForm: {},
  redirectTo,
});

const attendanceStatusOptions = [
  { value: 'present', label: 'Present' },
  { value: 'absent', label: 'Absent' },
  { value: 'late', label: 'Late' },
  { value: 'excused', label: 'Excused' },
];

const gradingScaleColumns = [
  { key: 'name', label: 'Scale', accessor: 'name', sortable: true },
  { key: 'grade', label: 'Grade', accessor: 'grade' },
  { key: 'min_score', label: 'Min Score', accessor: 'min_score' },
  { key: 'max_score', label: 'Max Score', accessor: 'max_score' },
  { key: 'grade_point', label: 'Points', accessor: 'grade_point' },
];

const gradingScaleFormFields = [
  { name: 'name', label: 'Scale Name', required: true, placeholder: 'e.g. A Grade' },
  { name: 'grade', label: 'Letter Grade', required: true, placeholder: 'A' },
  { name: 'min_score', label: 'Min Score', type: 'number', required: true },
  { name: 'max_score', label: 'Max Score', type: 'number', required: true },
  { name: 'grade_point', label: 'Grade Point', type: 'number' },
  { name: 'remarks', label: 'Remarks' },
];

const gradingScaleEmptyForm = {
  name: '', grade: '', min_score: '', max_score: '', grade_point: '', remarks: '',
};

export const ENTITY_REGISTRY_EXTRAS = {
  // ── Redirects to dedicated workspace pages ──────────────────────────────
  terms: redirectEntry(
    '/school-admin/academics/terms',
    'Manage academic terms within each school year',
    { to: '/school-admin/academics', label: 'Academics' },
  ),
  classes: redirectEntry(
    '/school-admin/classes',
    'Classes, streams, and enrolment capacity',
    { to: '/school-admin/academics', label: 'Academics' },
  ),
  student_management: redirectEntry(
    '/school-admin/students',
    'Student profiles, enrolment, and academic records',
  ),
  parent_management: redirectEntry(
    '/school-admin/parents',
    'Parents, guardians, and student linkage',
  ),
  staff_management: redirectEntry(
    '/school-admin/hr/staffs',
    'Staff directory, roles, and employment records',
    { to: '/school-admin/hr', label: 'HR' },
  ),
  student_billing: redirectEntry(
    '/school-admin/finance',
    'Student billing, invoices, and payment history',
    { to: '/school-admin/finance', label: 'Finance' },
  ),
  financial_reports: redirectEntry(
    '/school-admin/finance/reports',
    'Financial summaries and exportable reports',
    { to: '/school-admin/finance', label: 'Finance' },
  ),
  dashboard_analytics: redirectEntry(
    '/school-admin',
    'School overview, KPIs, and quick actions',
  ),
  reports: redirectEntry(
    '/school-admin/reports',
    'Generate and download school reports',
  ),
  statistics: redirectEntry(
    '/school-admin/analytics/statistics',
    'Enrollment, attendance, and performance statistics',
    { to: '/school-admin/analytics', label: 'Analytics' },
  ),
  data_snapshots: redirectEntry(
    '/school-admin/analytics/snapshots',
    'Point-in-time data snapshots for auditing',
    { to: '/school-admin/analytics', label: 'Analytics' },
  ),
  user_accounts: redirectEntry(
    '/school-admin/settings',
    'User accounts and login credentials',
    { to: '/school-admin/settings', label: 'Settings' },
  ),
  roles_permissions: redirectEntry(
    '/school-admin/settings',
    'Role-based access and feature permissions',
    { to: '/school-admin/settings', label: 'Settings' },
  ),
  school_settings: redirectEntry(
    '/school-admin/settings',
    'School profile, branding, and preferences',
    { to: '/school-admin/settings', label: 'Settings' },
  ),
  multi_campus_support: redirectEntry(
    '/school-admin/settings',
    'Multi-campus configuration and branch settings',
    { to: '/school-admin/settings', label: 'Settings' },
  ),
  hostel_management: redirectEntry(
    '/school-admin/hostel',
    'Hostel blocks, wardens, and capacity',
    { to: '/school-admin/hostel', label: 'Hostels' },
  ),

  student_promotion: redirectEntry(
    '/school-admin/students',
    'Promote students to the next class or stream',
    { to: '/school-admin/students', label: 'Students' },
  ),
  positions: redirectEntry(
    '/school-admin/hr/leave',
    'Staff positions and job titles',
    { to: '/school-admin/hr', label: 'HR' },
  ),
  leave_types: redirectEntry(
    '/school-admin/hr/leave',
    'Leave types and entitlement policies',
    { to: '/school-admin/hr', label: 'HR' },
  ),
  parent_fee_statements: redirectEntry(
    '/school-admin/finance/statements',
    'Read-only fee statements for linked children',
    { to: '/school-admin/finance', label: 'Finance' },
  ),

  bursar_workspace: redirectEntry(
    '/school-admin/finance/bursar',
    'Bursar financial oversight and approvals',
    { to: '/school-admin/finance', label: 'Finance' },
  ),
  assistant_bursar_workspace: redirectEntry(
    '/school-admin/finance/assistant',
    'Assistant bursar daily collections workspace',
    { to: '/school-admin/finance', label: 'Finance' },
  ),
  transaction_approval: redirectEntry(
    '/school-admin/finance/approval',
    'Approve or reverse financial transactions',
    { to: '/school-admin/finance', label: 'Finance' },
  ),

  payment_recording: redirectEntry(
    '/school-admin/finance/payments',
    'Record student fee payments',
    { to: '/school-admin/finance', label: 'Finance' },
  ),

  finance_analytics: redirectEntry(
    '/school-admin/finance/analytics',
    'Finance dashboards and collection KPIs',
    { to: '/school-admin/finance', label: 'Finance' },
  ),

  student_documents: redirectEntry(
    '/school-admin/admissions',
    'Student documents and admission files',
    { to: '/school-admin/admissions', label: 'Admissions' },
  ),
  reservations: redirectEntry(
    '/school-admin/library/borrowing',
    'Book reservations and hold requests',
    { to: '/school-admin/library', label: 'Library' },
  ),
  result_processing: redirectEntry(
    '/school-admin/examinations/report-cards',
    'Process exam results and publish report cards',
    { to: '/school-admin/examinations', label: 'Examinations' },
  ),

  // ── Academics ─────────────────────────────────────────────────────────
  periods: {
    service: periodsService,
    queryKey: ['periods'],
    createLabel: 'Add Period',
    subtitle: 'Daily timetable periods and break slots',
    backLink: { to: '/school-admin/academics', label: 'Academics' },
    columns: [
      { key: 'name', label: 'Period', accessor: 'name', sortable: true },
      { key: 'start_time', label: 'Starts', accessor: 'start_time' },
      { key: 'end_time', label: 'Ends', accessor: 'end_time' },
      { key: 'sort_order', label: 'Order', accessor: 'sort_order' },
      { key: 'is_break', label: 'Break', render: (row) => yesNo(row.is_break) },
    ],
    formFields: [
      { name: 'name', label: 'Period Name', required: true, placeholder: 'e.g. Period 1' },
      { name: 'start_time', label: 'Start Time', type: 'time', required: true },
      { name: 'end_time', label: 'End Time', type: 'time', required: true },
      { name: 'sort_order', label: 'Sort Order', type: 'number' },
      { name: 'is_break', label: 'Break Period', type: 'checkbox', checkboxLabel: 'This is a break / recess period' },
    ],
    emptyForm: { name: '', start_time: '', end_time: '', sort_order: 1, is_break: false },
  },

  classrooms: {
    service: classroomsService,
    queryKey: ['classrooms'],
    createLabel: 'Add Classroom',
    subtitle: 'Physical rooms used for teaching and labs',
    backLink: { to: '/school-admin/academics', label: 'Academics' },
    columns: [
      { key: 'name', label: 'Room', accessor: 'name', sortable: true },
      { key: 'code', label: 'Code', accessor: 'code' },
      { key: 'building', label: 'Building', accessor: 'building' },
      { key: 'capacity', label: 'Capacity', accessor: 'capacity' },
      { key: 'is_available', label: 'Available', render: (row) => yesNo(row.is_available) },
    ],
    formFields: [
      { name: 'name', label: 'Room Name', required: true },
      { name: 'code', label: 'Room Code', required: true },
      { name: 'building', label: 'Building' },
      { name: 'floor', label: 'Floor' },
      { name: 'capacity', label: 'Capacity', type: 'number' },
      { name: 'room_type', label: 'Type', type: 'select', options: [
        { value: 'classroom', label: 'Classroom' },
        { value: 'lab', label: 'Laboratory' },
        { value: 'hall', label: 'Hall' },
        { value: 'office', label: 'Office' },
        { value: 'other', label: 'Other' },
      ] },
      { name: 'is_available', label: 'Available', type: 'checkbox', checkboxLabel: 'Room is available for use' },
    ],
    emptyForm: {
      name: '', code: '', building: '', floor: '', capacity: 40,
      room_type: 'classroom', is_available: true,
    },
  },

  grading: {
    service: gradingScalesService,
    queryKey: ['grading-scales'],
    createLabel: 'Add Grade Band',
    subtitle: 'Letter grades and score ranges for assessments',
    backLink: { to: '/school-admin/academics', label: 'Academics' },
    columns: gradingScaleColumns,
    formFields: gradingScaleFormFields,
    emptyForm: gradingScaleEmptyForm,
  },

  assignments: {
    service: assignmentsService,
    queryKey: ['assignments'],
    createLabel: 'Add Assignment',
    subtitle: 'Class assignments and due dates',
    backLink: { to: '/school-admin/academics', label: 'Academics' },
    columns: [
      { key: 'title', label: 'Title', accessor: 'title', sortable: true },
      { key: 'due_date', label: 'Due', accessor: 'due_date' },
    ],
    formFields: [
      { name: 'title', label: 'Title', required: true },
      { name: 'description', label: 'Description', type: 'textarea', required: true },
      { name: 'school_class', label: 'Class', type: 'select', required: true, optionsFrom: 'classes' },
      { name: 'subject', label: 'Subject', type: 'select', required: true, optionsFrom: 'subjects' },
      { name: 'due_date', label: 'Due Date', type: 'datetime-local', required: true },
      { name: 'max_score', label: 'Max Score', type: 'number' },
    ],
    emptyForm: {
      title: '', description: '', school_class: '', subject: '',
      due_date: '', max_score: 100,
    },
  },

  // ── Examinations ────────────────────────────────────────────────────────
  grade_calculation: {
    service: gradingScalesService,
    queryKey: ['grade-calculation-scales'],
    createLabel: 'Add Scale Entry',
    subtitle: 'Configure how numeric scores map to letter grades',
    backLink: { to: '/school-admin/examinations', label: 'Examinations' },
    columns: gradingScaleColumns,
    formFields: gradingScaleFormFields,
    emptyForm: gradingScaleEmptyForm,
  },

  marks_entry: redirectEntry(
    '/school-admin/examinations/marks',
    'Subject-first marks entry workflow',
    { to: '/school-admin/examinations', label: 'Examinations' },
  ),

  marks_approval: redirectEntry(
    '/school-admin/examinations/approval',
    'Review and approve submitted mark sheets',
    { to: '/school-admin/examinations', label: 'Examinations' },
  ),

  assessment_management: redirectEntry(
    '/school-admin/examinations/assessments',
    'Publish draft assessments for marks entry',
    { to: '/school-admin/examinations', label: 'Examinations' },
  ),

  teacher_workspace: redirectEntry(
    '/school-admin/academics/teacher',
    'Personal teaching dashboard',
    { to: '/school-admin/academics', label: 'Academics' },
  ),

  hod_workspace: redirectEntry(
    '/school-admin/academics/hod',
    'Department academic coordination',
    { to: '/school-admin/academics', label: 'Academics' },
  ),

  dos_workspace: redirectEntry(
    '/school-admin/academics/dos',
    'School-wide academic oversight',
    { to: '/school-admin/academics', label: 'Academics' },
  ),

  class_teacher_tools: redirectEntry(
    '/school-admin/academics/class-teacher',
    'Class welfare tools for assigned class teachers',
    { to: '/school-admin/academics/teacher', label: 'Teacher Workspace' },
  ),

  lesson_attendance: redirectEntry(
    '/school-admin/attendance/lessons',
    'Mark attendance per lesson session',
    { to: '/school-admin/attendance', label: 'Attendance' },
  ),

  examination_sessions: {
    service: examinationSessionsService,
    queryKey: ['examination-sessions'],
    createLabel: 'Add Exam Session',
    subtitle: 'School-wide examination windows and calendars',
    backLink: { to: '/school-admin/examinations', label: 'Examinations' },
    columns: [
      { key: 'name', label: 'Session', accessor: 'name', sortable: true },
      { key: 'academic_year_name', label: 'Year', accessor: 'academic_year_name' },
      { key: 'term_name', label: 'Term', accessor: 'term_name' },
      { key: 'start_date', label: 'Starts', accessor: 'start_date' },
      { key: 'end_date', label: 'Ends', accessor: 'end_date' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'name', label: 'Session Name', required: true },
      { name: 'academic_year', label: 'Academic Year', type: 'select', required: true, optionsFrom: 'academic_years' },
      { name: 'term', label: 'Term', type: 'select', optionsFrom: 'terms' },
      { name: 'start_date', label: 'Start Date', type: 'date', required: true },
      { name: 'end_date', label: 'End Date', type: 'date', required: true },
      { name: 'status', label: 'Status', type: 'select', options: [
        { value: 'planned', label: 'Planned' },
        { value: 'active', label: 'Active' },
        { value: 'closed', label: 'Closed' },
      ] },
      { name: 'description', label: 'Description', type: 'textarea' },
    ],
    emptyForm: {
      name: '', academic_year: '', term: '', start_date: '', end_date: '',
      status: 'planned', description: '',
    },
  },

  class_notices: {
    service: classNoticesService,
    queryKey: ['class-notices'],
    createLabel: 'Add Notice',
    subtitle: 'Notices for your assigned class',
    backLink: { to: '/school-admin/academics/class-teacher', label: 'Class Teacher' },
    columns: [
      { key: 'title', label: 'Title', accessor: 'title', sortable: true },
      { key: 'school_class_name', label: 'Class', accessor: 'school_class_name' },
      {
        key: 'is_published',
        label: 'Published',
        render: (row) => (row.is_published
          ? <span className="badge text-bg-success-subtle border text-success">Published</span>
          : 'Draft'),
      },
    ],
    formFields: [
      { name: 'school_class', label: 'Class', type: 'select', required: true, optionsFrom: 'classes' },
      { name: 'title', label: 'Title', required: true },
      { name: 'body', label: 'Body', type: 'textarea', required: true },
      { name: 'is_published', label: 'Published', type: 'checkbox', checkboxLabel: 'Publish immediately' },
    ],
    emptyForm: { school_class: '', title: '', body: '', is_published: false },
  },

  discipline_remarks: {
    service: disciplineRemarksService,
    queryKey: ['discipline-remarks'],
    createLabel: 'Add Remark',
    subtitle: 'Student discipline and welfare remarks',
    backLink: { to: '/school-admin/academics', label: 'Academics' },
    columns: [
      { key: 'student_name', label: 'Student', accessor: 'student_name' },
      { key: 'school_class_name', label: 'Class', accessor: 'school_class_name' },
      { key: 'remark_type', label: 'Type', accessor: 'remark_type' },
      { key: 'title', label: 'Title', accessor: 'title' },
      { key: 'incident_date', label: 'Date', accessor: 'incident_date' },
    ],
    formFields: [
      { name: 'student', label: 'Student', type: 'select', required: true, optionsFrom: 'students' },
      { name: 'school_class', label: 'Class', type: 'select', required: true, optionsFrom: 'classes' },
      { name: 'remark_type', label: 'Type', type: 'select', required: true, options: [
        { value: 'commendation', label: 'Commendation' },
        { value: 'warning', label: 'Warning' },
        { value: 'sanction', label: 'Sanction' },
      ] },
      { name: 'title', label: 'Title', required: true },
      { name: 'description', label: 'Description', type: 'textarea', required: true },
      { name: 'incident_date', label: 'Incident Date', type: 'date', required: true },
      { name: 'subject', label: 'Subject', type: 'select', optionsFrom: 'subjects' },
      { name: 'term', label: 'Term', type: 'select', optionsFrom: 'terms' },
    ],
    emptyForm: {
      student: '', school_class: '', remark_type: 'warning', title: '',
      description: '', incident_date: '', subject: '', term: '',
    },
  },

  report_cards: {
    service: reportCardsService,
    queryKey: ['report-cards'],
    createLabel: 'Generate Report Card',
    subtitle: 'Term report cards with averages and rankings',
    backLink: { to: '/school-admin/examinations', label: 'Examinations' },
    columns: [
      { key: 'student', label: 'Student', accessor: 'student' },
      { key: 'term', label: 'Term', accessor: 'term' },
      { key: 'school_class', label: 'Class', accessor: 'school_class' },
      { key: 'average_score', label: 'Average', accessor: 'average_score' },
      { key: 'rank', label: 'Rank', accessor: 'rank' },
      {
        key: 'is_published',
        label: 'Published',
        render: (row) => (row.is_published
          ? <span className="badge text-bg-success-subtle border text-success">Published</span>
          : '—'),
      },
    ],
    formFields: [
      { name: 'student', label: 'Student', type: 'select', required: true, optionsFrom: 'students' },
      { name: 'term', label: 'Term', type: 'select', required: true, optionsFrom: 'terms' },
      { name: 'school_class', label: 'Class', type: 'select', required: true, optionsFrom: 'classes' },
      { name: 'remarks', label: 'Remarks', type: 'textarea' },
      { name: 'teacher_remarks', label: 'Teacher Remarks', type: 'textarea' },
      { name: 'is_published', label: 'Published', type: 'checkbox', checkboxLabel: 'Publish to parents' },
    ],
    emptyForm: {
      student: '', term: '', school_class: '', remarks: '',
      teacher_remarks: '', is_published: false,
    },
  },

  // ── Attendance ──────────────────────────────────────────────────────────
  attendance_sessions: {
    service: attendanceService,
    queryKey: ['attendance-sessions'],
    createLabel: 'Record Session',
    subtitle: 'Attendance session records by date, type, and status',
    backLink: { to: '/school-admin/attendance', label: 'Attendance' },
    columns: [
      { key: 'date', label: 'Date', accessor: 'date', sortable: true },
      { key: 'attendee_type', label: 'Type', accessor: 'attendee_type' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'attendee_type', label: 'Type', type: 'select', required: true, options: [
        { value: 'student', label: 'Student' },
        { value: 'staff', label: 'Staff' },
      ] },
      { name: 'student', label: 'Student', type: 'select', optionsFrom: 'students' },
      { name: 'staff', label: 'Staff', type: 'select', optionsFrom: 'staff' },
      { name: 'date', label: 'Date', type: 'date', required: true },
      { name: 'status', label: 'Status', type: 'select', required: true, options: attendanceStatusOptions },
      { name: 'remarks', label: 'Remarks', type: 'textarea' },
    ],
    emptyForm: {
      attendee_type: 'student', student: '', staff: '',
      date: new Date().toISOString().slice(0, 10), status: 'present', remarks: '',
    },
  },

  staff_attendance: {
    service: attendanceService,
    queryKey: ['staff-attendance'],
    createLabel: 'Mark Staff Attendance',
    subtitle: 'Daily staff attendance records',
    backLink: { to: '/school-admin/attendance', label: 'Attendance' },
    columns: [
      { key: 'date', label: 'Date', accessor: 'date', sortable: true },
      { key: 'staff', label: 'Staff', accessor: 'staff' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'attendee_type', label: 'Type', type: 'hidden', defaultValue: 'staff' },
      { name: 'staff', label: 'Staff', type: 'select', required: true, optionsFrom: 'staff' },
      { name: 'date', label: 'Date', type: 'date', required: true },
      { name: 'status', label: 'Status', type: 'select', required: true, options: attendanceStatusOptions },
      { name: 'remarks', label: 'Remarks' },
    ],
    emptyForm: {
      attendee_type: 'staff', staff: '',
      date: new Date().toISOString().slice(0, 10), status: 'present', remarks: '',
    },
  },

  // ── Finance & payroll ───────────────────────────────────────────────────
  fee_categories: {
    service: feeCategoriesService,
    queryKey: ['fee-categories'],
    createLabel: 'Add Category',
    subtitle: 'Fee categories used in billing structures',
    backLink: { to: '/school-admin/finance', label: 'Finance' },
    columns: [
      { key: 'name', label: 'Name', accessor: 'name', sortable: true },
      { key: 'code', label: 'Code', accessor: 'code' },
      { key: 'is_active', label: 'Active', render: (row) => yesNo(row.is_active) },
    ],
    formFields: [
      { name: 'name', label: 'Category Name', required: true },
      { name: 'code', label: 'Code' },
      { name: 'description', label: 'Description', type: 'textarea' },
      { name: 'is_active', label: 'Active', type: 'checkbox', checkboxLabel: 'Category is active' },
    ],
    emptyForm: { name: '', code: '', description: '', is_active: true },
  },

  debtor_management: {
    service: studentFeeBalancesService,
    queryKey: ['student-fee-balances'],
    subtitle: 'Outstanding student fee balances by term',
    backLink: { to: '/school-admin/finance', label: 'Finance' },
    columns: [
      { key: 'student_name', label: 'Student', accessor: 'student_name', sortable: true },
      { key: 'admission_number', label: 'Admission', accessor: 'admission_number' },
      { key: 'class_name', label: 'Class', accessor: 'class_name' },
      { key: 'term_name', label: 'Term', accessor: 'term_name' },
      { key: 'balance', label: 'Balance (UGX)', accessor: 'balance' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [],
    emptyForm: {},
    readOnly: true,
  },

  discounts: {
    service: feeDiscountsService,
    queryKey: ['fee-discounts'],
    createLabel: 'Add Discount',
    subtitle: 'Fee discounts, waivers, and scholarships',
    backLink: { to: '/school-admin/finance', label: 'Finance' },
    columns: [
      { key: 'student_name', label: 'Student', accessor: 'student_name' },
      { key: 'discount_type', label: 'Type', accessor: 'discount_type' },
      { key: 'amount', label: 'Amount (UGX)', accessor: 'amount' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'student', label: 'Student', type: 'select', required: true, optionsFrom: 'students' },
      { name: 'discount_type', label: 'Type', type: 'select', required: true, options: [
        { value: 'waiver', label: 'Waiver' },
        { value: 'scholarship', label: 'Scholarship' },
        { value: 'sibling', label: 'Sibling' },
        { value: 'other', label: 'Other' },
      ] },
      { name: 'amount', label: 'Amount (UGX)', type: 'number' },
      { name: 'percent', label: 'Percent', type: 'number' },
      { name: 'reason', label: 'Reason', type: 'textarea', required: true },
    ],
    emptyForm: { student: '', discount_type: 'waiver', amount: '', percent: '', reason: '' },
  },

  refunds: {
    service: refundsService,
    queryKey: ['refunds'],
    createLabel: 'Request Refund',
    subtitle: 'Process and track fee refunds',
    backLink: { to: '/school-admin/finance', label: 'Finance' },
    columns: [
      { key: 'student_name', label: 'Student', accessor: 'student_name' },
      { key: 'amount', label: 'Amount (UGX)', accessor: 'amount' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'fee_payment', label: 'Payment', type: 'select', required: true, optionsFrom: 'feePayments' },
      { name: 'amount', label: 'Amount (UGX)', type: 'number', required: true },
      { name: 'reason', label: 'Reason', type: 'textarea', required: true },
    ],
    emptyForm: { fee_payment: '', amount: '', reason: '' },
  },

  misc_income: {
    service: miscIncomeService,
    queryKey: ['misc-income'],
    createLabel: 'Record Income',
    subtitle: 'Non-fee school income',
    backLink: { to: '/school-admin/finance', label: 'Finance' },
    columns: [
      { key: 'description', label: 'Description', accessor: 'description', sortable: true },
      { key: 'amount', label: 'Amount (UGX)', accessor: 'amount' },
      { key: 'income_date', label: 'Date', accessor: 'income_date' },
      { key: 'account_name', label: 'Account', accessor: 'account_name' },
    ],
    formFields: [
      { name: 'description', label: 'Description', required: true },
      { name: 'amount', label: 'Amount (UGX)', type: 'number', required: true },
      { name: 'income_date', label: 'Date', type: 'date', required: true },
      { name: 'account', label: 'Account', type: 'select', optionsFrom: 'financialAccounts' },
      { name: 'reference', label: 'Reference' },
      { name: 'notes', label: 'Notes', type: 'textarea' },
    ],
    emptyForm: {
      description: '', amount: '',
      income_date: new Date().toISOString().slice(0, 10),
      account: '', reference: '', notes: '',
    },
  },

  finance_notes: {
    service: financeNotesService,
    queryKey: ['finance-notes'],
    createLabel: 'Add Note',
    subtitle: 'Notes on student accounts and transactions',
    backLink: { to: '/school-admin/finance', label: 'Finance' },
    columns: [
      { key: 'author_name', label: 'Author', accessor: 'author_name' },
      { key: 'content', label: 'Note', accessor: 'content' },
      { key: 'created_at', label: 'Created', accessor: 'created_at' },
    ],
    formFields: [
      { name: 'student', label: 'Student', type: 'select', optionsFrom: 'students' },
      { name: 'content', label: 'Note', type: 'textarea', required: true },
    ],
    emptyForm: { student: '', content: '' },
  },

  budget_management: {
    service: budgetsService,
    queryKey: ['budgets'],
    createLabel: 'Add Budget',
    subtitle: 'School budget planning and tracking',
    backLink: { to: '/school-admin/finance', label: 'Finance' },
    columns: [
      { key: 'name', label: 'Budget', accessor: 'name', sortable: true },
      { key: 'academic_year_name', label: 'Year', accessor: 'academic_year_name' },
      { key: 'allocated_amount', label: 'Allocated (UGX)', accessor: 'allocated_amount' },
      { key: 'spent_amount', label: 'Spent (UGX)', accessor: 'spent_amount' },
    ],
    formFields: [
      { name: 'name', label: 'Budget Name', required: true },
      { name: 'academic_year', label: 'Academic Year', type: 'select', required: true, optionsFrom: 'academic_years' },
      { name: 'term', label: 'Term', type: 'select', optionsFrom: 'terms' },
      { name: 'allocated_amount', label: 'Allocated (UGX)', type: 'number', required: true },
      { name: 'account', label: 'Account', type: 'select', optionsFrom: 'financialAccounts' },
      { name: 'notes', label: 'Notes', type: 'textarea' },
    ],
    emptyForm: { name: '', academic_year: '', term: '', allocated_amount: '', account: '', notes: '' },
  },

  financial_accounts: {
    service: financialAccountsService,
    queryKey: ['financial-accounts'],
    createLabel: 'Add Account',
    subtitle: 'Chart of accounts and balances',
    backLink: { to: '/school-admin/finance', label: 'Finance' },
    columns: [
      { key: 'name', label: 'Account', accessor: 'name', sortable: true },
      { key: 'code', label: 'Code', accessor: 'code' },
      { key: 'account_type', label: 'Type', accessor: 'account_type' },
      { key: 'balance', label: 'Balance (UGX)', accessor: 'balance' },
      { key: 'is_active', label: 'Active', render: (row) => yesNo(row.is_active) },
    ],
    formFields: [
      { name: 'name', label: 'Account Name', required: true },
      { name: 'code', label: 'Code' },
      { name: 'account_type', label: 'Type', type: 'select', required: true, options: [
        { value: 'asset', label: 'Asset' },
        { value: 'liability', label: 'Liability' },
        { value: 'income', label: 'Income' },
        { value: 'expense', label: 'Expense' },
      ] },
      { name: 'balance', label: 'Opening Balance (UGX)', type: 'number' },
      { name: 'is_active', label: 'Active', type: 'checkbox', checkboxLabel: 'Account is active' },
    ],
    emptyForm: { name: '', code: '', account_type: 'income', balance: 0, is_active: true },
  },

  accounting_periods: {
    service: accountingPeriodsService,
    queryKey: ['accounting-periods'],
    createLabel: 'Add Period',
    subtitle: 'Open and close financial reporting periods',
    backLink: { to: '/school-admin/finance', label: 'Finance' },
    columns: [
      { key: 'name', label: 'Period', accessor: 'name', sortable: true },
      { key: 'start_date', label: 'Start', accessor: 'start_date' },
      { key: 'end_date', label: 'End', accessor: 'end_date' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'name', label: 'Period Name', required: true },
      { name: 'start_date', label: 'Start Date', type: 'date', required: true },
      { name: 'end_date', label: 'End Date', type: 'date', required: true },
    ],
    emptyForm: { name: '', start_date: '', end_date: '' },
  },

  invoice_generation: {
    service: invoicesService,
    queryKey: ['invoices'],
    createLabel: 'Create Invoice',
    subtitle: 'Generate student fee invoices',
    backLink: { to: '/school-admin/finance', label: 'Finance' },
    columns: [
      { key: 'invoice_number', label: 'Invoice #', accessor: 'invoice_number', sortable: true },
      { key: 'student', label: 'Student', accessor: 'student' },
      { key: 'issue_date', label: 'Issued', accessor: 'issue_date' },
      { key: 'total_amount', label: 'Total (UGX)', accessor: 'total_amount' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'student', label: 'Student', type: 'select', required: true, optionsFrom: 'students' },
      { name: 'invoice_number', label: 'Invoice Number', required: true },
      { name: 'issue_date', label: 'Issue Date', type: 'date', required: true },
      { name: 'due_date', label: 'Due Date', type: 'date', required: true },
      { name: 'total_amount', label: 'Total Amount (UGX)', type: 'number', required: true },
      { name: 'notes', label: 'Notes', type: 'textarea' },
    ],
    emptyForm: {
      student: '', invoice_number: '', issue_date: new Date().toISOString().slice(0, 10),
      due_date: '', total_amount: '', notes: '',
    },
  },

  payroll_runs: {
    service: payrollRunsService,
    queryKey: ['payroll-runs'],
    createLabel: 'New Payroll Run',
    subtitle: 'Monthly payroll processing by pay period',
    backLink: { to: '/school-admin/payroll', label: 'Payroll' },
    columns: [
      { key: 'title', label: 'Title', accessor: 'title', sortable: true },
      { key: 'period_start', label: 'Period Start', accessor: 'period_start' },
      { key: 'period_end', label: 'Period End', accessor: 'period_end' },
      { key: 'status', label: 'Status', accessor: 'status' },
      { key: 'total_amount', label: 'Total (UGX)', accessor: 'total_amount' },
    ],
    formFields: [
      { name: 'title', label: 'Run Title', required: true, placeholder: 'July 2026 Payroll' },
      { name: 'period_start', label: 'Period Start', type: 'date', required: true },
      { name: 'period_end', label: 'Period End', type: 'date', required: true },
    ],
    emptyForm: { title: '', period_start: '', period_end: '' },
  },

  payslips: {
    service: payslipsService,
    queryKey: ['payslips'],
    createLabel: 'Add Payslip',
    subtitle: 'Staff payslips linked to payroll runs',
    backLink: { to: '/school-admin/payroll', label: 'Payroll' },
    columns: [
      { key: 'staff', label: 'Staff', accessor: 'staff' },
      { key: 'payroll_run', label: 'Payroll Run', accessor: 'payroll_run' },
      { key: 'net_salary', label: 'Net (UGX)', accessor: 'net_salary' },
      { key: 'is_paid', label: 'Paid', render: (row) => yesNo(row.is_paid) },
    ],
    formFields: [
      { name: 'payroll_run', label: 'Payroll Run', type: 'select', required: true, optionsFrom: 'payrollRuns' },
      { name: 'staff', label: 'Staff', type: 'select', required: true, optionsFrom: 'staff' },
      { name: 'basic_salary', label: 'Basic Salary (UGX)', type: 'number', required: true },
      { name: 'net_salary', label: 'Net Salary (UGX)', type: 'number', required: true },
    ],
    emptyForm: { payroll_run: '', staff: '', basic_salary: '', net_salary: '' },
  },

  // ── Library ─────────────────────────────────────────────────────────────
  book_categories: {
    service: booksService,
    queryKey: ['library-books-categories'],
    createLabel: 'Add Book',
    subtitle: 'Organise the catalogue by category',
    backLink: { to: '/school-admin/library', label: 'Library' },
    columns: [
      { key: 'category', label: 'Category', accessor: 'category', sortable: true },
      { key: 'title', label: 'Title', accessor: 'title' },
      { key: 'author', label: 'Author', accessor: 'author' },
      { key: 'total_copies', label: 'Copies', accessor: 'total_copies' },
    ],
    formFields: [
      { name: 'title', label: 'Title', required: true },
      { name: 'author', label: 'Author', required: true },
      { name: 'category', label: 'Category', required: true, placeholder: 'e.g. Science Fiction' },
      { name: 'isbn', label: 'ISBN' },
      { name: 'total_copies', label: 'Total Copies', type: 'number' },
    ],
    emptyForm: { title: '', author: '', category: '', isbn: '', total_copies: 1 },
    mapCreate: (data) => ({ ...data, available_copies: data.total_copies || 1 }),
  },

  borrowing: {
    service: borrowsService,
    queryKey: ['library-borrows'],
    createLabel: 'Issue Book',
    subtitle: 'Issue books to students and track due dates',
    backLink: { to: '/school-admin/library', label: 'Library' },
    columns: [
      { key: 'book', label: 'Book', accessor: 'book' },
      { key: 'student', label: 'Student', accessor: 'student' },
      { key: 'borrowed_date', label: 'Borrowed', accessor: 'borrowed_date' },
      { key: 'due_date', label: 'Due', accessor: 'due_date' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'book', label: 'Book', type: 'select', required: true, optionsFrom: 'books' },
      { name: 'student', label: 'Student', type: 'select', required: true, optionsFrom: 'students' },
      { name: 'borrowed_date', label: 'Borrowed Date', type: 'date', required: true },
      { name: 'due_date', label: 'Due Date', type: 'date', required: true },
      { name: 'notes', label: 'Notes', type: 'textarea' },
    ],
    emptyForm: {
      book: '', student: '',
      borrowed_date: new Date().toISOString().slice(0, 10), due_date: '', notes: '',
    },
  },

  returns: {
    service: borrowsService,
    queryKey: ['library-returns'],
    createLabel: 'Mark Returned',
    subtitle: 'Mark borrowed books as returned and update loan status',
    backLink: { to: '/school-admin/library', label: 'Library' },
    columns: [
      { key: 'book', label: 'Book', accessor: 'book' },
      { key: 'student', label: 'Student', accessor: 'student' },
      { key: 'due_date', label: 'Due', accessor: 'due_date' },
      { key: 'returned_date', label: 'Returned', accessor: 'returned_date' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'book', label: 'Book', type: 'select', required: true, optionsFrom: 'books' },
      { name: 'student', label: 'Student', type: 'select', required: true, optionsFrom: 'students' },
      { name: 'returned_date', label: 'Returned Date', type: 'date', required: true },
      { name: 'status', label: 'Status', type: 'select', required: true, options: [
        { value: 'returned', label: 'Returned' },
        { value: 'lost', label: 'Lost' },
      ] },
      { name: 'notes', label: 'Notes', type: 'textarea' },
    ],
    emptyForm: {
      book: '', student: '',
      returned_date: new Date().toISOString().slice(0, 10), status: 'returned', notes: '',
    },
  },

  library_fines: {
    service: borrowsService,
    queryKey: ['library-fines'],
    createLabel: 'Record Fine',
    subtitle: 'Outstanding fines on overdue or lost books',
    backLink: { to: '/school-admin/library', label: 'Library' },
    columns: [
      { key: 'student', label: 'Student', accessor: 'student' },
      { key: 'book', label: 'Book', accessor: 'book' },
      { key: 'due_date', label: 'Due', accessor: 'due_date' },
      { key: 'fine_amount', label: 'Fine (UGX)', accessor: 'fine_amount' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'book', label: 'Book', type: 'select', required: true, optionsFrom: 'books' },
      { name: 'student', label: 'Student', type: 'select', required: true, optionsFrom: 'students' },
      { name: 'fine_amount', label: 'Fine Amount (UGX)', type: 'number', required: true },
      { name: 'status', label: 'Status', type: 'select', options: [
        { value: 'overdue', label: 'Overdue' },
        { value: 'lost', label: 'Lost' },
        { value: 'returned', label: 'Returned' },
      ] },
      { name: 'notes', label: 'Notes', type: 'textarea' },
    ],
    emptyForm: { book: '', student: '', fine_amount: '', status: 'overdue', notes: '' },
  },

  // ── Hostel ──────────────────────────────────────────────────────────────
  rooms: {
    service: roomsService,
    queryKey: ['hostel-rooms'],
    createLabel: 'Add Room',
    subtitle: 'Hostel rooms, capacity, and availability',
    backLink: { to: '/school-admin/hostel', label: 'Hostels' },
    columns: [
      { key: 'hostel', label: 'Hostel', accessor: 'hostel' },
      { key: 'room_number', label: 'Room', accessor: 'room_number', sortable: true },
      { key: 'capacity', label: 'Capacity', accessor: 'capacity' },
      { key: 'occupied', label: 'Occupied', accessor: 'occupied' },
      { key: 'is_available', label: 'Available', render: (row) => yesNo(row.is_available) },
    ],
    formFields: [
      { name: 'hostel', label: 'Hostel', type: 'select', required: true, optionsFrom: 'hostels' },
      { name: 'room_number', label: 'Room Number', required: true },
      { name: 'floor', label: 'Floor', type: 'number' },
      { name: 'capacity', label: 'Capacity', type: 'number', required: true },
      { name: 'room_type', label: 'Type', type: 'select', options: [
        { value: 'single', label: 'Single' },
        { value: 'double', label: 'Double' },
        { value: 'dormitory', label: 'Dormitory' },
      ] },
      { name: 'is_available', label: 'Available', type: 'checkbox', checkboxLabel: 'Room is available' },
    ],
    emptyForm: {
      hostel: '', room_number: '', floor: 1, capacity: 4,
      room_type: 'dormitory', is_available: true,
    },
  },

  room_allocation: {
    service: allocationsService,
    queryKey: ['hostel-allocations'],
    createLabel: 'Allocate Room',
    subtitle: 'Assign students to hostel rooms',
    backLink: { to: '/school-admin/hostel', label: 'Hostels' },
    columns: [
      { key: 'student', label: 'Student', accessor: 'student' },
      { key: 'room', label: 'Room', accessor: 'room' },
      { key: 'start_date', label: 'From', accessor: 'start_date' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'student', label: 'Student', type: 'select', required: true, optionsFrom: 'students' },
      { name: 'room', label: 'Room', type: 'select', required: true, optionsFrom: 'rooms' },
      { name: 'start_date', label: 'Start Date', type: 'date', required: true },
      { name: 'end_date', label: 'End Date', type: 'date' },
      { name: 'bed_number', label: 'Bed Number' },
      { name: 'status', label: 'Status', type: 'select', options: [
        { value: 'active', label: 'Active' },
        { value: 'vacated', label: 'Vacated' },
      ] },
    ],
    emptyForm: {
      student: '', room: '',
      start_date: new Date().toISOString().slice(0, 10),
      end_date: '', bed_number: '', status: 'active',
    },
  },

  // ── Transport ───────────────────────────────────────────────────────────
  routes: {
    service: routesService,
    queryKey: ['transport-routes'],
    createLabel: 'Add Route',
    subtitle: 'Bus routes, stops, and schedules',
    backLink: { to: '/school-admin/transport', label: 'Transport' },
    columns: [
      { key: 'name', label: 'Route', accessor: 'name', sortable: true },
      { key: 'start_point', label: 'Start', accessor: 'start_point' },
      { key: 'end_point', label: 'End', accessor: 'end_point' },
      { key: 'departure_time', label: 'Departs', accessor: 'departure_time' },
      { key: 'fee', label: 'Fee (UGX)', accessor: 'fee' },
    ],
    formFields: [
      { name: 'name', label: 'Route Name', required: true },
      { name: 'start_point', label: 'Start Point', required: true },
      { name: 'end_point', label: 'End Point', required: true },
      { name: 'departure_time', label: 'Departure Time', type: 'time', required: true },
      { name: 'arrival_time', label: 'Arrival Time', type: 'time', required: true },
      { name: 'fee', label: 'Monthly Fee (UGX)', type: 'number' },
    ],
    emptyForm: {
      name: '', start_point: '', end_point: '',
      departure_time: '', arrival_time: '', fee: 0,
    },
  },

  student_transport_assignment: {
    service: studentTransportService,
    queryKey: ['student-transport'],
    createLabel: 'Assign Student',
    subtitle: 'Assign students to transport routes and pickup points',
    backLink: { to: '/school-admin/transport', label: 'Transport' },
    columns: [
      { key: 'student', label: 'Student', accessor: 'student' },
      { key: 'route', label: 'Route', accessor: 'route' },
      { key: 'pickup_point', label: 'Pickup', accessor: 'pickup_point' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'student', label: 'Student', type: 'select', required: true, optionsFrom: 'students' },
      { name: 'route', label: 'Route', type: 'select', required: true, optionsFrom: 'routes' },
      { name: 'pickup_point', label: 'Pickup Point', required: true },
      { name: 'dropoff_point', label: 'Drop-off Point', required: true },
      { name: 'start_date', label: 'Start Date', type: 'date', required: true },
      { name: 'status', label: 'Status', type: 'select', options: [
        { value: 'active', label: 'Active' },
        { value: 'inactive', label: 'Inactive' },
      ] },
    ],
    emptyForm: {
      student: '', route: '', pickup_point: '', dropoff_point: '',
      start_date: new Date().toISOString().slice(0, 10), status: 'active',
    },
  },

  // ── Inventory ───────────────────────────────────────────────────────────
  stock_movement: {
    service: stockMovementsService,
    queryKey: ['stock-movements'],
    createLabel: 'Record Movement',
    subtitle: 'Stock in, out, and adjustment entries',
    backLink: { to: '/school-admin/inventory', label: 'Inventory' },
    columns: [
      { key: 'item', label: 'Item', accessor: 'item' },
      { key: 'movement_type', label: 'Type', accessor: 'movement_type' },
      { key: 'quantity', label: 'Qty', accessor: 'quantity' },
      { key: 'reference', label: 'Reference', accessor: 'reference' },
    ],
    formFields: [
      { name: 'item', label: 'Item', type: 'select', required: true, optionsFrom: 'items' },
      { name: 'movement_type', label: 'Movement Type', type: 'select', required: true, options: [
        { value: 'in', label: 'Stock In' },
        { value: 'out', label: 'Stock Out' },
        { value: 'adjustment', label: 'Adjustment' },
      ] },
      { name: 'quantity', label: 'Quantity', type: 'number', required: true },
      { name: 'reference', label: 'Reference' },
      { name: 'notes', label: 'Notes', type: 'textarea' },
    ],
    emptyForm: { item: '', movement_type: 'in', quantity: '', reference: '', notes: '' },
  },

  purchase_orders: {
    service: procurementsService,
    queryKey: ['purchase-orders'],
    createLabel: 'Create Order',
    subtitle: 'Purchase orders and procurement requests',
    backLink: { to: '/school-admin/inventory', label: 'Inventory' },
    columns: [
      { key: 'title', label: 'Order', accessor: 'title', sortable: true },
      { key: 'supplier', label: 'Supplier', accessor: 'supplier' },
      { key: 'order_date', label: 'Ordered', accessor: 'order_date' },
      { key: 'total_cost', label: 'Total (UGX)', accessor: 'total_cost' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'title', label: 'Order Title', required: true },
      { name: 'supplier', label: 'Supplier', required: true },
      { name: 'order_date', label: 'Order Date', type: 'date', required: true },
      { name: 'expected_delivery', label: 'Expected Delivery', type: 'date' },
      { name: 'total_cost', label: 'Total Cost (UGX)', type: 'number', required: true },
      { name: 'status', label: 'Status', type: 'select', options: [
        { value: 'draft', label: 'Draft' },
        { value: 'ordered', label: 'Ordered' },
        { value: 'received', label: 'Received' },
        { value: 'cancelled', label: 'Cancelled' },
      ] },
    ],
    emptyForm: {
      title: '', supplier: '',
      order_date: new Date().toISOString().slice(0, 10),
      expected_delivery: '', total_cost: '', status: 'draft',
    },
  },

  suppliers: {
    service: procurementsService,
    queryKey: ['suppliers'],
    createLabel: 'Add Supplier Record',
    subtitle: 'Suppliers referenced on purchase orders',
    backLink: { to: '/school-admin/inventory', label: 'Inventory' },
    columns: [
      { key: 'supplier', label: 'Supplier', accessor: 'supplier', sortable: true },
      { key: 'title', label: 'Order', accessor: 'title' },
      { key: 'order_date', label: 'Last Order', accessor: 'order_date' },
      { key: 'total_cost', label: 'Amount (UGX)', accessor: 'total_cost' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'title', label: 'Reference Order', required: true },
      { name: 'supplier', label: 'Supplier Name', required: true },
      { name: 'order_date', label: 'Order Date', type: 'date', required: true },
      { name: 'total_cost', label: 'Order Value (UGX)', type: 'number', required: true },
    ],
    emptyForm: {
      title: '', supplier: '',
      order_date: new Date().toISOString().slice(0, 10), total_cost: '',
    },
  },

  // ── HR ──────────────────────────────────────────────────────────────────
  leave_requests: {
    service: leavesService,
    queryKey: ['leave-requests'],
    createLabel: 'Request Leave',
    subtitle: 'Staff leave requests and approvals',
    backLink: { to: '/school-admin/hr', label: 'HR' },
    columns: [
      { key: 'staff', label: 'Staff', accessor: 'staff' },
      { key: 'leave_type', label: 'Type', accessor: 'leave_type' },
      { key: 'start_date', label: 'From', accessor: 'start_date' },
      { key: 'end_date', label: 'To', accessor: 'end_date' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'staff', label: 'Staff', type: 'select', required: true, optionsFrom: 'staff' },
      { name: 'leave_type', label: 'Leave Type', type: 'select', required: true, options: [
        { value: 'annual', label: 'Annual' },
        { value: 'sick', label: 'Sick' },
        { value: 'maternity', label: 'Maternity' },
        { value: 'paternity', label: 'Paternity' },
        { value: 'unpaid', label: 'Unpaid' },
        { value: 'other', label: 'Other' },
      ] },
      { name: 'start_date', label: 'Start Date', type: 'date', required: true },
      { name: 'end_date', label: 'End Date', type: 'date', required: true },
      { name: 'days', label: 'Days', type: 'number', required: true },
      { name: 'reason', label: 'Reason', type: 'textarea', required: true },
    ],
    emptyForm: {
      staff: '', leave_type: 'annual', start_date: '', end_date: '', days: '', reason: '',
    },
  },

  performance_reviews: {
    service: performanceReviewsService,
    queryKey: ['performance-reviews'],
    createLabel: 'New Review',
    subtitle: 'Staff performance reviews and ratings',
    backLink: { to: '/school-admin/hr', label: 'HR' },
    columns: [
      { key: 'staff', label: 'Staff', accessor: 'staff' },
      { key: 'review_period_start', label: 'From', accessor: 'review_period_start' },
      { key: 'review_period_end', label: 'To', accessor: 'review_period_end' },
      { key: 'overall_rating', label: 'Rating', accessor: 'overall_rating' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'staff', label: 'Staff', type: 'select', required: true, optionsFrom: 'staff' },
      { name: 'review_period_start', label: 'Period Start', type: 'date', required: true },
      { name: 'review_period_end', label: 'Period End', type: 'date', required: true },
      { name: 'overall_rating', label: 'Overall Rating', type: 'number', required: true },
      { name: 'strengths', label: 'Strengths', type: 'textarea' },
      { name: 'areas_for_improvement', label: 'Areas for Improvement', type: 'textarea' },
      { name: 'goals', label: 'Goals', type: 'textarea' },
      { name: 'status', label: 'Status', type: 'select', options: [
        { value: 'draft', label: 'Draft' },
        { value: 'submitted', label: 'Submitted' },
        { value: 'acknowledged', label: 'Acknowledged' },
      ] },
    ],
    emptyForm: {
      staff: '', review_period_start: '', review_period_end: '',
      overall_rating: '', strengths: '', areas_for_improvement: '', goals: '', status: 'draft',
    },
  },

  // ── Communication ───────────────────────────────────────────────────────
  sms_communication: {
    service: smsService,
    queryKey: ['sms-messages'],
    createLabel: 'Send SMS',
    subtitle: 'SMS messages to parents and staff',
    deletable: true,
    allowBulkDelete: true,
    bulkDeleteLabel: 'Delete All SMS',
    backLink: { to: '/school-admin/communication', label: 'Communication' },
    columns: [
      { key: 'recipient_phone', label: 'Phone', accessor: 'recipient_phone' },
      { key: 'message', label: 'Message', accessor: 'message' },
      { key: 'status', label: 'Status', accessor: 'status' },
      { key: 'sent_at', label: 'Sent', accessor: 'sent_at' },
    ],
    formFields: [
      { name: 'recipient_phone', label: 'Recipient Phone', required: true },
      { name: 'message', label: 'Message', type: 'textarea', required: true },
    ],
    emptyForm: { recipient_phone: '', message: '' },
  },

  email_templates: {
    service: emailsService,
    queryKey: ['email-messages'],
    createLabel: 'Compose Email',
    subtitle: 'Email templates and outbound messages',
    deletable: true,
    allowBulkDelete: true,
    bulkDeleteLabel: 'Delete All Emails',
    backLink: { to: '/school-admin/communication', label: 'Communication' },
    columns: [
      { key: 'recipient_email', label: 'Recipient', accessor: 'recipient_email' },
      { key: 'subject', label: 'Subject', accessor: 'subject', sortable: true },
      { key: 'status', label: 'Status', accessor: 'status' },
      { key: 'sent_at', label: 'Sent', accessor: 'sent_at' },
    ],
    formFields: [
      { name: 'recipient_email', label: 'Recipient Email', type: 'email', required: true },
      { name: 'subject', label: 'Subject', required: true },
      { name: 'body', label: 'Body', type: 'textarea', required: true },
    ],
    emptyForm: { recipient_email: '', subject: '', body: '' },
  },

  broadcast_messaging: {
    service: broadcastsService,
    queryKey: ['broadcasts'],
    createLabel: 'New Broadcast',
    subtitle: 'Multi-channel broadcast messages via email, SMS, or WhatsApp',
    deletable: true,
    allowBulkDelete: true,
    bulkDeleteLabel: 'Delete All Broadcasts',
    backLink: { to: '/school-admin/communication', label: 'Communication' },
    columns: [
      { key: 'title', label: 'Title', accessor: 'title', sortable: true },
      { key: 'status', label: 'Status', accessor: 'status' },
      { key: 'recipient_count', label: 'Recipients', accessor: 'recipient_count' },
      { key: 'sent_at', label: 'Sent', accessor: 'sent_at' },
    ],
    formFields: [
      { name: 'title', label: 'Title', required: true },
      { name: 'message', label: 'Message', type: 'textarea', required: true },
      { name: 'channels', label: 'Delivery Channels', type: 'multiselect', options: [
        { value: 'email', label: 'Email' },
        { value: 'sms', label: 'SMS' },
        { value: 'whatsapp', label: 'WhatsApp' },
      ] },
    ],
    emptyForm: { title: '', message: '', channels: ['email'], status: 'draft' },
    rowActions: [
      {
        key: 'send',
        label: 'Send Now',
        variant: 'primary',
        show: (row) => row.status === 'draft' || row.status === 'scheduled',
        action: 'send',
        confirmText: (row) => {
          const channels = Array.isArray(row.channels) && row.channels.length
            ? row.channels
            : ['email'];
          return `Send "${row.title}" via ${channels.join(', ')}?`;
        },
        confirmTextButton: 'Yes, send now',
      },
    ],
  },

  notifications: {
    service: notificationsService,
    queryKey: ['school-notifications'],
    createLabel: 'Send Notification',
    subtitle: 'In-app notifications — primarily read and managed from the feed',
    deletable: true,
    allowBulkDelete: true,
    bulkDeleteLabel: 'Delete All Notifications',
    columns: [
      { key: 'title', label: 'Title', accessor: 'title', sortable: true },
      { key: 'message', label: 'Message', accessor: 'message' },
      {
        key: 'is_read',
        label: 'Read',
        render: (row) => (row.is_read
          ? <span className="badge text-bg-success-subtle border text-success">Read</span>
          : <span className="badge text-bg-warning-subtle border text-warning">Unread</span>),
      },
    ],
    formFields: [
      { name: 'title', label: 'Title', required: true },
      { name: 'message', label: 'Message', type: 'textarea', required: true },
    ],
    emptyForm: { title: '', message: '' },
  },

  // ── Support ─────────────────────────────────────────────────────────────
  support_tickets: {
    service: supportTicketsService,
    queryKey: ['support-tickets'],
    createLabel: 'Open Ticket',
    subtitle: 'Support tickets and help requests',
    backLink: { to: '/school-admin/support', label: 'Support' },
    columns: [
      { key: 'ticket_number', label: 'Ticket #', accessor: 'ticket_number', sortable: true },
      { key: 'subject', label: 'Subject', accessor: 'subject' },
      { key: 'category', label: 'Category', accessor: 'category' },
      { key: 'priority', label: 'Priority', accessor: 'priority' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'subject', label: 'Subject', required: true },
      { name: 'description', label: 'Description', type: 'textarea', required: true },
      { name: 'category', label: 'Category', type: 'select', options: [
        { value: 'technical', label: 'Technical' },
        { value: 'billing', label: 'Billing' },
        { value: 'academic', label: 'Academic' },
        { value: 'general', label: 'General' },
      ] },
      { name: 'priority', label: 'Priority', type: 'select', options: [
        { value: 'low', label: 'Low' },
        { value: 'medium', label: 'Medium' },
        { value: 'high', label: 'High' },
      ] },
    ],
    emptyForm: { subject: '', description: '', category: 'general', priority: 'medium' },
  },

  ticket_replies: {
    service: ticketRepliesService,
    queryKey: ['ticket-replies'],
    createLabel: 'Add Reply',
    subtitle: 'Replies and updates on support tickets',
    backLink: { to: '/school-admin/support', label: 'Support' },
    columns: [
      { key: 'ticket', label: 'Ticket', accessor: 'ticket' },
      { key: 'message', label: 'Message', accessor: 'message' },
      { key: 'is_internal', label: 'Internal', render: (row) => yesNo(row.is_internal) },
    ],
    formFields: [
      { name: 'ticket', label: 'Ticket', type: 'select', required: true, optionsFrom: 'tickets' },
      { name: 'message', label: 'Reply', type: 'textarea', required: true },
      { name: 'is_internal', label: 'Internal Note', type: 'checkbox', checkboxLabel: 'Internal note (not visible to submitter)' },
    ],
    emptyForm: { ticket: '', message: '', is_internal: false },
  },

  // ── Events ──────────────────────────────────────────────────────────────
  event_management: {
    service: eventsService,
    queryKey: ['events'],
    createLabel: 'Create Event',
    subtitle: 'School events, venues, and schedules',
    backLink: { to: '/school-admin/events', label: 'Events' },
    columns: [
      { key: 'title', label: 'Event', accessor: 'title', sortable: true },
      { key: 'start_date', label: 'Starts', accessor: 'start_date' },
      { key: 'location', label: 'Location', accessor: 'location' },
      { key: 'status', label: 'Status', accessor: 'status' },
      {
        key: 'is_registration_open',
        label: 'Registration',
        render: (row) => yesNo(row.is_registration_open),
      },
    ],
    formFields: [
      { name: 'title', label: 'Event Title', required: true },
      { name: 'description', label: 'Description', type: 'textarea' },
      { name: 'location', label: 'Location' },
      { name: 'start_date', label: 'Start', type: 'datetime-local', required: true },
      { name: 'end_date', label: 'End', type: 'datetime-local', required: true },
      { name: 'target_audience', label: 'Audience', type: 'select', options: [
        { value: 'all', label: 'Everyone' },
        { value: 'students', label: 'Students' },
        { value: 'parents', label: 'Parents' },
        { value: 'staff', label: 'Staff' },
      ] },
      { name: 'is_registration_open', label: 'Registration Open', type: 'checkbox', checkboxLabel: 'Allow registrations' },
    ],
    emptyForm: {
      title: '', description: '', location: '', start_date: '', end_date: '',
      target_audience: 'all', is_registration_open: true,
    },
  },

  event_registration: {
    service: eventRegistrationsService,
    queryKey: ['event-registrations'],
    createLabel: 'Register Attendee',
    subtitle: 'Event registrations for students and guests',
    backLink: { to: '/school-admin/events', label: 'Events' },
    columns: [
      { key: 'event', label: 'Event', accessor: 'event' },
      { key: 'registrant_name', label: 'Name', accessor: 'registrant_name', sortable: true },
      { key: 'student', label: 'Student', accessor: 'student' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'event', label: 'Event', type: 'select', required: true, optionsFrom: 'events' },
      { name: 'student', label: 'Student', type: 'select', optionsFrom: 'students' },
      { name: 'registrant_name', label: 'Registrant Name', required: true },
      { name: 'registrant_email', label: 'Email' },
      { name: 'registrant_phone', label: 'Phone' },
      { name: 'status', label: 'Status', type: 'select', options: [
        { value: 'registered', label: 'Registered' },
        { value: 'attended', label: 'Attended' },
        { value: 'cancelled', label: 'Cancelled' },
      ] },
    ],
    emptyForm: {
      event: '', student: '', registrant_name: '',
      registrant_email: '', registrant_phone: '', status: 'registered',
    },
  },
};

export default ENTITY_REGISTRY_EXTRAS;