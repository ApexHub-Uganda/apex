import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  FiArrowLeft, FiCalendar, FiCheckCircle, FiDownload, FiUsers, FiXCircle,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { PageLoader } from '../../components/ApexLoader';
import { attendanceSessionsHistoryService } from '../../services/moduleService';
import { extractApiError, notify } from '../../utils/notify';

function statusBadge(status) {
  const s = (status || '').toLowerCase();
  if (s === 'present') {
    return <span className="badge text-bg-success-subtle border text-success">Present</span>;
  }
  if (s === 'absent') {
    return <span className="badge text-bg-danger-subtle border text-danger">Absent</span>;
  }
  if (s === 'late') {
    return <span className="badge text-bg-warning-subtle border text-warning">Late</span>;
  }
  if (s === 'excused') {
    return <span className="badge text-bg-info-subtle border text-info">Excused</span>;
  }
  return <span className="badge text-bg-secondary-subtle border">{status || '—'}</span>;
}

function formatDate(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleDateString(undefined, {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return value;
  }
}

function SummaryChips({ session }) {
  return (
    <div className="d-flex flex-wrap gap-2 small">
      <span className="badge text-bg-success-subtle border text-success">
        <FiCheckCircle className="me-1" size={12} />
        {session.present_count ?? 0} present
      </span>
      <span className="badge text-bg-danger-subtle border text-danger">
        <FiXCircle className="me-1" size={12} />
        {session.absent_count ?? 0} absent
      </span>
      {(session.late_count || 0) > 0 && (
        <span className="badge text-bg-warning-subtle border text-warning">
          {session.late_count} late
        </span>
      )}
      {(session.excused_count || 0) > 0 && (
        <span className="badge text-bg-info-subtle border text-info">
          {session.excused_count} excused
        </span>
      )}
      <span className="text-muted">
        {session.marked_count ?? session.total_count ?? 0} marked
      </span>
    </div>
  );
}

export function AttendanceSessions() {
  const [selectedId, setSelectedId] = useState('');
  const [printing, setPrinting] = useState(false);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['attendance-sessions-recent'],
    queryFn: () => attendanceSessionsHistoryService.recent({ limit: 50, days: 90 }),
    staleTime: 30_000,
  });

  const sessions = data?.results || [];

  const {
    data: detail,
    isLoading: detailLoading,
    isError: detailError,
    error: detailErr,
  } = useQuery({
    queryKey: ['attendance-session-detail', selectedId],
    queryFn: () => attendanceSessionsHistoryService.detail(selectedId),
    enabled: Boolean(selectedId),
    staleTime: 15_000,
  });

  const selectedSummary = useMemo(
    () => sessions.find((s) => s.id === selectedId) || null,
    [sessions, selectedId],
  );

  const handlePrint = async () => {
    if (!selectedId) return;
    setPrinting(true);
    try {
      await attendanceSessionsHistoryService.pdf(selectedId);
      notify.success('Attendance PDF downloaded.');
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to print attendance session.'));
    } finally {
      setPrinting(false);
    }
  };

  if (selectedId) {
    return (
      <div>
        <div className="mb-3 d-flex flex-wrap gap-2 align-items-center justify-content-between">
          <button
            type="button"
            className="btn btn-link btn-sm text-decoration-none text-muted p-0"
            onClick={() => setSelectedId('')}
          >
            <FiArrowLeft className="me-1" /> All sessions
          </button>
          <button
            type="button"
            className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1"
            onClick={handlePrint}
            disabled={printing || detailLoading}
          >
            <FiDownload size={14} /> {printing ? 'Preparing…' : 'Print PDF'}
          </button>
        </div>

        <PageHeader
          title={detail?.title || selectedSummary?.title || 'Attendance session'}
          subtitle={
            [
              detail?.school_class_name || selectedSummary?.school_class_name,
              detail?.subject_name || selectedSummary?.subject_name,
              formatDate(detail?.date || selectedSummary?.date),
              (detail?.teacher_name || selectedSummary?.teacher_name)
                ? `Taken by ${detail?.teacher_name || selectedSummary?.teacher_name}`
                : null,
            ].filter(Boolean).join(' · ')
          }
        />

        {detailLoading ? (
          <PageLoader label="Loading roster…" />
        ) : detailError ? (
          <div className="alert alert-danger">
            {extractApiError(detailErr, 'Unable to load this session.')}
          </div>
        ) : (
          <>
            <div className="apex-card p-3 p-md-4 mb-4">
              <SummaryChips session={detail || selectedSummary || {}} />
              {detail?.topic ? (
                <p className="small text-muted mb-0 mt-2">Topic: {detail.topic}</p>
              ) : null}
            </div>

            <div className="row g-3 mb-4">
              <div className="col-12 col-md-6">
                <div className="apex-card p-3 h-100 border-start border-3 border-success">
                  <div className="fw-semibold mb-2 d-flex align-items-center gap-2">
                    <FiCheckCircle className="text-success" /> Present ({detail?.present?.length || 0})
                  </div>
                  {(detail?.present || []).length === 0 ? (
                    <p className="small text-muted mb-0">No students marked present.</p>
                  ) : (
                    <ul className="list-unstyled mb-0 small">
                      {detail.present.map((r) => (
                        <li key={r.student_id} className="py-1 border-bottom">
                          <span className="fw-medium">{r.full_name}</span>
                          <span className="text-muted ms-2">{r.admission_number}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
              <div className="col-12 col-md-6">
                <div className="apex-card p-3 h-100 border-start border-3 border-danger">
                  <div className="fw-semibold mb-2 d-flex align-items-center gap-2">
                    <FiXCircle className="text-danger" /> Absent ({detail?.absent?.length || 0})
                  </div>
                  {(detail?.absent || []).length === 0 ? (
                    <p className="small text-muted mb-0">No students marked absent.</p>
                  ) : (
                    <ul className="list-unstyled mb-0 small">
                      {detail.absent.map((r) => (
                        <li key={r.student_id} className="py-1 border-bottom">
                          <span className="fw-medium">{r.full_name}</span>
                          <span className="text-muted ms-2">{r.admission_number}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>

            <div className="apex-card p-0 overflow-hidden">
              <div className="p-3 border-bottom bg-light-subtle d-flex justify-content-between align-items-center flex-wrap gap-2">
                <h6 className="fw-semibold mb-0">Full roster</h6>
                <button
                  type="button"
                  className="btn btn-sm btn-primary d-inline-flex align-items-center gap-1"
                  onClick={handlePrint}
                  disabled={printing}
                >
                  <FiDownload size={14} /> Print
                </button>
              </div>
              <div className="apex-sheet-scroll">
                <table className="table table-hover apex-sheet-table align-middle mb-0">
                  <thead className="table-light">
                    <tr>
                      <th>#</th>
                      <th>Adm #</th>
                      <th className="apex-sheet-col-student">Student</th>
                      <th>Stream</th>
                      <th>Status</th>
                      <th className="apex-sheet-col-remarks">Remarks</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(detail?.roster || []).length === 0 ? (
                      <tr>
                        <td colSpan={6} className="text-center text-muted py-4">
                          No student rows for this session.
                        </td>
                      </tr>
                    ) : (
                      detail.roster.map((row, idx) => (
                        <tr key={row.student_id}>
                          <td className="text-muted">{idx + 1}</td>
                          <td className="small text-muted">{row.admission_number || '—'}</td>
                          <td className="fw-medium apex-sheet-col-student">{row.full_name}</td>
                          <td className="small">{row.stream_name || '—'}</td>
                          <td>{statusBadge(row.status)}</td>
                          <td className="small text-muted apex-sheet-col-remarks">{row.remarks || '—'}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/attendance" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Attendance
        </Link>
      </div>

      <PageHeader
        title="Attendance sessions"
        subtitle="Recent class and lesson attendance rolls — open any session for the full present/absent list and print."
        actions={(
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => refetch()}>
            Refresh
          </button>
        )}
      />

      {isLoading ? (
        <PageLoader label="Loading recent attendance…" />
      ) : isError ? (
        <div className="alert alert-danger">
          {extractApiError(error, 'Unable to load attendance sessions.')}
        </div>
      ) : sessions.length === 0 ? (
        <div className="apex-card p-5">
          <ModuleEmptyState
            icon={FiCalendar}
            title="No attendance taken yet"
            message="When teachers mark class or lesson attendance, those sessions appear here with present and absent counts."
            actionLabel="Mark class attendance"
            actionHref="/school-admin/attendance"
          />
        </div>
      ) : (
        <div className="d-flex flex-column gap-3">
          {sessions.map((session) => (
            <button
              key={session.id}
              type="button"
              className="apex-card p-3 p-md-4 text-start border-0 w-100 attendance-session-card"
              onClick={() => setSelectedId(session.id)}
              style={{ cursor: 'pointer' }}
            >
              <div className="d-flex flex-wrap justify-content-between gap-2 align-items-start">
                <div className="min-w-0">
                  <div className="d-flex flex-wrap align-items-center gap-2 mb-1">
                    <span className="fw-semibold text-break">
                      {session.session_type === 'lesson'
                        ? (session.subject_name || 'Lesson')
                        : 'Class attendance'}
                    </span>
                    <span className="badge text-bg-secondary-subtle border">
                      {session.session_type === 'lesson' ? 'Lesson' : 'Class day'}
                    </span>
                  </div>
                  <div className="small text-muted text-break">
                    <FiUsers className="me-1" size={12} />
                    {session.school_class_name || session.subtitle || '—'}
                    {' · '}
                    <FiCalendar className="me-1" size={12} />
                    {formatDate(session.date)}
                    {session.teacher_name ? ` · ${session.teacher_name}` : ''}
                  </div>
                </div>
                <span className="small text-primary flex-shrink-0">View roster →</span>
              </div>
              <div className="mt-3">
                <SummaryChips session={session} />
              </div>
            </button>
          ))}
        </div>
      )}

      <style>{`
        .attendance-session-card {
          transition: box-shadow 0.15s ease, transform 0.15s ease, border-color 0.15s ease;
          border: 1px solid var(--apex-border, #e2e8f0) !important;
          background: var(--apex-surface, #fff);
        }
        .attendance-session-card:hover {
          box-shadow: 0 6px 20px rgba(15, 23, 42, 0.08);
          transform: translateY(-1px);
          border-color: color-mix(in srgb, var(--apex-primary, #0f766e) 35%, var(--apex-border, #e2e8f0)) !important;
        }
      `}</style>
    </div>
  );
}

export default AttendanceSessions;
