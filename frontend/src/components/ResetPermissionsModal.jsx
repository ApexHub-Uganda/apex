import { useEffect, useState } from 'react';
import { FiAlertTriangle, FiRefreshCw } from 'react-icons/fi';
import Modal from './Modal';

export function ResetPermissionsModal({
  show,
  onHide,
  roleLabel,
  onConfirm,
  resetting = false,
}) {
  const [acknowledged, setAcknowledged] = useState(false);
  const [password, setPassword] = useState('');

  useEffect(() => {
    if (!show) {
      setAcknowledged(false);
      setPassword('');
    }
  }, [show]);

  const canSubmit = acknowledged && password.trim().length > 0;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit || resetting) return;
    await onConfirm({
      acknowledge_risk: true,
      password: password.trim(),
    });
  };

  return (
    <Modal
      show={show}
      onHide={resetting ? undefined : onHide}
      title="Reset role permissions"
      size="md"
      footer={(
        <button
          type="submit"
          form="reset-permissions-form"
          className="btn btn-danger d-inline-flex align-items-center gap-2 ms-auto"
          disabled={!canSubmit || resetting}
        >
          <FiRefreshCw size={14} />
          {resetting ? 'Resetting…' : 'Reset permissions'}
        </button>
      )}
    >
      <form id="reset-permissions-form" onSubmit={handleSubmit}>
        <div className="d-flex align-items-center gap-2 mb-3 text-danger">
          <FiAlertTriangle size={20} />
          <span className="fw-semibold">Critical security action</span>
        </div>

        <p className="text-muted small mb-3">
          You are about to reset permissions for <strong>{roleLabel}</strong> back to system defaults.
          This removes all custom access rules you configured for this role.
        </p>

        <div className="permission-reset-warning mb-4">
          <p className="small fw-semibold mb-2">What this means</p>
          <ul className="small text-muted mb-0 ps-3">
            <li>Users in this role may gain access to modules they could not reach before.</li>
            <li>They may be able to view, change, or delete sensitive school records.</li>
            <li>Financial, academic, and staff operations could become available immediately.</li>
            <li>Changes take effect as soon as users refresh or sign in again.</li>
          </ul>
        </div>

        <div className="form-check mb-4">
          <input
            className="form-check-input"
            type="checkbox"
            id="ack-reset-permissions"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
            disabled={resetting}
          />
          <label className="form-check-label small" htmlFor="ack-reset-permissions">
            I understand this reset can allow users to access and execute risky operations,
            and I accept responsibility for this change.
          </label>
        </div>

        <div>
          <label className="form-label fw-medium small" htmlFor="reset-permissions-password">
            Confirm with your account password
          </label>
          <input
            id="reset-permissions-password"
            type="password"
            className="form-control"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your school admin password"
            autoComplete="current-password"
            disabled={resetting}
            required
          />
          <p className="text-muted small mt-2 mb-0">
            Only a verified school admin password can authorize this reset.
          </p>
        </div>
      </form>
    </Modal>
  );
}

export default ResetPermissionsModal;