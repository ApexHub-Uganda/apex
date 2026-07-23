import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  FiArrowLeft,
  FiAward,
  FiCheck,
  FiDownload,
  FiRotateCcw,
  FiSend,
  FiTrendingUp,
  FiUsers,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import SearchableSelect from '../../components/SearchableSelect';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { ApexLoader } from '../../components/ApexLoader';
import {
  academicCertificatesService,
  examsService,
  marksApprovalService,
  promotionService,
  studentsService,
} from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { alert, extractApiError, notify } from '../../utils/notify';

/**
 * Assessment hub — learner progression (promote / hold / graduate),
 * completion certificates for final-class leavers, plus draft exam publish.
 */
export function Assessments() {
  const queryClient = useQueryClient();
  const { canWriteFeature, canReadFeature } = usePermissions();

  const canPromote = canWriteFeature('student_promotion') || canWriteFeature('dos_workspace');
  const canViewPromotion = canReadFeature('student_promotion')
    || canReadFeature('dos_workspace')
    || canPromote;
  const canPublishExams = canWriteFeature('assessment_management');
  const canViewExams = canReadFeature('assessment_management') || canPublishExams;
  const canCerts = canPromote || canReadFeature('student_management') || canReadFeature('report_cards');

  const [tab, setTab] = useState('promotion');

  // ── Promotion state ─────────────────────────────────────────────
  const [sourceClass, setSourceClass] = useState('');
  const [sourceStream, setSourceStream] = useState('');
  const [targetClass, setTargetClass] = useState('');
  const [targetStream, setTargetStream] = useState('');
  const [targetYear, setTargetYear] = useState('');
  const [preview, setPreview] = useState(null);
  const [batchId, setBatchId] = useState('');
  const [busy, setBusy] = useState(false);
  const [rowActions, setRowActions] = useState({});
  const [issueCertificates, setIssueCertificates] = useState(true);

  // ── Certificates state ──────────────────────────────────────────
  const [certStudentId, setCertStudentId] = useState('');
  const [certReason, setCertReason] = useState('');
  const [certBusy, setCertBusy] = useState(false);

  // ── Draft exams state ───────────────────────────────────────────
  const [selected, setSelected] = useState(new Set());

  const { data: ctx, isLoading: ctxLoading } = useQuery({
    queryKey: ['promotion-context'],
    queryFn: () => promotionService.context(),
    enabled: canViewPromotion && tab === 'promotion',
  });

  const { data: students = [], isLoading: studentsLoading } = useQuery({
    queryKey: ['students', 'assessment-certs'],
    queryFn: () => studentsService.list({ page_size: 500, status: 'graduated' }).catch(async () => {
      // Fallback: list all if status filter unsupported
      try {
        return await studentsService.list({ page_size: 300 });
      } catch {
        return [];
      }
    }),
    enabled: canCerts && tab === 'certificates',
  });

  const { data: exams = [], isLoading: examsLoading, refetch: refetchExams } = useQuery({
    queryKey: ['draft-assessments'],
    queryFn: () => examsService.list({ lifecycle_status: 'draft' }),
    staleTime: 15_000,
    enabled: canViewExams && tab === 'exams',
  });

  const classes = ctx?.classes || [];
  const years = ctx?.academic_years || [];

  const classOptions = useMemo(() => classes.map((c) => ({
    value: c.id,
    label: `${c.name} (${c.code})${c.is_terminal ? ' · Final' : ''}`,
    meta: `${c.academic_year_name || ''} · ${c.active_students} students`
      + (c.suggested_next_class_name ? ` → ${c.suggested_next_class_name}` : '')
      + (c.is_terminal ? ' · Graduate' : ''),
    keywords: `${c.name} ${c.code} ${c.academic_year_name || ''}`,
  })), [classes]);

  const sourceStreams = useMemo(() => {
    const c = classes.find((x) => x.id === sourceClass);
    return (c?.streams || []).map((s) => ({ value: s.id, label: s.name }));
  }, [classes, sourceClass]);

  const targetStreams = useMemo(() => {
    const c = classes.find((x) => x.id === targetClass);
    return (c?.streams || []).map((s) => ({ value: s.id, label: s.name }));
  }, [classes, targetClass]);

  const yearOptions = useMemo(() => years.map((y) => ({
    value: y.id,
    label: y.name + (y.is_current ? ' (current)' : ''),
  })), [years]);

  const sourceMeta = useMemo(
    () => classes.find((c) => c.id === sourceClass) || null,
    [classes, sourceClass],
  );

  // Auto-suggest next class / graduate when source changes
  useEffect(() => {
    if (!sourceMeta) return;
    if (sourceMeta.is_terminal) {
      setTargetClass('');
      return;
    }
    if (sourceMeta.suggested_next_class_id) {
      setTargetClass(sourceMeta.suggested_next_class_id);
    }
  }, [sourceMeta]);

  const studentOptions = useMemo(() => (students || []).map((s) => ({
    value: s.id,
    label: `${s.full_name || `${s.first_name || ''} ${s.last_name || ''}`.trim()} (${s.admission_number || ''})`,
    meta: s.status || s.school_class_name || '',
    keywords: `${s.full_name || ''} ${s.admission_number || ''} ${s.email || ''}`,
  })), [students]);

  const drafts = (exams || []).filter((e) => e.lifecycle_status === 'draft');

  const runPreview = async () => {
    if (!sourceClass) {
      notify.error('Select source class.');
      return;
    }
    setBusy(true);
    try {
      const actions = Object.entries(rowActions).map(([student_id, action]) => ({
        student_id,
        action,
      }));
      const data = await promotionService.preview({
        source_class: sourceClass,
        source_stream: sourceStream || undefined,
        target_class: targetClass || undefined,
        target_stream: targetStream || undefined,
        target_academic_year: targetYear || undefined,
        actions,
      });
      setPreview(data);
      setBatchId(data.batch_id);
      const p = data.preview || {};
      notify.success(
        `Preview ready: ${p.count || 0} learner(s) — promote ${p.promote || 0}, hold ${p.hold || 0}, graduate ${p.graduate || 0}.`,
      );
    } catch (err) {
      notify.error(extractApiError(err, 'Preview failed.'));
    } finally {
      setBusy(false);
    }
  };

  const runCommit = async () => {
    if (!batchId) return;
    const gradCount = preview?.preview?.graduate || 0;
    const confirmed = await alert.confirm({
      title: 'Commit progression?',
      text: gradCount > 0 && issueCertificates
        ? `${gradCount} graduate(s) will be ready for completion certificates. Student class placements will change.`
        : 'Student class placements will change for this batch.',
      confirmText: 'Yes, commit',
      cancelText: 'Cancel',
      icon: 'warning',
    });
    if (!confirmed.isConfirmed) return;
    setBusy(true);
    try {
      const data = await promotionService.commit(batchId, {
        issue_certificates: issueCertificates,
      });
      notify.success(`Progression committed for ${data.applied} learner(s).`);
      setPreview((p) => (p ? { ...p, status: data.status, graduated_student_ids: data.graduated_student_ids } : p));
      await queryClient.invalidateQueries({ queryKey: ['promotion-context'] });
      await queryClient.invalidateQueries({ queryKey: ['students'] });
      if (data.graduated > 0 && issueCertificates) {
        notify.info(`${data.graduated} graduate(s) — download certificates under the Certificates tab.`);
        setTab('certificates');
      }
    } catch (err) {
      notify.error(extractApiError(err, 'Commit failed.'));
    } finally {
      setBusy(false);
    }
  };

  const runUndo = async () => {
    if (!batchId) return;
    const confirmed = await alert.confirm({
      title: 'Undo this promotion?',
      text: 'Only allowed if no new marks exist in the target class for these learners.',
      confirmText: 'Yes, undo',
      cancelText: 'Keep it',
      icon: 'warning',
      danger: true,
    });
    if (!confirmed.isConfirmed) return;
    setBusy(true);
    try {
      await promotionService.undo(batchId);
      notify.success('Promotion undone.');
      setPreview(null);
      setBatchId('');
      await queryClient.invalidateQueries({ queryKey: ['students'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Undo failed.'));
    } finally {
      setBusy(false);
    }
  };

  const downloadCert = async (type) => {
    if (!certStudentId) {
      notify.error('Select a student.');
      return;
    }
    setCertBusy(true);
    try {
      if (type === 'completion') {
        await academicCertificatesService.completion(certStudentId);
      } else if (type === 'leaving') {
        await academicCertificatesService.leaving(certStudentId, { reason: certReason || undefined });
      } else {
        await academicCertificatesService.transcript(certStudentId);
      }
      notify.success('Certificate downloaded.');
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to download certificate.'));
    } finally {
      setCertBusy(false);
    }
  };

  const toggleExam = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const publishSelected = async () => {
    if (!selected.size) {
      notify.warning('Select at least one assessment.');
      return;
    }
    setBusy(true);
    try {
      const result = await marksApprovalService.bulkAction({
        action: 'publish',
        exam_ids: [...selected],
      });
      if (result?.errors?.length) {
        notify.warning(result.message || 'Some assessments could not be published.');
      } else {
        notify.success(result?.message || 'Assessments published for marks entry.');
      }
      setSelected(new Set());
      await queryClient.invalidateQueries({ queryKey: ['draft-assessments'] });
      await refetchExams();
    } catch (err) {
      notify.error(extractApiError(err, 'Publish failed.'));
    } finally {
      setBusy(false);
    }
  };

  const rows = preview?.rows || [];
  const promotionColumns = [
    { key: 'admission_number', label: 'Adm #', accessor: 'admission_number', sortable: true },
    { key: 'full_name', label: 'Student', accessor: 'full_name', sortable: true },
    {
      key: 'from',
      label: 'From',
      render: (r) => `${r.from_class_name || ''}${r.from_stream_name ? ` · ${r.from_stream_name}` : ''}`,
    },
    {
      key: 'action',
      label: 'Action',
      render: (r) => (
        canPromote && preview?.status !== 'committed' ? (
          <select
            className="form-select form-select-sm"
            value={rowActions[r.student_id] || r.action}
            onChange={(e) => setRowActions((prev) => ({ ...prev, [r.student_id]: e.target.value }))}
          >
            <option value="promote">Promote</option>
            <option value="hold">Hold / Repeat</option>
            <option value="graduate">Graduate (final class)</option>
            <option value="skip">Skip</option>
          </select>
        ) : (
          <span className="text-capitalize">{rowActions[r.student_id] || r.action}</span>
        )
      ),
    },
  ];

  const tabs = [
    { id: 'promotion', label: 'Promote & graduate', icon: FiTrendingUp, show: canViewPromotion },
    { id: 'certificates', label: 'Certificates', icon: FiAward, show: canCerts },
    { id: 'exams', label: 'Publish exams', icon: FiSend, show: canViewExams },
  ].filter((t) => t.show);

  useEffect(() => {
    if (tabs.length && !tabs.find((t) => t.id === tab)) {
      setTab(tabs[0].id);
    }
  }, [tabs, tab]);

  if (!tabs.length) {
    return (
      <div className="apex-card p-5">
        <ModuleEmptyState
          title="Assessment unavailable"
          message="You do not have access to learner progression or assessment tools."
        />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/examinations" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Examinations
        </Link>
      </div>

      <PageHeader
        title="Assessment & progression"
        subtitle="Promote learners to the next class, graduate final-class students with certificates, and open draft exams for marks entry."
      />

      <ul className="nav nav-pills flex-wrap gap-2 mb-4">
        {tabs.map((t) => {
          const Icon = t.icon;
          return (
            <li className="nav-item" key={t.id}>
              <button
                type="button"
                className={`nav-link d-inline-flex align-items-center gap-1 ${tab === t.id ? 'active' : ''}`}
                onClick={() => setTab(t.id)}
              >
                <Icon size={14} /> {t.label}
              </button>
            </li>
          );
        })}
      </ul>

      {tab === 'promotion' && (
        !canViewPromotion ? (
          <div className="apex-card p-5">
            <ModuleEmptyState title="Promotion unavailable" message="Student promotion is not enabled for your role." />
          </div>
        ) : ctxLoading ? (
          <div className="py-5 text-center"><ApexLoader label="Loading…" /></div>
        ) : (
          <div className="row g-4">
            <div className="col-lg-4">
              <div className="apex-card p-4">
                <h6 className="fw-semibold mb-1 d-flex align-items-center gap-2">
                  <FiUsers size={16} /> Source class
                </h6>
                <p className="text-muted small mb-3">
                  Final classes (e.g. P7, S4, S6) default to <strong>Graduate</strong> with certificates.
                </p>
                <div className="mb-3">
                  <label className="form-label small">Source class</label>
                  <SearchableSelect
                    options={classOptions}
                    value={sourceClass}
                    onChange={(v) => {
                      setSourceClass(v);
                      setSourceStream('');
                      setPreview(null);
                      setRowActions({});
                    }}
                    placeholder="Search class…"
                  />
                  {sourceMeta?.is_terminal && (
                    <div className="alert alert-warning small mt-2 mb-0 py-2">
                      This looks like a <strong>final / top class</strong>. Learners will graduate by default.
                    </div>
                  )}
                  {sourceMeta?.suggested_next_class_name && !sourceMeta.is_terminal && (
                    <div className="form-text">
                      Suggested next class: <strong>{sourceMeta.suggested_next_class_name}</strong>
                      {sourceMeta.suggested_next_class_code ? ` (${sourceMeta.suggested_next_class_code})` : ''}
                    </div>
                  )}
                </div>
                {sourceStreams.length > 0 && (
                  <div className="mb-3">
                    <label className="form-label small">Source stream (optional)</label>
                    <SearchableSelect options={sourceStreams} value={sourceStream} onChange={setSourceStream} placeholder="All streams" allowClear />
                  </div>
                )}

                <h6 className="fw-semibold mb-3 mt-4">Target (promote)</h6>
                <div className="mb-3">
                  <label className="form-label small">Target academic year</label>
                  <SearchableSelect options={yearOptions} value={targetYear} onChange={setTargetYear} placeholder="Usually next year" allowClear />
                </div>
                <div className="mb-3">
                  <label className="form-label small">Target class</label>
                  <SearchableSelect
                    options={classOptions}
                    value={targetClass}
                    onChange={(v) => { setTargetClass(v); setTargetStream(''); }}
                    placeholder="Auto-suggested when possible"
                    allowClear
                  />
                </div>
                {targetStreams.length > 0 && (
                  <div className="mb-3">
                    <label className="form-label small">Target stream</label>
                    <SearchableSelect options={targetStreams} value={targetStream} onChange={setTargetStream} placeholder="Optional" allowClear />
                  </div>
                )}

                <div className="form-check mb-3">
                  <input
                    type="checkbox"
                    className="form-check-input"
                    id="issueCertificates"
                    checked={issueCertificates}
                    onChange={(e) => setIssueCertificates(e.target.checked)}
                  />
                  <label className="form-check-label small" htmlFor="issueCertificates">
                    Prepare certificates for graduates on commit
                  </label>
                </div>

                {canPromote && (
                  <div className="d-flex flex-wrap gap-2">
                    <button type="button" className="btn btn-outline-primary btn-sm" disabled={busy} onClick={runPreview}>
                      Dry-run preview
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
                      disabled={busy || !batchId || preview?.status === 'committed'}
                      onClick={runCommit}
                    >
                      <FiCheck size={14} /> Commit
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline-secondary btn-sm d-inline-flex align-items-center gap-1"
                      disabled={busy || preview?.status !== 'committed'}
                      onClick={runUndo}
                    >
                      <FiRotateCcw size={14} /> Undo
                    </button>
                  </div>
                )}
                {preview?.preview && (
                  <div className="alert alert-info small mt-3 mb-0">
                    Promote {preview.preview.promote} · Hold {preview.preview.hold} · Graduate {preview.preview.graduate} · Skip {preview.preview.skip}
                    {preview.status === 'committed' && <div className="mt-1 fw-semibold text-success">Committed</div>}
                  </div>
                )}
              </div>
            </div>
            <div className="col-lg-8">
              <div className="apex-card p-4">
                <h6 className="fw-semibold mb-3">Learners in batch</h6>
                <DataTable
                  columns={promotionColumns}
                  data={rows}
                  searchable
                  searchPlaceholder="Search student or admission number…"
                  searchKeys={['admission_number', 'full_name', 'action', 'from_class_name']}
                  emptyState={(
                    <ModuleEmptyState
                      title="No preview yet"
                      message="Select a source class and run dry-run preview. Final classes default to Graduate."
                    />
                  )}
                />
                {Object.keys(rowActions).length > 0 && preview?.status !== 'committed' && (
                  <button type="button" className="btn btn-link btn-sm px-0 mt-2" onClick={runPreview}>
                    Re-preview with per-student actions
                  </button>
                )}
              </div>
            </div>
          </div>
        )
      )}

      {tab === 'certificates' && (
        <div className="row g-4">
          <div className="col-lg-6">
            <div className="apex-card p-4">
              <h6 className="fw-semibold mb-1 d-flex align-items-center gap-2">
                <FiAward size={16} /> Issue certificates
              </h6>
              <p className="text-muted small mb-3">
                Award a <strong>Certificate of Completion</strong> when a learner finishes the school&apos;s top class.
                Leaving certificates and transcripts remain available for transfers and records.
              </p>
              {studentsLoading ? (
                <ApexLoader label="Loading students…" />
              ) : (
                <>
                  <div className="mb-3">
                    <label className="form-label small">Student</label>
                    <SearchableSelect
                      options={studentOptions}
                      value={certStudentId}
                      onChange={setCertStudentId}
                      placeholder="Search by name or admission number…"
                    />
                    <div className="form-text">
                      Tip: graduated learners appear first when available. You can also open any student record.
                    </div>
                  </div>
                  <div className="mb-3">
                    <label className="form-label small">Leaving reason (optional)</label>
                    <input
                      className="form-control form-control-sm"
                      value={certReason}
                      onChange={(e) => setCertReason(e.target.value)}
                      placeholder="e.g. Completed studies / Transfer"
                    />
                  </div>
                  <div className="d-flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
                      disabled={certBusy || !certStudentId}
                      onClick={() => downloadCert('completion')}
                    >
                      <FiDownload size={14} /> Completion certificate
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1"
                      disabled={certBusy || !certStudentId}
                      onClick={() => downloadCert('leaving')}
                    >
                      <FiDownload size={14} /> Leaving certificate
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline-secondary btn-sm d-inline-flex align-items-center gap-1"
                      disabled={certBusy || !certStudentId}
                      onClick={() => downloadCert('transcript')}
                    >
                      <FiDownload size={14} /> Academic transcript
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
          <div className="col-lg-6">
            <div className="apex-card p-4 h-100">
              <h6 className="fw-semibold mb-2">When to issue what</h6>
              <ul className="small text-muted mb-0 ps-3">
                <li className="mb-2">
                  <strong className="text-body">Completion</strong> — learner finished the final class (P7 / S4 / S6 / equivalent).
                </li>
                <li className="mb-2">
                  <strong className="text-body">Leaving / transfer</strong> — mid-pathway exit or transfer to another school.
                </li>
                <li className="mb-2">
                  <strong className="text-body">Transcript</strong> — multi-term academic record from generated report cards.
                </li>
                <li>
                  Use <strong className="text-body">Promote &amp; graduate</strong> first so placements and status stay accurate.
                </li>
              </ul>
              <div className="mt-3">
                <Link to="/school-admin/academics/report-cards" className="btn btn-link btn-sm px-0">
                  Open report cards →
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'exams' && (
        <>
          <PageHeader
            title="Publish draft exams"
            subtitle="Open scheduled draft assessments so teachers can enter marks"
            actions={canPublishExams && (
              <button
                type="button"
                className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
                disabled={busy || !selected.size}
                onClick={publishSelected}
              >
                <FiSend size={14} /> Publish selected
              </button>
            )}
          />
          {examsLoading ? (
            <div className="py-5 text-center"><ApexLoader label="Loading…" /></div>
          ) : drafts.length === 0 ? (
            <div className="apex-card p-5">
              <ModuleEmptyState
                title="No draft assessments"
                message="Schedule exams under Examinations, then publish them here before marks entry."
                actionLabel="Schedule exams"
                actionHref="/school-admin/examinations"
              />
            </div>
          ) : (
            <div className="apex-card p-0 overflow-hidden">
              <div className="apex-sheet-scroll">
                <table className="table table-hover apex-sheet-table align-middle">
                  <thead className="table-light">
                    <tr>
                      {canPublishExams && <th style={{ width: 40 }} />}
                      <th>Name</th>
                      <th>Subject</th>
                      <th>Class</th>
                      <th>Date</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {drafts.map((row) => (
                      <tr key={row.id}>
                        {canPublishExams && (
                          <td>
                            <input
                              type="checkbox"
                              className="form-check-input"
                              checked={selected.has(row.id)}
                              onChange={() => toggleExam(row.id)}
                            />
                          </td>
                        )}
                        <td className="fw-medium">{row.name}</td>
                        <td>{row.subject_name}</td>
                        <td>{row.school_class_name}</td>
                        <td>{row.exam_date}</td>
                        <td>
                          <span className="badge text-bg-secondary-subtle border">{row.lifecycle_status}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default Assessments;
