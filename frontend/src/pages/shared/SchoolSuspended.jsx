import { FiAlertOctagon, FiMail, FiShield } from 'react-icons/fi';
import { useAuth } from '../../hooks/useAuth';
import { useTenant } from '../../hooks/useTenant';

const formatDate = (value) => {
  if (!value) return null;
  return new Date(value).toLocaleString();
};

export function SchoolSuspended() {
  const { user } = useAuth();
  const { tenant } = useTenant();

  const schoolName = tenant?.name || user?.tenant_name || 'Your school';
  const reason = tenant?.suspension_reason?.trim();
  const suspendedAt = formatDate(tenant?.suspended_at);

  return (
    <div className="school-suspended-screen">
      <div className="school-suspended-card apex-card">
        <div className="school-suspended-icon" aria-hidden>
          <FiAlertOctagon size={40} />
        </div>

        <h2 className="school-suspended-title">Account Temporarily Suspended</h2>
        <p className="school-suspended-lead">
          Your school has been temporarily suspended! Contact admin to verify issue.
        </p>

        <div className="school-suspended-meta">
          <div className="school-suspended-meta-item">
            <FiShield size={16} className="flex-shrink-0" />
            <span>
              School: <strong>{schoolName}</strong>
            </span>
          </div>
          {suspendedAt && (
            <div className="school-suspended-meta-item">
              <FiAlertOctagon size={16} className="flex-shrink-0" />
              <span>
                Suspended on <strong>{suspendedAt}</strong>
              </span>
            </div>
          )}
          {reason && (
            <div className="school-suspended-reason">
              <span className="school-suspended-reason-label">Reason provided</span>
              <p>{reason}</p>
            </div>
          )}
          <div className="school-suspended-meta-item">
            <FiMail size={16} className="flex-shrink-0" />
            <span>
              Contact your platform administrator to resolve this suspension and restore access.
            </span>
          </div>
        </div>

        <p className="school-suspended-footnote">
          Dashboard features are disabled until your school is reactivated. You may sign out or
          refresh this page after the issue is resolved.
        </p>
      </div>
    </div>
  );
}

export default SchoolSuspended;