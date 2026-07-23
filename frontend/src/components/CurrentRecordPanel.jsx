import { FiCalendar, FiClock, FiEdit2, FiInfo, FiTrash2, FiXCircle } from 'react-icons/fi';

function formatDate(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleDateString(undefined, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return value;
  }
}

/**
 * Active year / term / exam-period summary.
 * Edit, end, and delete are only wired when canMutate is true (school admin).
 */
export function CurrentRecordPanel({
  title,
  record,
  lockReason,
  creationLocked = false,
  type = 'academic_year',
  canMutate = false,
  onEdit,
  onEnd,
  onDelete,
  ending = false,
  deleting = false,
}) {
  if (!record) return null;

  const Icon = type === 'term' || type === 'examination_session' ? FiClock : FiCalendar;
  const subtitle = type === 'term' && record.academic_year_name
    ? `${record.academic_year_name}${record.term_number ? ` · Term ${record.term_number}` : ''}`
    : (type === 'examination_session'
      ? [record.academic_year_name, record.term_name, record.status].filter(Boolean).join(' · ')
      : null);

  const endLabel = type === 'examination_session'
    ? 'End exam period'
    : type === 'term'
      ? 'End current term'
      : 'End current year';

  const statusLabel = record.status
    ? String(record.status).replace(/_/g, ' ')
    : (record.is_current ? 'current' : null);

  return (
    <div className="apex-glass border-0 p-3 p-md-4 p-lg-5 mb-4">
      <div className="d-flex align-items-start gap-3">
        <div
          className="d-none d-sm-inline-flex align-items-center justify-content-center rounded-3 flex-shrink-0"
          style={{ width: 48, height: 48, background: 'rgba(37, 99, 235, 0.1)', color: '#2563eb' }}
        >
          <Icon size={22} />
        </div>
        <div className="flex-grow-1 min-w-0">
          <div className="d-flex flex-wrap align-items-start justify-content-between gap-2 mb-1">
            <div className="d-flex flex-wrap align-items-center gap-2 min-w-0">
              <h3 className="fw-bold mb-0 text-break">{title}</h3>
              <span className="badge text-bg-primary-subtle border text-primary">Current</span>
              {statusLabel && (
                <span className="badge text-bg-secondary-subtle border text-capitalize">{statusLabel}</span>
              )}
            </div>
            {canMutate && (
              <div className="d-flex flex-wrap gap-2 w-100 w-sm-auto">
                {typeof onEdit === 'function' && (
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-primary d-inline-flex align-items-center justify-content-center gap-1 flex-grow-1 flex-sm-grow-0"
                    onClick={onEdit}
                  >
                    <FiEdit2 size={14} /> Edit
                  </button>
                )}
                {typeof onEnd === 'function' && (
                  <button
                    type="button"
                    className="btn btn-sm btn-warning d-inline-flex align-items-center justify-content-center gap-1 flex-grow-1 flex-sm-grow-0"
                    onClick={onEnd}
                    disabled={ending}
                  >
                    <FiXCircle size={14} /> {ending ? 'Ending…' : endLabel}
                  </button>
                )}
                {typeof onDelete === 'function' && (
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-danger d-inline-flex align-items-center justify-content-center gap-1 flex-grow-1 flex-sm-grow-0"
                    onClick={onDelete}
                    disabled={deleting}
                  >
                    <FiTrash2 size={14} /> {deleting ? 'Deleting…' : 'Delete'}
                  </button>
                )}
              </div>
            )}
          </div>
          <p className="text-muted small mb-3">
            {canMutate
              ? (type === 'examination_session'
                ? 'Edit details or status, end this exam period, or delete it. Ending unlocks the next period and keeps entered marks.'
                : 'You can edit details, end this period early, or delete it. Ending it unlocks creation of the next one.')
              : (creationLocked
                ? 'This period is still active. A new one can be opened after it ends. School admin (or DoS for exam periods) can edit, end, or delete it.'
                : 'This is the active school record for your team.')}
          </p>

          <div className="row g-3">
            <div className="col-sm-6 col-md-4">
              <div className="small text-muted text-uppercase fw-semibold mb-1">Name</div>
              <div className="fw-semibold">{record.name}</div>
              {subtitle && <div className="small text-muted">{subtitle}</div>}
            </div>
            <div className="col-sm-6 col-md-4">
              <div className="small text-muted text-uppercase fw-semibold mb-1">Starts</div>
              <div>{formatDate(record.start_date)}</div>
            </div>
            <div className="col-sm-6 col-md-4">
              <div className="small text-muted text-uppercase fw-semibold mb-1">Ends</div>
              <div>{formatDate(record.end_date)}</div>
            </div>
          </div>

          {creationLocked && lockReason && !canMutate && (
            <div className="d-flex align-items-start gap-2 mt-4 p-3 rounded-3" style={{ background: 'rgba(37, 99, 235, 0.06)' }}>
              <FiInfo className="text-primary mt-1 flex-shrink-0" />
              <p className="small mb-0 text-muted">{lockReason}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default CurrentRecordPanel;
