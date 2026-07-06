import { useEffect, useState } from 'react';
import { FiAlertTriangle, FiTrash2 } from 'react-icons/fi';
import Modal from './Modal';

const STEPS = ['review', 'confirm', 'execute'];

export function SchoolDeleteModal({
  show,
  onHide,
  school,
  preview,
  previewLoading = false,
  onConfirmDelete,
  deleting = false,
}) {
  const [step, setStep] = useState('review');
  const [confirmationName, setConfirmationName] = useState('');
  const [acknowledged, setAcknowledged] = useState(false);

  useEffect(() => {
    if (!show) {
      setStep('review');
      setConfirmationName('');
      setAcknowledged(false);
    }
  }, [show]);

  const requiredName = preview?.confirmation_required || school?.name || '';
  const nameMatches = confirmationName.trim().toLowerCase() === requiredName.trim().toLowerCase();
  const canProceedConfirm = nameMatches && acknowledged;

  const handleNext = () => {
    if (step === 'review') setStep('confirm');
    else if (step === 'confirm' && canProceedConfirm) setStep('execute');
  };

  const handleBack = () => {
    if (step === 'confirm') setStep('review');
    else if (step === 'execute') setStep('confirm');
  };

  const handleDelete = async () => {
    if (!canProceedConfirm) return;
    await onConfirmDelete({
      confirmation_name: confirmationName.trim(),
      acknowledge_permanent: true,
    });
  };

  const stepIndex = STEPS.indexOf(step) + 1;

  return (
    <Modal
      show={show}
      onHide={deleting ? undefined : onHide}
      title="Permanently Delete School"
      size="lg"
      footer={(
        <>
          <span className="text-muted small me-auto">Step {stepIndex} of 3</span>
          {step !== 'review' && !deleting && (
            <button type="button" className="btn btn-outline-secondary" onClick={handleBack}>
              Back
            </button>
          )}
          {step === 'review' && (
            <button
              type="button"
              className="btn btn-danger"
              onClick={handleNext}
              disabled={previewLoading || !preview}
            >
              Continue
            </button>
          )}
          {step === 'confirm' && (
            <button
              type="button"
              className="btn btn-danger"
              onClick={handleNext}
              disabled={!canProceedConfirm}
            >
              Proceed to Final Step
            </button>
          )}
          {step === 'execute' && (
            <button
              type="button"
              className="btn btn-danger"
              onClick={handleDelete}
              disabled={deleting || !canProceedConfirm}
            >
              {deleting ? 'Deleting…' : 'Delete School Permanently'}
            </button>
          )}
        </>
      )}
    >
      <div className="d-flex align-items-center gap-2 mb-3 text-danger">
        <FiAlertTriangle size={20} />
        <span className="fw-semibold">This action is irreversible</span>
      </div>

      {step === 'review' && (
        <div>
          {previewLoading ? (
            <div className="text-center py-4">
              <div className="spinner-border text-danger" role="status" />
              <p className="text-muted small mt-2 mb-0">Analyzing school data…</p>
            </div>
          ) : preview ? (
            <>
              <p className="text-muted small">
                You are about to remove <strong>{school?.name}</strong> ({school?.code}) and all associated records from Apex Hub.
              </p>
              <div className="row g-2 mb-3">
                <div className="col-6 col-md-3">
                  <div className="border rounded-3 p-2 text-center">
                    <div className="fw-bold">{preview.summary?.users ?? 0}</div>
                    <div className="text-muted" style={{ fontSize: '0.7rem' }}>Users</div>
                  </div>
                </div>
                <div className="col-6 col-md-3">
                  <div className="border rounded-3 p-2 text-center">
                    <div className="fw-bold">{preview.summary?.subscriptions ?? 0}</div>
                    <div className="text-muted" style={{ fontSize: '0.7rem' }}>Subscriptions</div>
                  </div>
                </div>
                <div className="col-6 col-md-3">
                  <div className="border rounded-3 p-2 text-center">
                    <div className="fw-bold">{preview.summary?.tenant_records ?? 0}</div>
                    <div className="text-muted" style={{ fontSize: '0.7rem' }}>Records</div>
                  </div>
                </div>
                <div className="col-6 col-md-3">
                  <div className="border rounded-3 p-2 text-center bg-danger-subtle">
                    <div className="fw-bold text-danger">{preview.summary?.grand_total ?? 0}</div>
                    <div className="text-muted" style={{ fontSize: '0.7rem' }}>Total Items</div>
                  </div>
                </div>
              </div>
              <ul className="small text-muted mb-3">
                {(preview.warnings || []).map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
              {(preview.categories || []).length > 0 && (
                <div className="border rounded-3 p-3" style={{ maxHeight: 200, overflowY: 'auto' }}>
                  <div className="small fw-semibold mb-2">Data breakdown</div>
                  {preview.categories.map((cat) => (
                    <div key={cat.name} className="mb-2">
                      <div className="small fw-medium">{cat.name} ({cat.total})</div>
                      <div className="text-muted" style={{ fontSize: '0.72rem' }}>
                        {cat.items.map((item) => `${item.label}: ${item.count}`).join(' · ')}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <p className="text-muted">Unable to load deletion preview.</p>
          )}
        </div>
      )}

      {step === 'confirm' && (
        <div>
          <p className="small text-muted mb-3">
            To confirm deletion, type the exact school name below and acknowledge the consequences.
          </p>
          <label className="form-label fw-medium">
            Type <span className="text-danger">{requiredName}</span> to confirm
          </label>
          <input
            className={`form-control mb-3 ${confirmationName && !nameMatches ? 'is-invalid' : ''}`}
            value={confirmationName}
            onChange={(e) => setConfirmationName(e.target.value)}
            placeholder={requiredName}
            autoComplete="off"
          />
          <div className="form-check">
            <input
              className="form-check-input"
              type="checkbox"
              id="ack-delete"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
            />
            <label className="form-check-label small" htmlFor="ack-delete">
              I understand this will permanently delete all school data and cannot be undone.
            </label>
          </div>
        </div>
      )}

      {step === 'execute' && (
        <div className="text-center py-3">
          <div
            className="d-inline-flex align-items-center justify-content-center rounded-circle mb-3"
            style={{ width: 64, height: 64, background: 'rgba(220, 38, 38, 0.1)' }}
          >
            <FiTrash2 size={28} className="text-danger" />
          </div>
          <h6 className="fw-bold">Final confirmation</h6>
          <p className="text-muted small mb-0">
            Click <strong>Delete School Permanently</strong> to remove
            {' '}<strong>{school?.name}</strong> and {preview?.summary?.grand_total ?? 'all'} associated items.
          </p>
          {deleting && (
            <div className="mt-3">
              <div className="spinner-border spinner-border-sm text-danger" role="status" />
              <span className="small text-muted ms-2">Removing school and associated data…</span>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

export default SchoolDeleteModal;