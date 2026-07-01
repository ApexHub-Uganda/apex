export const MOCK_SUPER_ADMIN_DASHBOARD = {
  stats: {
    total_schools: 128,
    active_schools: 112,
    pending_schools: 8,
    suspended_schools: 3,
    unverified_schools: 5,
    active_subscriptions: 112,
    trial_subscriptions: 24,
    grace_period_subscriptions: 4,
    monthly_revenue: 485200,
    revenue_mtd: 128400,
    total_revenue: 2840000,
    arr: 5822400,
    total_students: 45230,
    total_staff: 3180,
    active_users_24h: 1842,
    active_sessions: 956,
    growth_rate: 12.4,
    churn_rate: 2.1,
    conversion_rate: 68.5,
    avg_revenue_per_school: 3789,
    failed_payments_30d: 7,
  },
  revenue_chart: {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [{ label: 'Revenue ($)', data: [320000, 380000, 410000, 395000, 450000, 485200] }],
  },
  schools_chart: {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [{ label: 'New Schools', data: [8, 12, 15, 10, 18, 22] }],
  },
  enrollment_chart: {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [{ label: 'New Enrollments', data: [1200, 1450, 1680, 1520, 1890, 2100] }],
  },
  subscription_chart: {
    labels: ['Basic', 'Premium', 'Premium Plus', 'Free Trial'],
    datasets: [{ label: 'Subscriptions', data: [42, 38, 22, 26] }],
  },
  country_chart: {
    labels: ['Kenya', 'Uganda', 'Tanzania', 'Nigeria', 'Ghana', 'Rwanda'],
    datasets: [{ label: 'Schools', data: [38, 22, 18, 24, 15, 11] }],
  },
  plan_breakdown: [
    { plan: 'Basic', count: 42, percent: 32.8 },
    { plan: 'Premium', count: 38, percent: 29.7 },
    { plan: 'Premium Plus', count: 22, percent: 17.2 },
    { plan: 'Free Trial', count: 26, percent: 20.3 },
  ],
  system_health: {
    api_status: 'healthy',
    database: 'connected',
    uptime_percent: 99.97,
    storage_used_mb: 48200,
    storage_cap_mb: 131072,
    active_sessions: 956,
    failed_jobs: 0,
  },
  recent_schools: [
    { id: 1, name: 'Greenwood Academy', plan: 'Premium Plus', status: 'active', students: 1240, country: 'Kenya' },
    { id: 2, name: 'Riverside High', plan: 'Premium', status: 'active', students: 890, country: 'Uganda' },
    { id: 3, name: 'Summit International', plan: 'Free Trial', status: 'pending', students: 450, country: 'Tanzania' },
    { id: 4, name: 'Oak Valley School', plan: 'Basic', status: 'suspended', students: 320, country: 'Nigeria' },
  ],
  top_schools: [
    { id: 1, name: 'Greenwood Academy', students: 1240, country: 'Kenya' },
    { id: 2, name: 'Riverside High', students: 890, country: 'Uganda' },
    { id: 3, name: 'Summit International', students: 450, country: 'Tanzania' },
    { id: 4, name: 'Lakeside Prep', students: 380, country: 'Ghana' },
    { id: 5, name: 'Oak Valley School', students: 320, country: 'Nigeria' },
  ],
  recent_activity: [
    { id: 1, action: 'create', description: 'New school registered: Greenwood Academy', user: 'admin@greenwood.edu', tenant: 'Greenwood Academy', time: new Date(Date.now() - 3600000).toISOString() },
    { id: 2, action: 'login', description: 'Successful login from 102.68.12.44', user: 'superadmin@apexhub.io', tenant: 'Platform', time: new Date(Date.now() - 7200000).toISOString() },
    { id: 3, action: 'update', description: 'Subscription upgraded to Premium Plus', user: 'admin@riverside.edu', tenant: 'Riverside High', time: new Date(Date.now() - 14400000).toISOString() },
    { id: 4, action: 'create', description: 'Payment received — $2,499.00', user: 'system', tenant: 'Summit International', time: new Date(Date.now() - 28800000).toISOString() },
  ],
};

export const MOCK_SCHOOL_DASHBOARD = {
  stats: {
    total_students: 1240,
    total_staff: 86,
    attendance_rate: 94.2,
    fee_collection: 87.5,
    active_classes: 42,
    pending_fees: 125000,
  },
  attendance_chart: {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
    datasets: [
      { label: 'Present', data: [1180, 1195, 1170, 1200, 1185] },
      { label: 'Absent', data: [60, 45, 70, 40, 55] },
    ],
  },
  finance_chart: {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [{ label: 'Collected', data: [420000, 445000, 460000, 438000, 475000, 490000] }],
  },
  recent_activities: [
    { id: 1, type: 'enrollment', message: '12 new students enrolled', time: '2h ago' },
    { id: 2, type: 'payment', message: 'Fee payment received — Grade 10', time: '4h ago' },
    { id: 3, type: 'attendance', message: 'Attendance marked for all classes', time: '6h ago' },
  ],
};

export const DEFAULT_FEATURE_FLAGS = {
  students: true,
  staff: true,
  classes: true,
  attendance: true,
  finance: true,
  library: true,
  hostel: false,
  transport: true,
  inventory: true,
  hr: true,
  payroll: true,
  reports: true,
  communication: true,
};

export const MOCK_SCHOOLS = [
  { id: 1, name: 'Greenwood Academy', email: 'admin@greenwood.edu', plan: 'Enterprise', status: 'active', students: 1240, created_at: '2025-01-15' },
  { id: 2, name: 'Riverside High', email: 'admin@riverside.edu', plan: 'Professional', status: 'active', students: 890, created_at: '2025-02-20' },
  { id: 3, name: 'Summit International', email: 'admin@summit.edu', plan: 'Enterprise', status: 'trial', students: 450, created_at: '2025-06-01' },
  { id: 4, name: 'Oak Valley School', email: 'admin@oakvalley.edu', plan: 'Starter', status: 'suspended', students: 320, created_at: '2024-11-10' },
];

export const MOCK_PLANS = [
  { id: 1, name: 'Starter', price: 99, billing_cycle: 'monthly', max_students: 500, features: ['Students', 'Staff', 'Classes', 'Attendance'] },
  { id: 2, name: 'Professional', price: 249, billing_cycle: 'monthly', max_students: 2000, features: ['All Starter', 'Finance', 'Library', 'Reports'] },
  { id: 3, name: 'Enterprise', price: 499, billing_cycle: 'monthly', max_students: 10000, features: ['All Professional', 'Hostel', 'Transport', 'HR', 'Payroll'] },
];

export const MOCK_STUDENTS = [
  { id: 1, admission_no: 'STU-2026-001', name: 'Aisha Patel', class: 'Grade 10-A', gender: 'Female', status: 'active', guardian: 'Raj Patel' },
  { id: 2, admission_no: 'STU-2026-002', name: 'James Wilson', class: 'Grade 9-B', gender: 'Male', status: 'active', guardian: 'Mary Wilson' },
  { id: 3, admission_no: 'STU-2026-003', name: 'Emma Chen', class: 'Grade 11-A', gender: 'Female', status: 'active', guardian: 'Li Chen' },
  { id: 4, admission_no: 'STU-2026-004', name: 'Omar Hassan', class: 'Grade 8-C', gender: 'Male', status: 'inactive', guardian: 'Fatima Hassan' },
];

export const MOCK_STAFF = [
  { id: 1, employee_id: 'EMP-001', name: 'Dr. Sarah Mitchell', role: 'Principal', department: 'Administration', status: 'active' },
  { id: 2, employee_id: 'EMP-002', name: 'Mr. David Kim', role: 'Mathematics Teacher', department: 'Academics', status: 'active' },
  { id: 3, employee_id: 'EMP-003', name: 'Ms. Laura Brooks', role: 'Librarian', department: 'Library', status: 'active' },
];

export const withFallback = async (apiCall, mockData) => {
  try {
    return await apiCall();
  } catch {
    return mockData;
  }
};