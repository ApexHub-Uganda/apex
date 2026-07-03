import { Link } from 'react-router-dom';
import { FiLock } from 'react-icons/fi';
import { getModuleByKey } from '../../config/schoolModules';

export function AccessDenied({ moduleKey, message }) {
  const module = moduleKey ? getModuleByKey(moduleKey) : null;
  const label = module?.label || moduleKey?.replace(/_/g, ' ') || 'this area';

  return (
    <div className="apex-card p-5 text-center mx-auto" style={{ maxWidth: 520 }}>
      <div className="mb-3">
        <FiLock size={40} className="text-muted" />
      </div>
      <h4 className="fw-bold mb-2">Access restricted</h4>
      <p className="text-muted mb-4">
        {message || `Your role does not have permission to access ${label}. Contact your school admin to update Permission Settings.`}
      </p>
      <Link to="/school-admin" className="btn btn-primary btn-sm">
        Back to dashboard
      </Link>
    </div>
  );
}

export default AccessDenied;