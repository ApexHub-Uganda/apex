/** Static content for Apex Hub marketing landing page. */
import {
  FiUsers, FiBookOpen, FiCalendar, FiAward, FiFileText, FiDollarSign,
  FiBriefcase, FiPackage, FiBook, FiTruck, FiHome, FiHeart, FiBarChart2,
  FiMessageSquare, FiCpu, FiShield, FiLayers, FiGlobe, FiCloud, FiLock,
  FiSmartphone, FiZap, FiDatabase, FiRefreshCw, FiCheck, FiTrendingUp,
  FiSearch, FiMail, FiBell, FiGrid, FiSettings, FiCreditCard,
} from 'react-icons/fi';

export const BRAND = {
  name: 'Apex Hub',
  tagline: 'The Easy Way',
  primary: '#0F766E',
  secondary: '#FF7F50',
  accent: '#F5E6CA',
};

export const NAV_LINKS = [
  { label: 'Home', href: '#home' },
  { label: 'Features', href: '#features' },
  { label: 'Solutions', href: '#solutions' },
  { label: 'Pricing', href: '#pricing' },
  { label: 'Testimonials', href: '#testimonials' },
  { label: 'About', href: '#about' },
  { label: 'Resources', href: '#resources' },
  { label: 'Contact', href: '#contact' },
];

export const TRUST_BADGES = [
  { icon: FiCloud, label: 'Cloud Based' },
  { icon: FiLock, label: 'Secure' },
  { icon: FiLayers, label: 'Multi-Tenant' },
  { icon: FiZap, label: '99.9% Uptime' },
];

export const TRUSTED_LOGOS = [
  'Greenfield Academy', 'Lakeside University', 'Summit College',
  'Horizon Institute', 'Nova Training', 'Pinnacle Schools',
  'BrightPath Academy', 'Unity College',
];

export const FEATURES = [
  { icon: FiUsers, title: 'Admissions', desc: 'Streamline applications, enrollment, and student onboarding from one portal.' },
  { icon: FiCalendar, title: 'Attendance', desc: 'Real-time student and staff attendance with automated alerts and reports.' },
  { icon: FiAward, title: 'Examinations', desc: 'Manage exams, marks entry, grading, and report cards with confidence.' },
  { icon: FiFileText, title: 'Academic Reports', desc: 'Generate transcripts, progress reports, and analytics instantly.' },
  { icon: FiDollarSign, title: 'Fees', desc: 'Fee structures, invoicing, payments, and reconciliation made effortless.' },
  { icon: FiBriefcase, title: 'Payroll', desc: 'Salary structures, payroll runs, and payslips for your entire staff.' },
  { icon: FiPackage, title: 'Inventory', desc: 'Track supplies, stock movement, and purchase orders across campuses.' },
  { icon: FiBook, title: 'Library', desc: 'Catalog management, borrowing, returns, and overdue tracking.' },
  { icon: FiTruck, title: 'Transport', desc: 'Routes, vehicles, drivers, and student transport assignments.' },
  { icon: FiHome, title: 'Hostel', desc: 'Room allocation, boarding management, and warden workflows.' },
  { icon: FiHeart, title: 'Parent Portal', desc: 'Parents stay informed on fees, grades, attendance, and announcements.' },
  { icon: FiBookOpen, title: 'Student Portal', desc: 'Students access timetables, homework, results, and resources.' },
  { icon: FiUsers, title: 'Teacher Portal', desc: 'Class management, attendance, assignments, and communication tools.' },
  { icon: FiBarChart2, title: 'Analytics', desc: 'Executive dashboards with KPIs across academics, finance, and operations.' },
  { icon: FiMessageSquare, title: 'Communication', desc: 'SMS, email, in-app notifications, and broadcast messaging.' },
  { icon: FiCpu, title: 'AI Insights', desc: 'Predictive analytics on attendance, performance, and fee collection.' },
  { icon: FiShield, title: 'Role Management', desc: 'Granular permissions for 12+ roles with module and sub-module control.' },
  { icon: FiGlobe, title: 'Multi-Campus', desc: 'Manage multiple schools or branches from a single cloud account.' },
  { icon: FiSettings, title: 'Custom Branding', desc: 'Your logo, colors, and identity across every portal and report.' },
  { icon: FiDatabase, title: 'Cloud Backup', desc: 'Automatic daily backups with point-in-time recovery options.' },
];

export const WHY_BENEFITS = [
  { icon: FiCloud, title: 'Cloud Based', desc: 'Access anywhere. No servers to maintain. Always up to date.' },
  { icon: FiLock, title: 'Enterprise Security', desc: 'Encryption at rest and in transit with role-based access control.' },
  { icon: FiZap, title: 'Blazing Fast', desc: 'Optimized for speed on desktop, tablet, and mobile devices.' },
  { icon: FiTrendingUp, title: 'Infinitely Scalable', desc: 'From 50 students to 50,000 — Apex Hub grows with you.' },
  { icon: FiRefreshCw, title: 'Automatic Backups', desc: 'Daily snapshots with disaster recovery built in.' },
  { icon: FiShield, title: 'Role Permissions', desc: 'Control exactly who sees and edits every module.' },
  { icon: FiSmartphone, title: 'Mobile Friendly', desc: 'Full responsive experience for every stakeholder.' },
  { icon: FiGrid, title: 'Easy Deployment', desc: 'Go live in days, not months. Guided onboarding included.' },
  { icon: FiDollarSign, title: 'Affordable', desc: 'Transparent pricing designed for African institutions.' },
];

export const WORKFLOW_STEPS = [
  { step: '01', title: 'School Registers', desc: 'Create your institution profile in minutes.' },
  { step: '02', title: 'Chooses Plan', desc: 'Pick Basic, Premium, or Premium Plus.' },
  { step: '03', title: 'Adds Staff', desc: 'Onboard teachers, admins, and support teams.' },
  { step: '04', title: 'Registers Students', desc: 'Import or enroll students with full records.' },
  { step: '05', title: 'Starts Managing', desc: 'Attendance, fees, exams — all in one place.' },
  { step: '06', title: 'Everything Easier', desc: 'Operations run smoother. Everyone stays aligned.' },
];

export const PRICING_PLANS = [
  {
    id: 'basic',
    name: 'Basic',
    monthly: 49,
    yearly: 470,
    students: '500',
    users: '25',
    storage: '10 GB',
    sms: '500 / mo',
    email: '2,000 / mo',
    features: ['Core modules', 'Student & staff management', 'Attendance', 'Basic reports', 'Email support'],
    cta: 'Start Free Trial',
  },
  {
    id: 'premium',
    name: 'Premium',
    monthly: 129,
    yearly: 1238,
    students: '2,500',
    users: '100',
    storage: '50 GB',
    sms: '2,500 / mo',
    email: '10,000 / mo',
    recommended: true,
    features: ['Everything in Basic', 'Finance & payroll', 'Examinations', 'Library & inventory', 'Parent portal', 'Priority support'],
    cta: 'Start Free Trial',
  },
  {
    id: 'premium_plus',
    name: 'Premium Plus',
    monthly: 249,
    yearly: 2390,
    students: 'Unlimited',
    users: 'Unlimited',
    storage: '200 GB',
    sms: '10,000 / mo',
    email: 'Unlimited',
    features: ['Everything in Premium', 'Multi-campus', 'AI insights', 'API access', 'Custom branding', 'Dedicated success manager'],
    cta: 'Contact Sales',
  },
];

export const STATS = [
  { value: 500, suffix: '+', label: 'Schools' },
  { value: 250000, suffix: '+', label: 'Students' },
  { value: 12000, suffix: '+', label: 'Teachers' },
  { value: 99.9, suffix: '%', label: 'Uptime', decimals: 1 },
  { value: 15, suffix: 'M+', label: 'Records Managed' },
];

export const TESTIMONIALS = [
  { name: 'Dr. Amara Okafor', role: 'Principal', school: 'Greenfield Academy', rating: 5, quote: 'Apex Hub transformed how we manage academics and finance. Our admin workload dropped by 40% in the first term.', avatar: 'AO' },
  { name: 'James Mwangi', role: 'Bursar', school: 'Summit College', rating: 5, quote: 'Fee collection used to take weeks. Now parents pay online and we reconcile in real time. Remarkable platform.', avatar: 'JM' },
  { name: 'Sarah Ndlovu', role: 'Head Teacher', school: 'Lakeside University', rating: 5, quote: 'Teachers love the portal. Attendance, homework, and report cards are finally in one cohesive system.', avatar: 'SN' },
  { name: 'David Kiprop', role: 'IT Director', school: 'Horizon Institute', rating: 5, quote: 'Security, uptime, and support are enterprise-grade. We migrated 3 campuses without a single day of downtime.', avatar: 'DK' },
];

export const CASE_STUDIES = [
  { school: 'Pinnacle Schools', before: 'Manual registers, delayed fee reports', after: '98% on-time fee collection', metric: '+62% efficiency' },
  { school: 'Nova Training', before: 'Paper-based attendance', after: 'Real-time parent notifications', metric: '85% parent engagement' },
  { school: 'Unity College', before: 'Disconnected spreadsheets', after: 'Unified academic dashboard', metric: '3× faster reporting' },
];

export const SECURITY_ITEMS = [
  { icon: FiLock, title: 'AES-256 Encryption', desc: 'Data encrypted at rest and in transit across all services.' },
  { icon: FiRefreshCw, title: 'Daily Backups', desc: 'Automated snapshots with geo-redundant storage.' },
  { icon: FiCloud, title: 'Cloud Hosting', desc: 'Hosted on enterprise-grade infrastructure with SLA guarantees.' },
  { icon: FiFileText, title: 'Audit Logs', desc: 'Complete activity trails for compliance and accountability.' },
  { icon: FiShield, title: 'Role Permissions', desc: 'Granular access control at module and sub-module level.' },
  { icon: FiGlobe, title: 'GDPR-Ready', desc: 'Privacy-by-design architecture for global compliance.' },
];

/** Base folder for swappable mobile showcase PNGs (see public/landing/mobile/README.md). */
export const MOBILE_SHOWCASE_IMAGE_DIR = '/landing/mobile';

export const MOBILE_APPS = [
  {
    id: 'parent-portal',
    name: 'Parent Portal',
    image: `${MOBILE_SHOWCASE_IMAGE_DIR}/parent-portal.png`,
    alt: 'Parent Portal mobile app screenshot',
  },
  {
    id: 'teacher-portal',
    name: 'Teacher Portal',
    image: `${MOBILE_SHOWCASE_IMAGE_DIR}/teacher-portal.png`,
    alt: 'Teacher Portal mobile app screenshot',
  },
  {
    id: 'student-portal',
    name: 'Student Portal',
    image: `${MOBILE_SHOWCASE_IMAGE_DIR}/student-portal.png`,
    alt: 'Student Portal mobile app screenshot',
  },
  {
    id: 'finance-app',
    name: 'Finance App',
    image: `${MOBILE_SHOWCASE_IMAGE_DIR}/finance-app.png`,
    alt: 'Finance app mobile screenshot',
  },
];

export const FAQ_ITEMS = [
  { q: 'How long does implementation take?', a: 'Most schools go live within 5–14 days with our guided onboarding. Data migration support is included on Premium plans.' },
  { q: 'Can we migrate existing student data?', a: 'Yes. Import via CSV, Excel, or API. Our team assists with mapping and validation at no extra cost for Premium Plus.' },
  { q: 'Is Apex Hub suitable for universities?', a: 'Absolutely. Multi-campus, department structures, and large student volumes are fully supported.' },
  { q: 'What payment methods are supported?', a: 'Mobile money, card gateways, bank transfers, and cash recording with full reconciliation.' },
  { q: 'Do you offer training for staff?', a: 'Yes — video tutorials, documentation, live webinars, and dedicated onboarding for Premium Plus clients.' },
  { q: 'What happens if we exceed our student limit?', a: 'We notify you in advance. Upgrade seamlessly or add capacity packs without disruption.' },
];

export const RESOURCES = [
  { title: 'Blog', desc: 'Insights on school management and EdTech.', href: '#resources' },
  { title: 'Documentation', desc: 'Complete guides for every module.', href: '#resources' },
  { title: 'Release Notes', desc: 'Latest features and improvements.', href: '#resources' },
  { title: 'API', desc: 'REST API for custom integrations.', href: '#resources' },
  { title: 'Help Center', desc: 'Searchable knowledge base.', href: '#resources' },
  { title: 'Community', desc: 'Connect with other institutions.', href: '#resources' },
];

export const INTEGRATIONS = [
  'Google Workspace', 'Microsoft 365', 'M-Pesa', 'MTN MoMo',
  'Stripe', 'Paystack', 'Flutterwave', 'REST API',
];

export const DASHBOARD_TABS = [
  { id: 'admin', label: 'Admin Dashboard' },
  { id: 'teacher', label: 'Teacher Portal' },
  { id: 'parent', label: 'Parent Portal' },
  { id: 'student', label: 'Student Portal' },
  { id: 'finance', label: 'Finance' },
  { id: 'analytics', label: 'Analytics' },
];

export const ROADMAP_ITEMS = [
  { quarter: 'Q3 2026', title: 'AI Attendance Predictions', status: 'In Progress' },
  { quarter: 'Q4 2026', title: 'Native Mobile Apps', status: 'Planned' },
  { quarter: 'Q1 2027', title: 'Advanced BI Suite', status: 'Planned' },
];

export const COMPARISON_ROWS = [
  { feature: 'Student Management', basic: true, premium: true, plus: true },
  { feature: 'Finance & Payroll', basic: false, premium: true, plus: true },
  { feature: 'Multi-Campus', basic: false, premium: false, plus: true },
  { feature: 'AI Insights', basic: false, premium: false, plus: true },
  { feature: 'API Access', basic: false, premium: false, plus: true },
  { feature: 'Custom Branding', basic: false, premium: true, plus: true },
];

export const THEME_PRESETS = [
  { name: 'Apex Teal', primary: '#0F766E', secondary: '#FF7F50' },
  { name: 'Royal Blue', primary: '#1E40AF', secondary: '#F59E0B' },
  { name: 'Forest Green', primary: '#166534', secondary: '#EA580C' },
];

export const AWARDS = [
  'ISO 27001 Ready', 'SOC 2 Type II', 'EdTech Africa 2026', 'Cloud Excellence',
];

export const UPDATES = [
  { date: 'Jul 2026', title: 'Granular Role Permissions', desc: 'Sub-module read/write control for 12+ roles.' },
  { date: 'Jun 2026', title: 'Global Search', desc: 'Instant search across students, staff, and modules.' },
  { date: 'May 2026', title: 'Profile Workspaces', desc: 'Self-service profiles with avatar upload.' },
];

export const ONBOARDING_STEPS = [
  'Kickoff call', 'Data migration', 'Staff training', 'Go-live support', '30-day check-in',
];

export const FOOTER_LINKS = {
  product: ['Features', 'Pricing', 'Integrations', 'Roadmap', 'API'],
  company: ['About', 'Careers', 'Press', 'Partners', 'Contact'],
  resources: ['Blog', 'Documentation', 'Help Center', 'Community', 'Status'],
  legal: ['Privacy', 'Terms', 'Security', 'Cookies', 'GDPR'],
};