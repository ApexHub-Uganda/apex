import { FiClock, FiMail, FiShield } from 'react-icons/fi';
import { useAuth } from '../../hooks/useAuth';
import { useTenant } from '../../hooks/useTenant';

const REGISTRATION_LABELS = {
  trial_email: 'Free trial via email',
  trial_plan: 'Trial plan selected',
  paid: 'Paid subscription',
  pending: 'Registration in progress',
};

export function PendingApproval() {
  const { user } = useAuth();
  const { tenant } = useTenant();

  const registrationType = user?.tenant_registration_type || tenant?.registration_type || 'pending';
  const schoolName = user?.tenant_name || tenant?.name || 'Your school';

  return (
    <div className="d-flex align-items-center justify-content-center" style={{ minHeight: '60vh' }}>
      <div className="apex-card p-5 text-center" style={{ maxWidth: 520 }}>
        <div
          className="rounded-circle d-inline-flex align-items-center justify-content-center mb-4"
          style={{ width: 72, height: 72, background: 'rgba(255, 127, 80, 0.12)', color: 'var(--apex-secondary)' }}
        >
          <FiClock size={36} />
        </div>

        <h4 className="fw-bold mb-2">Awaiting Approval</h4>
        <p className="text-muted mb-4">
          <strong>{schoolName}</strong> is registered but not yet activated.
          A super admin must approve your account before you can access the dashboard.
        </p>

        <div className="text-start d-flex flex-column gap-3 mb-4">
          <div className="d-flex align-items-start gap-2 small">
            <FiShield className="text-muted mt-1 flex-shrink-0" />
            <span>
              Registration type: <strong>{REGISTRATION_LABELS[registrationType] || registrationType}</strong>
            </span>
          </div>
          {registrationType === 'paid' && (
            <div className="d-flex align-items-start gap-2 small">
              <FiMail className="text-muted mt-1 flex-shrink-0" />
              <span>
                Your payment has been recorded. Account activation will follow after super admin verification.
              </span>
            </div>
          )}
          {registrationType === 'trial_email' && (
            <div className="d-flex align-items-start gap-2 small">
              <FiMail className="text-muted mt-1 flex-shrink-0" />
              <span>
                If you contacted support for a free trial, approval will be processed once your request is reviewed.
              </span>
            </div>
          )}
        </div>

        <p className="text-muted small mb-0">
          You&apos;ll receive access automatically once approved. Check back by signing in again later.
        </p>
      </div>
    </div>
  );
}

export default PendingApproval;