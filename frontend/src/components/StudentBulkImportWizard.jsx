import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  FiAlertCircle, FiCheck, FiChevronRight, FiDownload, FiUpload, FiX,
} from 'react-icons/fi';
import { Modal } from './Modal';
import { studentsService } from '../services/moduleService';

const FULL_STEPS = ['Class & stream', 'Download template', 'Upload & validate', 'Import'];
const LOCKED_STEPS = ['Download template', 'Upload & validate', 'Import'];

export function StudentBulkImportWizard({
  show,
  onHide,
  importService,
  onSuccess,
  presetClassId = '',
  presetStreamId = '',
  presetClassName = '',
  presetStreamName = '',
  presetRequiresStream = false,
  title = 'Import Students',
}) {
  const isClassLocked = Boolean(presetClassId);
  const STEPS = isClassLocked ? LOCKED_STEPS : FULL_STEPS;
  const [step, setStep] = useState(0);
  const [schoolClass, setSchoolClass] = useState(presetClassId || '');
  const [stream, setStream] = useState(presetStreamId || '');
  const [file, setFile] = useState(null);
  const [validation, setValidation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const { data: importContext, isLoading: contextLoading } = useQuery({
    queryKey: ['student-import-context'],
    queryFn: () => studentsService.getImportContext(),
    enabled: show && !isClassLocked,
    staleTime: 60_000,
  });

  const classes = importContext?.classes || [];
  const selectedClass = useMemo(
    () => classes.find((row) => row.id === schoolClass),
    [classes, schoolClass],
  );
  const streams = selectedClass?.streams || [];
  const requiresStream = isClassLocked ? presetRequiresStream : Boolean(selectedClass?.has_streams);

  useEffect(() => {
    if (!show) return;
    if (isClassLocked) {
      setSchoolClass(presetClassId);
      setStream(presetStreamId || '');
      return;
    }
    if (!schoolClass && importContext?.default_class_id) {
      setSchoolClass(importContext.default_class_id);
    }
  }, [show, isClassLocked, presetClassId, presetStreamId, importContext, schoolClass]);

  useEffect(() => {
    if (!show || isClassLocked || stream) return;
    if (importContext?.default_stream_id && importContext?.default_class_id === schoolClass) {
      setStream(importContext.default_stream_id);
    }
  }, [show, isClassLocked, importContext, schoolClass, stream]);

  const importContextPayload = useMemo(() => ({
    school_class: schoolClass || undefined,
    stream: stream || undefined,
  }), [schoolClass, stream]);

  const canProceedFromClassStep = Boolean(
    schoolClass && (!requiresStream || stream),
  );

  const reset = () => {
    setStep(0);
    setSchoolClass(presetClassId || '');
    setStream(presetStreamId || '');
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
      setStep(isClassLocked ? 1 : 2);
    } catch (err) {
      setError(err?.message || 'Unable to download template. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    try {
      const result = await importService.validate(file, importContextPayload);
      setValidation(result);
      setStep(isClassLocked ? 2 : 3);
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
      const result = await importService.commit(validation.ready, importContextPayload);
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
        <div className="d-flex w-100 justify-content-end align-items-center gap-2">
          {!isClassLocked && step === 0 && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setStep(1)}
              disabled={!canProceedFromClassStep || contextLoading}
            >
              Continue <FiChevronRight className="ms-1" />
            </button>
          )}
          {((isClassLocked && step === 0) || (!isClassLocked && step === 1)) && (
            <button type="button" className="btn btn-primary" onClick={handleDownload} disabled={loading}>
              <FiDownload className="me-1" /> Download template
            </button>
          )}
          {((isClassLocked && step === 1) || (!isClassLocked && step === 2)) && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleValidate}
              disabled={loading || !file}
            >
              <FiChevronRight className="me-1" /> Validate file
            </button>
          )}
          {((isClassLocked && step === 2) || (!isClassLocked && step === 3)) && validation?.can_commit && (
            <button type="button" className="btn btn-primary" onClick={handleCommit} disabled={loading}>
              <FiCheck className="me-1" /> Import {validCount} student{validCount !== 1 ? 's' : ''}
            </button>
          )}
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

        <p className="text-muted small mb-2">
          {isClassLocked ? (
            <>
              Import <strong>first name</strong>, <strong>last name</strong>, and <strong>sex</strong> (M or F). Every student will be enrolled in
              {' '}<strong>{presetClassName}</strong>
              {presetStreamName ? (
                <> · stream <strong>{presetStreamName}</strong></>
              ) : null}
              . Complete email, phone, and other details in each profile later.
            </>
          ) : (
            <>
              Import <strong>first name</strong>, <strong>last name</strong>, and <strong>sex</strong> (M or F). Every student is assigned to the class
              {requiresStream ? ' and stream' : ''} you select below — complete other details in each profile later.
            </>
          )}
        </p>
        {!isClassLocked && importContext?.is_class_teacher && (
          <div className="alert alert-info py-2 small mb-3">
            As a class teacher, your assigned class is pre-selected. Choose a stream if your class is divided.
          </div>
        )}
        {error && <div className="alert alert-danger py-2 small">{error}</div>}

        {!isClassLocked && step === 0 && (
          <div className="row g-3">
            <div className="col-md-6">
              <label className="form-label small fw-semibold" htmlFor="import-class">Class</label>
              <select
                id="import-class"
                className="form-select"
                value={schoolClass}
                disabled={contextLoading}
                onChange={(e) => { setSchoolClass(e.target.value); setStream(''); }}
              >
                <option value="">Select class…</option>
                {classes.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name} ({row.code}){row.is_class_teacher ? ' — your class' : ''}
                  </option>
                ))}
              </select>
            </div>
            {requiresStream && (
              <div className="col-md-6">
                <label className="form-label small fw-semibold" htmlFor="import-stream">Stream</label>
                <select
                  id="import-stream"
                  className="form-select"
                  value={stream}
                  onChange={(e) => setStream(e.target.value)}
                >
                  <option value="">Select stream…</option>
                  {streams.map((row) => (
                    <option key={row.id} value={row.id}>{row.name}</option>
                  ))}
                </select>
              </div>
            )}
            {selectedClass && (
              <div className="col-12">
                <div className="small text-muted">
                  Students in this import will be enrolled in
                  {' '}<strong>{selectedClass.name}</strong>
                  {stream ? (
                    <> · stream <strong>{streams.find((row) => row.id === stream)?.name}</strong></>
                  ) : null}
                  . Admission numbers are generated automatically.
                </div>
              </div>
            )}
          </div>
        )}

        {((isClassLocked && step === 0) || (!isClassLocked && step === 1)) && (
          <div className="bulk-import-panel">
            <div className="bulk-import-icon-wrap">
              <FiDownload size={28} />
            </div>
            <h6 className="fw-bold mb-2">Get the minimal Excel template</h6>
            <p className="text-muted small mb-0">
              Three columns: <strong>First Name</strong>, <strong>Last Name</strong>, and <strong>Sex</strong> (M or F).
              Class and stream are chosen in the step before — complete email, phone, and other details in each student profile later.
            </p>
            {(selectedClass || presetClassName) && (
              <div className="mt-3 p-3 rounded-3 border bg-light-subtle small">
                Target: {selectedClass?.name || presetClassName}
                {(stream ? streams.find((row) => row.id === stream)?.name : null) || presetStreamName
                  ? ` · ${(stream ? streams.find((row) => row.id === stream)?.name : null) || presetStreamName}`
                  : ''}
              </div>
            )}
          </div>
        )}

        {((isClassLocked && step === 1) || (!isClassLocked && step === 2)) && (
          <div className="bulk-import-panel">
            <label className="bulk-import-dropzone">
              <input
                type="file"
                accept=".xlsx,.xlsm,.csv,.txt"
                className="d-none"
                onChange={(e) => { setFile(e.target.files?.[0] || null); setError(''); }}
              />
              <FiUpload size={28} className="text-primary mb-2" />
              <div className="fw-medium">{file ? file.name : 'Choose Excel or CSV file'}</div>
              <div className="text-muted small">or drag and drop here</div>
            </label>
            {file && (
              <button type="button" className="btn btn-sm btn-outline-secondary mt-2" onClick={() => setFile(null)}>
                <FiX className="me-1" /> Clear
              </button>
            )}
          </div>
        )}

        {((isClassLocked && step === 2) || (!isClassLocked && step === 3)) && validation && (
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

            {validation.import_context?.school_class_name && (
              <div className="alert alert-light border small mb-3">
                Importing into <strong>{validation.import_context.school_class_name}</strong>
                {validation.import_context.stream_name ? (
                  <> · stream <strong>{validation.import_context.stream_name}</strong></>
                ) : null}
              </div>
            )}

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
              </div>
            )}

            {validCount > 0 && (
              <div className="alert alert-success py-2 small mb-0">
                <FiCheck className="me-1" />
                {validCount} student{validCount !== 1 ? 's' : ''} ready to import with basic profiles.
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}

export default StudentBulkImportWizard;