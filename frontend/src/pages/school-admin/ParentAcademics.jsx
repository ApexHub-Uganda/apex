import { useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiAward, FiBookOpen, FiLock } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { parentPortalService } from '../../services/moduleService';
import { ApexLoader } from '../../components/ApexLoader';

const formatPct = (v) => {
  const n = Number(v);
  if (Number.isNaN(n)) return '—';
  return `${n}%`;
};

export function ParentAcademics() {
  const location = useLocation();
  const resultsOnly = location.pathname.includes('/parent/results');
  const [selectedChild, setSelectedChild] = useState('');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['parent-portal-academics', selectedChild],
    queryFn: () => parentPortalService.academics(selectedChild ? { student_id: selectedChild } : {}),
  });

  const children = data?.children || [];
  const active = useMemo(
    () => children.find((c) => c.student?.id === selectedChild) || children[0],
    [children, selectedChild],
  );

  if (isLoading) {
    return (
      <div className="py-5 text-center">
        <ApexLoader label="Loading…" />
      </div>
    );
  }

  if (data?.denied) {
    return (
      <div className="apex-card p-5">
        <ModuleEmptyState
          title={resultsOnly ? 'Results not available' : 'Academics not available'}
          message={data.message || 'Your school has not enabled this view for parents.'}
          icon={resultsOnly ? FiAward : FiBookOpen}
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title={resultsOnly ? 'Results & progress' : 'My children’s academics'}
        subtitle={
          resultsOnly
            ? 'Marks and report cards for your linked learners (unlocked per active-term fee clearance)'
            : 'Timetable, homework, attendance, and progress for learners linked to your account'
        }
      />

      {isError && <div className="alert alert-danger">Unable to load academic information.</div>}

      {children.length === 0 ? (
        <div className="apex-card p-5">
          <ModuleEmptyState
            title="No linked children"
            message="Ask the school to link your parent account to enrolled learners."
          />
        </div>
      ) : (
        <>
          {children.length > 1 && (
            <div className="mb-3">
              <select
                className="form-select form-select-sm"
                style={{ maxWidth: 360 }}
                value={selectedChild || active?.student?.id || ''}
                onChange={(e) => setSelectedChild(e.target.value)}
              >
                {children.map((row) => (
                  <option key={row.student.id} value={row.student.id}>
                    {row.student.full_name} ({row.student.admission_number})
                  </option>
                ))}
              </select>
            </div>
          )}

          {active && (
            <div className="row g-3">
              <div className="col-12">
                <div className="apex-card p-3 p-md-4">
                  <h5 className="fw-semibold mb-1">{active.student.full_name}</h5>
                  <div className="small text-muted">
                    {active.student.admission_number}
                    {active.student.class_name ? ` · ${active.student.class_name}` : ''}
                  </div>
                  {active.fee_clearance && (
                    <div className="mt-2 small">
                      {active.fee_clearance.term_name
                        ? (
                          <>
                            <span className="text-muted">Term:</span>{' '}
                            <strong>{active.fee_clearance.term_name}</strong>
                            <span className="mx-1">·</span>
                          </>
                        )
                        : null}
                      Fee clearance:{' '}
                      <strong>{formatPct(active.fee_clearance.cleared_percent)}</strong>
                      {' '}(required {formatPct(active.fee_clearance.required_percent)})
                      {active.fee_clearance.results_allowed
                        ? <span className="text-success ms-2">Results unlocked</span>
                        : <span className="text-warning ms-2">Results locked</span>}
                      {active.fee_clearance.scope === 'no_active_term' && (
                        <div className="text-warning mt-1">
                          No active academic term — results stay locked until a term is set.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {!resultsOnly && active.sections?.timetable && (
                <div className="col-lg-6">
                  <div className="apex-card p-3 h-100">
                    <h6 className="fw-semibold mb-3">Class timetable</h6>
                    {active.sections.timetable.length === 0 ? (
                      <p className="small text-muted mb-0">No timetable published yet.</p>
                    ) : (
                      <div className="table-responsive">
                        <table className="table table-sm mb-0">
                          <thead><tr><th>Day</th><th>Time</th><th>Subject</th><th>Teacher</th></tr></thead>
                          <tbody>
                            {active.sections.timetable.map((s, i) => (
                              <tr key={i}>
                                <td>{s.day_of_week}</td>
                                <td>{s.start_time}–{s.end_time}</td>
                                <td>{s.subject}</td>
                                <td>{s.teacher || '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {!resultsOnly && active.sections?.homework && (
                <div className="col-lg-6">
                  <div className="apex-card p-3 h-100">
                    <h6 className="fw-semibold mb-3">Homework</h6>
                    {active.sections.homework.length === 0 ? (
                      <p className="small text-muted mb-0">No homework published.</p>
                    ) : (
                      <ul className="list-group list-group-flush">
                        {active.sections.homework.map((h, i) => (
                          <li key={i} className="list-group-item px-0">
                            <div className="fw-medium">{h.title}</div>
                            <div className="small text-muted">{h.subject} · due {h.due_date}</div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )}

              {!resultsOnly && active.sections?.attendance && (
                <div className="col-lg-6">
                  <div className="apex-card p-3 h-100">
                    <h6 className="fw-semibold mb-3">Attendance</h6>
                    <div className="d-flex flex-wrap gap-2 mb-3">
                      {Object.entries(active.sections.attendance.summary || {}).map(([status, count]) => (
                        <span key={status} className="badge text-bg-light border text-capitalize">
                          {status}: {count}
                        </span>
                      ))}
                    </div>
                    <div className="table-responsive">
                      <table className="table table-sm mb-0">
                        <thead><tr><th>Date</th><th>Status</th></tr></thead>
                        <tbody>
                          {(active.sections.attendance.recent || []).map((r, i) => (
                            <tr key={i}><td>{r.date}</td><td className="text-capitalize">{r.status}</td></tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {active.sections?.results && (
                <div className="col-12">
                  <div className="apex-card p-3 p-md-4">
                    <h6 className="fw-semibold mb-3 d-flex align-items-center gap-2">
                      {resultsOnly ? 'Results & progress' : 'Academic progress'}
                      {active.sections.results.locked && <FiLock className="text-warning" />}
                    </h6>
                    {active.sections.results.locked ? (
                      <div className="alert alert-warning mb-0">
                        <strong>Results locked.</strong>{' '}
                        {active.sections.results.message
                          || 'Clear outstanding fees for the active term to the school’s required percentage to view marks and report cards.'}
                      </div>
                    ) : (
                      <div className="row g-3">
                        <div className="col-lg-5">
                          <h6 className="small text-muted text-uppercase">Report cards</h6>
                          {(active.sections.results.report_cards || []).length === 0 ? (
                            <p className="small text-muted">No published report cards yet.</p>
                          ) : (
                            <ul className="list-group list-group-flush">
                              {active.sections.results.report_cards.map((c, i) => (
                                <li key={i} className="list-group-item px-0">
                                  <div className="fw-medium">{c.term} · avg {c.average_score}</div>
                                  <div className="small text-muted">
                                    Rank {c.rank ?? '—'}
                                    {c.teacher_remarks ? ` · ${c.teacher_remarks}` : ''}
                                  </div>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                        <div className="col-lg-7">
                          <h6 className="small text-muted text-uppercase">Recent grades</h6>
                          {(active.sections.results.recent_grades || []).length === 0 ? (
                            <p className="small text-muted">No published grades yet.</p>
                          ) : (
                            <div className="table-responsive">
                              <table className="table table-sm mb-0">
                                <thead><tr><th>Exam</th><th>Subject</th><th>Score</th><th>Grade</th></tr></thead>
                                <tbody>
                                  {active.sections.results.recent_grades.map((g, i) => (
                                    <tr key={i}>
                                      <td>{g.exam}</td>
                                      <td>{g.subject}</td>
                                      <td>{g.score}</td>
                                      <td>{g.grade || '—'}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default ParentAcademics;
