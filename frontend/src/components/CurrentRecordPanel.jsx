import { FiCalendar, FiClock, FiInfo } from 'react-icons/fi';

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

export function CurrentRecordPanel({
  title,
  record,
  lockReason,
  creationLocked = false,
  type = 'academic_year',
}) {
  if (!record) return null;

  const Icon = type === 'term' || type === 'examination_session' ? FiClock : FiCalendar;
  const subtitle = type === 'term' && record.academic_year_name
    ? `${record.academic_year_name}${record.term_number ? ` · Term ${record.term_number}` : ''}`
    : (type === 'examination_session'
      ? [record.academic_year_name, record.term_name, record.status].filter(Boolean).join(' · ')
      : null);

  return (
    <div className="apex-glass border-0 p-4 p-md-5 mb-4">
      <div className="d-flex align-items-start gap-3">
        <div
          className="d-inline-flex align-items-center justify-content-center rounded-3 flex-shrink-0"
          style={{ width: 48, height: 48, background: 'rgba(37, 99, 235, 0.1)', color: '#2563eb' }}
        >
          <Icon size={22} />
        </div>
        <div className="flex-grow-1">
          <div className="d-flex flex-wrap align-items-center gap-2 mb-1">
            <h3 className="fw-bold mb-0">{title}</h3>
            <span className="badge text-bg-primary-subtle border text-primary">Current</span>
          </div>
          <p className="text-muted small mb-3">
            {creationLocked
              ? 'This period is still active. A new one can be opened after it ends.'
              : 'This is the active school record for your team.'}
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

          {creationLocked && lockReason && (
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