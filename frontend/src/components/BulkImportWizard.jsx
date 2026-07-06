import { useState } from 'react';
import {
  FiAlertCircle, FiCheck, FiChevronRight, FiDownload, FiUpload, FiX,
} from 'react-icons/fi';
import { Modal } from './Modal';

const STEPS = ['Download template', 'Upload & validate', 'Import'];

export function BulkImportWizard({
  show,
  onHide,
  title = 'Bulk Import',
  description,
  profileNote,
  importService,
  onSuccess,
}) {
  const [step, setStep] = useState(0);
  const [file, setFile] = useState(null);
  const [validation, setValidation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const reset = () => {
    setStep(0);
    setFile(null);
    setValidation(null);
    setLoading(false);
    setError('');
  };

  const handleClose = () => {
    reset();
    onHide();
  };

  const handleDownload = async () => {
    setLoading(true);
    setError('');
    try {
      await importService.downloadTemplate();
      setStep(1);
    } catch {
      setError('Unable to download template. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    try {
      const result = await importService.validate(file);
      setValidation(result);
      setStep(2);
    } catch (err) {
      const msg = err?.response?.data?.message || 'Validation failed. Check your file format.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleCommit = async () => {
    if (!validation?.ready?.length) return;
    setLoading(true);
    setError('');
    try {
      const result = await importService.commit(validation.ready);
      onSuccess?.(result);
      handleClose();
    } catch (err) {
      const msg = err?.response?.data?.message || 'Import failed. Re-validate and try again.';
      setError(msg);
      if (err?.response?.data?.data) {
        setValidation(err.response.data.data);
      }
    } finally {
      setLoading(false);
    }
  };

  const validCount = validation?.valid_count ?? 0;
  const errorCount = validation?.error_count ?? 0;
  const errors = validation?.errors?.filter((e) => e.severity !== 'warning') ?? [];

  return (
    <Modal
      show={show}
      onHide={handleClose}
      title={title}
      size="lg"
      footer={(
        <div className="d-flex w-100 justify-content-between align-items-center">
          <button type="button" className="btn btn-link text-muted" onClick={handleClose}>
            Cancel
          </button>
          <div className="d-flex gap-2">
            {step === 0 && (
              <button type="button" className="btn btn-primary" onClick={handleDownload} disabled={loading}>
                <FiDownload className="me-1" /> Download template
              </button>
            )}
            {step === 1 && (
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleValidate}
                disabled={loading || !file}
              >
                <FiChevronRight className="me-1" /> Validate file
              </button>
            )}
            {step === 2 && validation?.can_commit && (
              <button type="button" className="btn btn-primary" onClick={handleCommit} disabled={loading}>
                <FiCheck className="me-1" /> Import {validCount} record{validCount !== 1 ? 's' : ''}
              </button>
            )}
          </div>
        </div>
      )}
    >
      <div className="bulk-import-wizard">
        <div className="bulk-import-steps mb-4">
          {STEPS.map((label, idx) => (
            <div
              key={label}
              className={`bulk-import-step ${idx === step ? 'is-active' : ''} ${idx < step ? 'is-done' : ''}`}
            >
              <span className="bulk-import-step-num">{idx < step ? <FiCheck size={12} /> : idx + 1}</span>
              <span className="bulk-import-step-label">{label}</span>
            </div>
          ))}
        </div>

        {description && <p className="text-muted small mb-2">{description}</p>}
        {profileNote && (
          <div className="alert alert-info py-2 small mb-3">
            {profileNote}
          </div>
        )}
        {error && <div className="alert alert-danger py-2 small">{error}</div>}

        {step === 0 && (
          <div className="bulk-import-panel">
            <div className="bulk-import-icon-wrap">
              <FiDownload size={28} />
            </div>
            <h6 className="fw-bold mb-2">Get the CSV template</h6>
            <p className="text-muted small mb-0">
              Download a <strong>minimal</strong> template — only essential fields to get records in fast.
              Fill in Excel or Google Sheets, then save as <strong>CSV UTF-8</strong> before uploading.
            </p>
          </div>
        )}

        {step === 1 && (
          <div className="bulk-import-panel">
            <label className="bulk-import-dropzone">
              <input
                type="file"
                accept=".csv,.txt"
                className="d-none"
                onChange={(e) => { setFile(e.target.files?.[0] || null); setError(''); }}
              />
              <FiUpload size={28} className="text-primary mb-2" />
              <div className="fw-medium">{file ? file.name : 'Choose CSV file'}</div>
              <div className="text-muted small">or drag and drop here</div>
            </label>
            {file && (
              <button type="button" className="btn btn-sm btn-outline-secondary mt-2" onClick={() => setFile(null)}>
                <FiX className="me-1" /> Clear
              </button>
            )}
          </div>
        )}

        {step === 2 && validation && (
          <div>
            <div className="row g-3 mb-3">
              <div className="col-4">
                <div className="bulk-import-stat">
                  <div className="bulk-import-stat-value text-success">{validCount}</div>
                  <div className="bulk-import-stat-label">Ready</div>
                </div>
              </div>
              <div className="col-4">
                <div className="bulk-import-stat">
                  <div className="bulk-import-stat-value text-danger">{errorCount}</div>
                  <div className="bulk-import-stat-label">Issues</div>
                </div>
              </div>
              <div className="col-4">
                <div className="bulk-import-stat">
                  <div className="bulk-import-stat-value">{validation.total_rows}</div>
                  <div className="bulk-import-stat-label">Total rows</div>
                </div>
              </div>
            </div>

            {errors.length > 0 && (
              <div className="bulk-import-errors mb-3">
                <div className="d-flex align-items-center gap-2 mb-2 text-danger small fw-medium">
                  <FiAlertCircle /> Fix these before importing
                </div>
                <div className="table-responsive" style={{ maxHeight: 220 }}>
                  <table className="table table-sm table-bordered mb-0">
                    <thead>
                      <tr>
                        <th>Row</th>
                        <th>Field</th>
                        <th>Issue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {errors.slice(0, 50).map((err, i) => (
                        <tr key={`${err.row}-${err.field}-${i}`}>
                          <td>{err.row || '—'}</td>
                          <td><code className="small">{err.field}</code></td>
                          <td className="small">{err.message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {errors.length > 50 && (
                  <div className="text-muted small mt-1">Showing first 50 of {errors.length} issues</div>
                )}
              </div>
            )}

            {validCount > 0 && (
              <div className="alert alert-success py-2 small mb-0">
                <FiCheck className="me-1" />
                {validCount} row{validCount !== 1 ? 's' : ''} passed validation and can be imported.
              </div>
            )}

            {!validation.can_commit && (
              <button type="button" className="btn btn-sm btn-outline-primary mt-3" onClick={() => setStep(1)}>
                Upload corrected file
              </button>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}

export default BulkImportWizard;