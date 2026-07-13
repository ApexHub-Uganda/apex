import { Link } from 'react-router-dom';
import { FiAlertTriangle } from 'react-icons/fi';

export function IncompleteProfileBanner({ count = 0, className = '' }) {
  if (!count) return null;

  return (
    <div className={`alert alert-warning d-flex align-items-start gap-2 mb-4 ${className}`.trim()}>
      <FiAlertTriangle className="mt-1 flex-shrink-0" />
      <div className="small">
        <strong>{count}</strong> student{count === 1 ? '' : 's'} ha{count === 1 ? 's' : 've'} an incomplete profile
        {' '}(missing date of birth, UPI, parents, or county).
        {' '}Open each record to add the remaining details.
        {' '}
        <Link to="/school-admin/students" className="alert-link">View students</Link>
      </div>
    </div>
  );
}

export default IncompleteProfileBanner;