/**
 * Maps feature keys to real API-backed list/workspace configs.
 * Used by SubModulePage and EntityListPage — replaces stub fetch/create.
 */
import {
  academicYearsService,
  termsService,
  classesService,
  streamsService,
  subjectsService,
  departmentsService,
  homeworkService,
  assignmentsService,
  timetablesService,
  feeStructuresService,
  accountingService,
  admissionApplicationsService,
  admittedStudentsService,
  admissionVacanciesService,
  medicalRecordsService,
  attendanceService,
  examsService,
  booksService,
  routesService,
  vehiclesService,
  inventoryItemsService,
  leavesService,
  payrollRunsService,
  salaryStructuresService,
  announcementsService,
} from '../services/moduleService';
import { ENTITY_REGISTRY_EXTRAS } from './entityRegistryExtras';

const yesNo = (v) => (v ? 'Yes' : '—');

export const ENTITY_REGISTRY = {
  academic_years: {
    service: academicYearsService,
    queryKey: ['academic-years'],
    singleton: { type: 'academic_year', title: 'Current academic year' },
    createLabel: 'Add Academic Year',
    subtitle: 'Define school years — required before terms and classes',
    backLink: { to: '/school-admin/academics', label: 'Academics' },
    columns: [
      { key: 'name', label: 'Year', accessor: 'name', sortable: true },
      { key: 'start_date', label: 'Starts', accessor: 'start_date' },
      { key: 'end_date', label: 'Ends', accessor: 'end_date' },
      {
        key: 'is_current',
        label: 'Current',
        render: (row) => (row.is_current
          ? <span className="badge text-bg-primary-subtle border text-primary">Current</span>
          : '—'),
      },
    ],
    formFields: [
      { name: 'name', label: 'Year Name', required: true, placeholder: 'e.g. 2026' },
      { name: 'start_date', label: 'Start Date', type: 'date', required: true },
      { name: 'end_date', label: 'End Date', type: 'date', required: true },
      { name: 'is_current', label: 'Current Year', type: 'checkbox', checkboxLabel: 'Mark as current academic year' },
    ],
    emptyForm: { name: '', start_date: '', end_date: '', is_current: false },
  },

  subjects: {
    service: subjectsService,
    queryKey: ['subjects'],
    createLabel: 'Add Subject',
    subtitle: 'Curriculum subjects and codes',
    backLink: { to: '/school-admin/academics', label: 'Academics' },
    columns: [
      { key: 'name', label: 'Subject', accessor: 'name', sortable: true },
      { key: 'code', label: 'Code', accessor: 'code' },
      { key: 'paper_codes_display', label: 'Papers', accessor: 'paper_codes_display' },
      { key: 'is_compulsory', label: 'Compulsory', render: (row) => yesNo(row.is_compulsory) },
    ],
    formFields: [
      { name: 'name', label: 'Subject Name', required: true },
      { name: 'code', label: 'Code', required: true },
      {
        name: 'paper_codes',
        label: 'Papers (optional)',
        placeholder: 'e.g. M223, M224',
        helpText: 'Comma-separated paper codes for multi-paper subjects. Leave blank for single-paper subjects.',
      },
      { name: 'is_compulsory', label: 'Compulsory', type: 'checkbox', checkboxLabel: 'Compulsory subject' },
      { name: 'description', label: 'Description', type: 'textarea' },
    ],
    fieldAliases: { paper_codes: 'paper_codes_display' },
    emptyForm: { name: '', code: '', paper_codes: '', is_compulsory: true, description: '' },
  },

  departments: {
    service: departmentsService,
    queryKey: ['departments'],
    createLabel: 'Add Department',
    subtitle: 'Organizational units for staff, subjects, and reporting',
    backLink: { to: '/school-admin/core', label: 'Core Management' },
    columns: [
      { key: 'name', label: 'Department', accessor: 'name', sortable: true, primary: true },
      { key: 'code', label: 'Code', accessor: 'code', primary: true },
      { key: 'head_name', label: 'Head', accessor: 'head_name', primary: true },
      { key: 'description', label: 'Description', accessor: 'description' },
    ],
    formFields: [
      { name: 'name', label: 'Name', required: true },
      { name: 'code', label: 'Code', required: true, helpText: 'Short unique code, e.g. SCI, ADMIN' },
      { name: 'head', label: 'Department Head', type: 'select', optionsFrom: 'staff' },
      { name: 'description', label: 'Description', type: 'textarea' },
    ],
    emptyForm: { name: '', code: '', head: '', description: '' },
  },

  homework: {
    service: homeworkService,
    queryKey: ['homework'],
    createLabel: 'Add Homework',
    subtitle: 'Homework assignments by class and subject',
    backLink: { to: '/school-admin/academics', label: 'Academics' },
    columns: [
      { key: 'title', label: 'Title', accessor: 'title', sortable: true },
      { key: 'assigned_date', label: 'Assigned', accessor: 'assigned_date' },
      { key: 'due_date', label: 'Due', accessor: 'due_date' },
    ],
    formFields: [
      { name: 'title', label: 'Title', required: true },
      { name: 'description', label: 'Description', type: 'textarea', required: true },
      { name: 'school_class', label: 'Class', type: 'select', required: true, optionsFrom: 'classes' },
      { name: 'subject', label: 'Subject', type: 'select', required: true, optionsFrom: 'subjects' },
      { name: 'assigned_date', label: 'Assigned Date', type: 'date', required: true },
      { name: 'due_date', label: 'Due Date', type: 'date', required: true },
    ],
    emptyForm: {
      title: '', description: '', school_class: '', subject: '',
      assigned_date: new Date().toISOString().slice(0, 10), due_date: '',
    },
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
    emptyForm: { title: '', description: '', school_class: '', subject: '', due_date: '', max_score: 100 },
  },

  subject_assignment: {
    redirectTo: '/school-admin/academics/subject-assignments',
  },
  teacher_assignments: {
    redirectTo: '/school-admin/academics/subject-assignments',
  },

  timetables: {
    service: timetablesService,
    queryKey: ['timetables'],
    singleton: { type: 'term', title: 'Current academic term', hideTableWhenLocked: false },
    createLabel: 'Add Manual Entry',
    subtitle: 'Prefer the generation wizard for full schedules — manual slots are for fine-tuning',
    backLink: { to: '/school-admin/academics/timetable/wizard', label: 'Timetable Wizard' },
    columns: [
      { key: 'school_class_name', label: 'Class', accessor: 'school_class_name' },
      { key: 'subject_name', label: 'Subject', accessor: 'subject_name' },
      { key: 'teacher_name', label: 'Teacher', accessor: 'teacher_name' },
      { key: 'day_label', label: 'Day', accessor: 'day_label' },
      { key: 'start_time', label: 'Start', accessor: 'start_time' },
      { key: 'end_time', label: 'End', accessor: 'end_time' },
      { key: 'schedule_type', label: 'Type', accessor: 'schedule_type' },
    ],
    formFields: [
      { name: 'school_class', label: 'Class', type: 'select', required: true, optionsFrom: 'classes' },
      { name: 'subject', label: 'Subject', type: 'select', required: true, optionsFrom: 'subjects' },
      { name: 'day_of_week', label: 'Day', type: 'select', required: true, options: [
        { value: '0', label: 'Monday' }, { value: '1', label: 'Tuesday' },
        { value: '2', label: 'Wednesday' }, { value: '3', label: 'Thursday' },
        { value: '4', label: 'Friday' }, { value: '5', label: 'Saturday' },
      ] },
      { name: 'start_time', label: 'Start Time', type: 'time', required: true },
      { name: 'end_time', label: 'End Time', type: 'time', required: true },
      { name: 'room', label: 'Room' },
    ],
    emptyForm: { school_class: '', subject: '', day_of_week: '0', start_time: '', end_time: '', room: '' },
  },

  fee_structures: {
    service: feeStructuresService,
    queryKey: ['fee-structures'],
    createLabel: 'Add Fee Structure',
    subtitle: 'Term fee items per class (UGX)',
    backLink: { to: '/school-admin/finance', label: 'Finance' },
    searchKeys: ['name', 'fee_category', 'amount', 'due_date', 'class_name', 'term_name'],
    columns: [
      { key: 'name', label: 'Name', accessor: 'name', sortable: true },
      { key: 'fee_category', label: 'Category', accessor: 'fee_category' },
      { key: 'amount', label: 'Amount (UGX)', accessor: 'amount' },
      { key: 'due_date', label: 'Due', accessor: 'due_date' },
    ],
    formFields: [
      { name: 'name', label: 'Fee Name', required: true },
      { name: 'fee_category', label: 'Category', type: 'select', options: [
        { value: 'tuition', label: 'Tuition' }, { value: 'boarding', label: 'Boarding' },
        { value: 'transport', label: 'Transport' }, { value: 'meals', label: 'Meals' },
        { value: 'other', label: 'Other' },
      ] },
      { name: 'school_class', label: 'Class', type: 'select', required: true, optionsFrom: 'classes' },
      { name: 'term', label: 'Term', type: 'select', required: true, optionsFrom: 'terms' },
      { name: 'amount', label: 'Amount (UGX)', type: 'number', required: true },
      { name: 'due_date', label: 'Due Date', type: 'date', required: true },
    ],
    emptyForm: { name: '', fee_category: 'tuition', school_class: '', term: '', amount: '', due_date: '' },
  },

  payment_recording: {
    service: feeStructuresService,
    queryKey: ['fee-payments-alt'],
    createLabel: 'Record Payment',
    subtitle: 'Use Billing & Invoices for payments',
    backLink: { to: '/school-admin/finance', label: 'Finance' },
    columns: [],
    formFields: [],
    emptyForm: {},
    redirectTo: '/school-admin/finance',
  },

  expenses: {
    service: accountingService,
    queryKey: ['accounting-entries'],
    createLabel: 'Add Entry',
    subtitle: 'Expense and ledger entries',
    backLink: { to: '/school-admin/finance', label: 'Finance' },
    columns: [
      { key: 'entry_date', label: 'Date', accessor: 'entry_date', sortable: true },
      { key: 'description', label: 'Description', accessor: 'description' },
      { key: 'amount', label: 'Amount', accessor: 'amount' },
      { key: 'debit_account', label: 'Debit', accessor: 'debit_account' },
      { key: 'credit_account', label: 'Credit', accessor: 'credit_account' },
    ],
    formFields: [
      { name: 'entry_date', label: 'Date', type: 'date', required: true },
      { name: 'description', label: 'Description', required: true },
      { name: 'amount', label: 'Amount', type: 'number', required: true },
      { name: 'debit_account', label: 'Debit Account', required: true },
      { name: 'credit_account', label: 'Credit Account', required: true },
      { name: 'reference', label: 'Reference' },
    ],
    emptyForm: { entry_date: new Date().toISOString().slice(0, 10), description: '', amount: '', debit_account: '', credit_account: '', reference: '' },
  },

  admissions: {
    service: admissionApplicationsService,
    queryKey: ['admission-applications'],
    listParams: { exclude_admitted: true },
    createLabel: 'New Application',
    subtitle: 'Applicant intake — no student record required until admission',
    backLink: { to: '/school-admin/admissions', label: 'Admissions' },
    columns: [
      { key: 'full_name', label: 'Applicant', accessor: 'full_name', sortable: true },
      { key: 'grade_applied', label: 'Grade', accessor: 'grade_applied' },
      { key: 'parent_name', label: 'Parent/Guardian', accessor: 'parent_name' },
      { key: 'application_date', label: 'Applied', accessor: 'application_date' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'first_name', label: 'First Name', required: true },
      { name: 'middle_name', label: 'Middle Name' },
      { name: 'last_name', label: 'Last Name', required: true },
      { name: 'date_of_birth', label: 'Date of Birth', type: 'date', required: true },
      { name: 'gender', label: 'Gender', type: 'select', required: true, options: [
        { value: 'male', label: 'Male' }, { value: 'female', label: 'Female' }, { value: 'other', label: 'Other' },
      ] },
      { name: 'email', label: 'Applicant Email', type: 'email' },
      { name: 'phone', label: 'Applicant Phone' },
      { name: 'parent_name', label: 'Parent/Guardian Name', required: true },
      { name: 'parent_email', label: 'Parent Email', type: 'email' },
      { name: 'parent_phone', label: 'Parent Phone', required: true },
      { name: 'parent_relationship', label: 'Relationship', type: 'select', options: [
        { value: 'father', label: 'Father' }, { value: 'mother', label: 'Mother' },
        { value: 'guardian', label: 'Guardian' }, { value: 'sponsor', label: 'Sponsor' }, { value: 'other', label: 'Other' },
      ] },
      { name: 'grade_applied', label: 'Grade Applied', required: true },
      { name: 'previous_school', label: 'Previous School' },
      { name: 'application_date', label: 'Application Date', type: 'date', required: true },
      { name: 'status', label: 'Status', type: 'select', options: [
        { value: 'pending', label: 'Pending' }, { value: 'under_review', label: 'Under Review' },
        { value: 'approved', label: 'Approved' }, { value: 'rejected', label: 'Rejected' },
        { value: 'waitlisted', label: 'Waitlisted' },
      ] },
      { name: 'notes', label: 'Notes', type: 'textarea' },
    ],
    emptyForm: {
      first_name: '', middle_name: '', last_name: '', date_of_birth: '', gender: 'male',
      email: '', phone: '', parent_name: '', parent_email: '', parent_phone: '',
      parent_relationship: 'guardian', grade_applied: '', previous_school: '',
      application_date: new Date().toISOString().slice(0, 10), status: 'pending', notes: '',
    },
    rowActions: [
      {
        key: 'admit',
        label: 'Admit',
        variant: 'primary',
        action: 'admit',
        show: (row) => !['admitted', 'rejected'].includes(row.status),
        confirmText: (row) => `Admit ${row.full_name || 'this applicant'} and create a student record?`,
        confirmTextButton: 'Yes, admit',
      },
      {
        key: 'reject',
        label: 'Reject',
        action: 'reject',
        show: (row) => !['admitted', 'rejected'].includes(row.status),
        confirmText: (row) => `Reject application for ${row.full_name || 'this applicant'}?`,
        confirmTextButton: 'Yes, reject',
      },
    ],
  },

  admitted_students: {
    service: admittedStudentsService,
    queryKey: ['admitted-students'],
    createLabel: 'Admitted Student',
    subtitle: 'Students enrolled through the admissions pipeline',
    backLink: { to: '/school-admin/admissions', label: 'Admissions' },
    creatable: false,
    deletable: false,
    columns: [
      { key: 'full_name', label: 'Student', accessor: 'full_name', sortable: true },
      { key: 'student_admission_number', label: 'Admission No.', accessor: 'student_admission_number' },
      { key: 'grade_applied', label: 'Grade Applied', accessor: 'grade_applied' },
      { key: 'admitted_class_name', label: 'Class', accessor: 'admitted_class_name' },
      { key: 'admission_date', label: 'Admitted', accessor: 'admission_date' },
    ],
    formFields: [
      { name: 'full_name', label: 'Applicant', type: 'text' },
      { name: 'student_admission_number', label: 'Admission Number', type: 'text' },
      { name: 'grade_applied', label: 'Grade Applied', type: 'text' },
      { name: 'admission_date', label: 'Admission Date', type: 'date' },
      { name: 'notes', label: 'Notes', type: 'textarea' },
    ],
    emptyForm: {},
  },

  admission_vacancies: {
    service: admissionVacanciesService,
    queryKey: ['admission-vacancies'],
    createLabel: 'New Vacancy',
    subtitle: 'Advertise open grade slots on the landing page and parent portal',
    backLink: { to: '/school-admin/admissions', label: 'Admissions' },
    columns: [
      { key: 'title', label: 'Title', accessor: 'title', sortable: true },
      { key: 'grade_levels', label: 'Grades', accessor: 'grade_levels' },
      { key: 'remaining_openings', label: 'Openings', accessor: 'remaining_openings' },
      { key: 'application_deadline', label: 'Deadline', accessor: 'application_deadline' },
      { key: 'is_published', label: 'Published', format: 'boolean', accessor: 'is_published' },
      { key: 'show_on_landing', label: 'Landing', format: 'boolean', accessor: 'show_on_landing' },
      { key: 'show_on_parent_portal', label: 'Parents', format: 'boolean', accessor: 'show_on_parent_portal' },
    ],
    formFields: [
      { name: 'title', label: 'Title', required: true },
      { name: 'description', label: 'Description', type: 'textarea' },
      { name: 'grade_levels', label: 'Grade Levels', placeholder: 'e.g. Grade 1, Grade 2' },
      { name: 'school_class', label: 'Class (optional)', type: 'select', optionsFrom: 'classes' },
      { name: 'openings_count', label: 'Openings', type: 'number', required: true },
      { name: 'application_deadline', label: 'Application Deadline', type: 'date' },
      { name: 'contact_email', label: 'Contact Email', type: 'email' },
      { name: 'contact_phone', label: 'Contact Phone' },
      { name: 'is_active', label: 'Active', type: 'checkbox', checkboxLabel: 'Vacancy is active' },
      { name: 'is_published', label: 'Published', type: 'checkbox', checkboxLabel: 'Published to applicants' },
      { name: 'show_on_landing', label: 'Landing Page', type: 'checkbox', checkboxLabel: 'Show on public landing page' },
      { name: 'show_on_parent_portal', label: 'Parent Portal', type: 'checkbox', checkboxLabel: 'Show on parent dashboards' },
    ],
    emptyForm: {
      title: '', description: '', grade_levels: '', school_class: '', openings_count: 1,
      application_deadline: '', contact_email: '', contact_phone: '',
      is_active: true, is_published: false, show_on_landing: false, show_on_parent_portal: false,
    },
    rowActions: [
      {
        key: 'publish',
        label: 'Publish',
        variant: 'primary',
        action: 'publish',
        show: (row) => !row.is_published,
        confirmText: (row) => `Publish "${row.title}" so it can appear on configured channels?`,
        confirmTextButton: 'Yes, publish',
      },
    ],
  },

  medical_records: {
    service: medicalRecordsService,
    queryKey: ['medical-records'],
    createLabel: 'Add Medical Record',
    subtitle: 'Student health records',
    backLink: { to: '/school-admin/admissions', label: 'Admissions' },
    columns: [
      { key: 'condition', label: 'Condition', accessor: 'condition', sortable: true },
      { key: 'recorded_date', label: 'Recorded', accessor: 'recorded_date' },
      { key: 'is_chronic', label: 'Chronic', render: (row) => yesNo(row.is_chronic) },
    ],
    formFields: [
      { name: 'student', label: 'Student', type: 'select', required: true, optionsFrom: 'students' },
      { name: 'condition', label: 'Condition', required: true },
      { name: 'recorded_date', label: 'Recorded Date', type: 'date', required: true },
      { name: 'is_chronic', label: 'Chronic', type: 'checkbox', checkboxLabel: 'Chronic condition' },
      { name: 'allergies', label: 'Allergies', type: 'textarea' },
      { name: 'medications', label: 'Medications', type: 'textarea' },
    ],
    emptyForm: { student: '', condition: '', recorded_date: new Date().toISOString().slice(0, 10), is_chronic: false, allergies: '', medications: '' },
  },

  student_attendance: {
    service: attendanceService,
    queryKey: ['attendance-records'],
    createLabel: 'Mark Attendance',
    subtitle: 'Daily student and staff attendance',
    columns: [
      { key: 'date', label: 'Date', accessor: 'date', sortable: true },
      { key: 'attendee_type', label: 'Type', accessor: 'attendee_type' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'attendee_type', label: 'Type', type: 'select', required: true, options: [
        { value: 'student', label: 'Student' }, { value: 'staff', label: 'Staff' },
      ] },
      { name: 'student', label: 'Student', type: 'select', optionsFrom: 'students' },
      { name: 'date', label: 'Date', type: 'date', required: true },
      { name: 'status', label: 'Status', type: 'select', required: true, options: [
        { value: 'present', label: 'Present' }, { value: 'absent', label: 'Absent' },
        { value: 'late', label: 'Late' }, { value: 'excused', label: 'Excused' },
      ] },
    ],
    emptyForm: { attendee_type: 'student', student: '', date: new Date().toISOString().slice(0, 10), status: 'present' },
  },

  staff_attendance: {
    service: attendanceService,
    queryKey: ['staff-attendance'],
    createLabel: 'Mark Staff Attendance',
    subtitle: 'Staff attendance records',
    columns: [
      { key: 'date', label: 'Date', accessor: 'date', sortable: true },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'attendee_type', label: 'Type', type: 'hidden', defaultValue: 'staff' },
      { name: 'date', label: 'Date', type: 'date', required: true },
      { name: 'status', label: 'Status', type: 'select', required: true, options: [
        { value: 'present', label: 'Present' }, { value: 'absent', label: 'Absent' },
        { value: 'late', label: 'Late' },
      ] },
    ],
    emptyForm: { attendee_type: 'staff', date: new Date().toISOString().slice(0, 10), status: 'present' },
  },

  examination_management: {
    service: examsService,
    queryKey: ['exams'],
    createLabel: 'Schedule Exam',
    subtitle: 'Examinations by class, subject, and term',
    backLink: { to: '/school-admin/examinations', label: 'Examinations' },
    columns: [
      { key: 'name', label: 'Exam', accessor: 'name', sortable: true },
      { key: 'subject_name', label: 'Subject', accessor: 'subject_name' },
      { key: 'paper_code', label: 'Paper', accessor: 'paper_code' },
      { key: 'school_class_name', label: 'Class', accessor: 'school_class_name' },
      { key: 'term_name', label: 'Term', accessor: 'term_name' },
      { key: 'exam_date', label: 'Date', accessor: 'exam_date' },
      { key: 'exam_type', label: 'Type', accessor: 'exam_type' },
    ],
    formFields: [
      { name: 'subject', label: 'Subject', type: 'select', required: true, optionsFrom: 'subjects', clears: ['paper', 'school_class', 'term'] },
      {
        name: 'paper',
        label: 'Paper (optional)',
        type: 'select',
        optionsFrom: 'subjectPapers',
        filterByField: 'subject',
        placeholder: 'Whole subject (no paper)',
        showWhen: (form, opts) => {
          const papers = (opts.subjectPapers || []).filter((p) => p.subjectId === form.subject);
          return Boolean(form.subject) && papers.length > 0;
        },
      },
      { name: 'school_class', label: 'Class', type: 'select', required: true, optionsFrom: 'classes', clears: ['term'] },
      { name: 'term', label: 'Term', type: 'select', required: true, optionsFrom: 'terms' },
      { name: 'name', label: 'Exam Name', required: true },
      { name: 'exam_date', label: 'Exam Date', type: 'date', required: true },
      { name: 'exam_type', label: 'Type', type: 'select', options: [
        { value: 'midterm', label: 'Midterm' }, { value: 'final', label: 'Final' },
        { value: 'continuous', label: 'Continuous Assessment' },
      ] },
      { name: 'max_score', label: 'Max Score', type: 'number' },
    ],
    emptyForm: { name: '', subject: '', paper: '', school_class: '', term: '', exam_date: '', exam_type: 'final', max_score: 100 },
  },

  library_management: {
    service: booksService,
    queryKey: ['library-books'],
    createLabel: 'Add Book',
    subtitle: 'Library catalogue',
    columns: [
      { key: 'title', label: 'Title', accessor: 'title', sortable: true },
      { key: 'author', label: 'Author', accessor: 'author' },
      { key: 'isbn', label: 'ISBN', accessor: 'isbn' },
      { key: 'available_copies', label: 'Available', accessor: 'available_copies' },
    ],
    formFields: [
      { name: 'title', label: 'Title', required: true },
      { name: 'author', label: 'Author', required: true },
      { name: 'isbn', label: 'ISBN' },
      { name: 'category', label: 'Category' },
      { name: 'total_copies', label: 'Total Copies', type: 'number' },
    ],
    emptyForm: { title: '', author: '', isbn: '', category: '', total_copies: 1 },
    mapCreate: (data) => ({ ...data, available_copies: data.total_copies || 1 }),
  },

  vehicles: {
    service: vehiclesService,
    queryKey: ['vehicles'],
    createLabel: 'Add Vehicle',
    subtitle: 'School fleet vehicles',
    backLink: { to: '/school-admin/transport', label: 'Transport' },
    columns: [
      { key: 'registration_number', label: 'Registration', accessor: 'registration_number', sortable: true },
      { key: 'make', label: 'Make', accessor: 'make' },
      { key: 'capacity', label: 'Capacity', accessor: 'capacity' },
      { key: 'status', label: 'Status', accessor: 'status' },
    ],
    formFields: [
      { name: 'registration_number', label: 'Registration No.', required: true },
      { name: 'make', label: 'Make', required: true },
      { name: 'model', label: 'Model', required: true },
      { name: 'capacity', label: 'Capacity', type: 'number', required: true },
      { name: 'vehicle_type', label: 'Type', type: 'select', options: [
        { value: 'bus', label: 'Bus' }, { value: 'van', label: 'Van' }, { value: 'minibus', label: 'Minibus' },
      ] },
    ],
    emptyForm: { registration_number: '', make: '', model: '', capacity: 40, vehicle_type: 'bus' },
  },

  inventory_items: {
    service: inventoryItemsService,
    queryKey: ['inventory-items'],
    createLabel: 'Add Item',
    subtitle: 'Stock items and supplies',
    columns: [
      { key: 'name', label: 'Item', accessor: 'name', sortable: true },
      { key: 'sku', label: 'SKU', accessor: 'sku' },
      { key: 'category', label: 'Category', accessor: 'category' },
      { key: 'quantity', label: 'Qty', accessor: 'quantity' },
    ],
    formFields: [
      { name: 'name', label: 'Item Name', required: true },
      { name: 'sku', label: 'SKU', required: true },
      { name: 'category', label: 'Category', required: true },
      { name: 'unit', label: 'Unit', placeholder: 'pcs' },
      { name: 'quantity', label: 'Quantity', type: 'number' },
      { name: 'reorder_level', label: 'Reorder Level', type: 'number' },
    ],
    emptyForm: { name: '', sku: '', category: '', unit: 'pcs', quantity: 0, reorder_level: 10 },
  },

  salary_structures: {
    service: salaryStructuresService,
    queryKey: ['salary-structures'],
    createLabel: 'Add Salary Structure',
    subtitle: 'Staff salary templates',
    backLink: { to: '/school-admin/finance', label: 'Finance' },
    columns: [
      { key: 'staff', label: 'Staff ID', accessor: 'staff' },
      { key: 'basic_salary', label: 'Basic (UGX)', accessor: 'basic_salary' },
      { key: 'effective_from', label: 'From', accessor: 'effective_from' },
      { key: 'is_active', label: 'Active', render: (row) => yesNo(row.is_active) },
    ],
    formFields: [
      { name: 'staff', label: 'Staff', type: 'select', required: true, optionsFrom: 'staff' },
      { name: 'basic_salary', label: 'Basic Salary (UGX)', type: 'number', required: true },
      { name: 'effective_from', label: 'Effective From', type: 'date', required: true },
      { name: 'is_active', label: 'Active', type: 'checkbox', checkboxLabel: 'Currently active' },
    ],
    emptyForm: { staff: '', basic_salary: '', effective_from: '', is_active: true },
  },

  announcements: {
    service: announcementsService,
    queryKey: ['announcements'],
    createLabel: 'New Announcement',
    subtitle: 'School-wide announcements with email and in-app delivery',
    columns: [
      { key: 'title', label: 'Title', accessor: 'title', sortable: true },
      { key: 'audience', label: 'Audience', accessor: 'target_audience' },
      { key: 'is_published', label: 'Published', format: 'boolean', accessor: 'is_published' },
      { key: 'publish_date', label: 'Publish Date', accessor: 'publish_date' },
    ],
    formFields: [
      { name: 'title', label: 'Title', required: true },
      { name: 'content', label: 'Content', type: 'textarea', required: true },
      { name: 'audience', label: 'Audience', type: 'select', options: [
        { value: 'all', label: 'Everyone' }, { value: 'parents', label: 'Parents' },
        { value: 'staff', label: 'Staff' }, { value: 'students', label: 'Students' },
      ] },
      { name: 'channels', label: 'Delivery Channels', type: 'multiselect', options: [
        { value: 'email', label: 'Email' },
        { value: 'notification', label: 'In-app Notification' },
        { value: 'sms', label: 'SMS' },
        { value: 'whatsapp', label: 'WhatsApp' },
      ] },
      { name: 'priority', label: 'Priority', type: 'select', options: [
        { value: 'low', label: 'Low' },
        { value: 'normal', label: 'Normal' },
        { value: 'high', label: 'High' },
        { value: 'urgent', label: 'Urgent' },
      ] },
    ],
    emptyForm: { title: '', content: '', audience: 'all', channels: ['email', 'notification'], priority: 'normal' },
    fieldAliases: { audience: 'target_audience' },
    deletable: true,
    allowBulkDelete: true,
    bulkDeleteLabel: 'Delete All Announcements',
    rowActions: [
      {
        key: 'publish',
        label: 'Publish',
        variant: 'primary',
        show: (row) => !row.is_published,
        action: 'publish',
        confirmText: (row) => {
          const channels = Array.isArray(row.channels) && row.channels.length
            ? row.channels
            : ['email', 'notification'];
          return `Publish "${row.title}" via ${channels.join(', ')}?`;
        },
        confirmTextButton: 'Yes, publish',
        payload: (row) => ({
          channels: Array.isArray(row.channels) && row.channels.length
            ? row.channels
            : ['email', 'notification'],
        }),
      },
    ],
  },
};

export function getEntityConfig(featureKey) {
  if (featureKey === 'hr_departments') {
    return {
      ...ENTITY_REGISTRY.departments,
      queryKey: ['hr-departments'],
      backLink: { to: '/school-admin/hr', label: 'Human Resources' },
    };
  }
  return ENTITY_REGISTRY_EXTRAS[featureKey] || ENTITY_REGISTRY[featureKey] || null;
}