import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FiBriefcase, FiCalendar, FiLayers, FiStar, FiUsers } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import FeatureGate from '../../components/FeatureGate';

const HR_LINKS = [
  {
    featureKey: 'staff_management',
    path: '/school-admin/hr/staffs',
    label: 'Staffs',
    icon: FiBriefcase,
    description: 'Add employees, assign dashboard roles, and provision portal accounts with work emails.',
    accent: 'primary',
  },
  {
    featureKey: 'hr_departments',
    path: '/school-admin/hr/departments',
    label: 'Departments',
    icon: FiLayers,
    description: 'Organize staff into academic and administrative departments.',
    accent: 'secondary',
  },
  {
    featureKey: 'leave_requests',
    path: '/school-admin/hr/leave',
    label: 'Leave Requests',
    icon: FiCalendar,
    description: 'Review and approve staff leave applications.',
    accent: 'warning',
  },
  {
    featureKey: 'performance_reviews',
    path: '/school-admin/hr/reviews',
    label: 'Performance Reviews',
    icon: FiStar,
    description: 'Track staff performance evaluations and feedback.',
    accent: 'accent',
  },
];

export function HR() {
  return (
    <div>
      <PageHeader
        title="Human Resources"
        subtitle="Staff onboarding, departments, leave, and performance management"
      />

      <div className="row g-3">
        {HR_LINKS.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div className="col-md-6 col-xl-3" key={item.path}>
              <FeatureGate featureKey={item.featureKey}>
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.06 }}
                >
                  <Link to={item.path} className={`hr-hub-card hr-hub-card--${item.accent}`}>
                    <span className="hr-hub-card-icon"><Icon size={22} /></span>
                    <h5 className="fw-bold mb-1">{item.label}</h5>
                    <p className="text-muted small mb-0">{item.description}</p>
                  </Link>
                </motion.div>
              </FeatureGate>
            </div>
          );
        })}
      </div>

      <motion.div
        className="apex-card p-4 mt-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        <div className="d-flex align-items-center gap-2 mb-2">
          <FiUsers className="text-primary" />
          <h6 className="fw-bold mb-0">Staff onboarding</h6>
        </div>
        <p className="text-muted small mb-3">
          Use <strong>Staffs</strong> to add employees with complete profiles, work emails, and automated role assignment.
          Dashboard access respects your subscription plan and Permission Settings.
        </p>
        <Link to="/school-admin/hr/staffs" className="btn btn-outline-primary btn-sm">
          Go to Staffs
        </Link>
      </motion.div>
    </div>
  );
}

export default HR;