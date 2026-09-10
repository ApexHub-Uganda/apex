import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiAward, FiFileText, FiPrinter, FiSend } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import SearchableSelect from '../../components/SearchableSelect';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { PageLoader } from '../../components/ApexLoader';
import {
  academicReportCardsService,
  classResultsService,
  classesService,
  termsService,
} from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { alert, extractApiError, notify } from '../../utils/notify';

/**
 * Results Processing — live class marks matrix + publish pipeline.
 *
 * Until published, data here is "results" only.
 * After publish, the same work becomes report cards on Report Cards / parent portal.
 */
export function ExaminationResults() {
  const queryClient = useQueryClient();
  const { canReadFeature } = usePermissions();
  const featureView = canReadFeature('result_processing')
    || canReadFeature('report_cards')
    || canReadFeature('class_report_cards')
    || canReadFeature('marks_entry')
    || canReadFeature('marks_approval');

  const [term, setTerm] = useState('');
  const [schoolClass, setSchoolClass] = useState('');
  const [stream, setStream] = useState('');
  const [showExamDetail, setShowExamDetail] = useState(false);
  const [busy, setBusy] = useState(false);
  const [autoPicked, setAutoPicked] = useState({ term: false, class: false });

  const { data: caps, isLoading: capsLoading } = useQuery({
    queryKey: ['results-capabilities'],
    queryFn: () => academicReportCardsService.capabilities(),
    staleTime: 60_000,
    enabled: Boolean(featureView),
  });

  const canPrint = Boolean(caps?.can_print_report_cards || caps?.is_dos || caps?.is_school_admin);
  const canEnter = Boolean(caps?.can_enter_marks);
  const canView = featureView || canEnter || canPrint || Boolean(caps?.is_class_teacher);

  const { data: terms = [] } = useQuery({
    queryKey: ['terms', 'results-workspace'],
    queryFn: () => termsService.list({ page_size: 50 }),
    enabled: Boolean(canView),
  });
  const { data: classes = [] } = useQuery({
    queryKey: ['classes', 'results-workspace'],
    queryFn: () => classesService.list({ page_size: 200 }),
    enabled: Boolean(canView),
  });

  const classOptions = useMemo(() => {
    let list = classes || [];
    if (caps && !caps.can_read_all_classes) {
      const allowed = new Set([
        ...(caps.headed_class_ids || []),
        ...(caps.taught_class_ids || []),
      ]);
      if (allowed.size) {
        list = list.filter((c) => allowed.has(String(c.id)));
      }
    }
    // Prefer headed classes first for class teachers
    if (caps?.headed_class_ids?.length) {
      const headed = new Set(caps.headed_class_ids.map(String));
      list = [...list].sort((a, b) => {
        const ah = headed.has(String(a.id)) ? 0 : 1;
        const bh = headed.has(String(b.id)) ? 0 : 1;
        return ah - bh;
      });
    }
    return list.map((c) => ({
      value: c.id,
      label: `${c.name}${c.code ? ` (${c.code})` : ''}`,
    }));
  }, [classes, caps]);

  const termOptions = useMemo(() => (terms || []).map((t) => ({
    value: t.id,
    label: t.name,
    meta: t.is_current ? 'Current' : (t.academic_year_name || undefined),
  })), [terms]);

  // Auto-select current term and first in-scope class so the matrix appears without extra clicks
  useEffect(() => {
    if (autoPicked.term || term || !termOptions.length) return;
    const current = termOptions.find((t) => {
      const raw = (terms || []).find((x) => String(x.id) === String(t.value));
      return raw?.is_current;
    });
    setTerm(String(current?.value || termOptions[0].value));
    setAutoPicked((p) => ({ ...p, term: true }));
  }, [termOptions, terms, term, autoPicked.term]);

  useEffect(() => {
    if (autoPicked.class || schoolClass || !classOptions.length) return;
    // Prefer a headed class when the user is a class teacher
    const headed = new Set((caps?.headed_class_ids || []).map(String));
    const preferred = classOptions.find((c) => headed.has(String(c.value))) || classOptions[0];
    setSchoolClass(String(preferred.value));
    setAutoPicked((p) => ({ ...p, class: true }));
  }, [classOptions, schoolClass, autoPicked.class, caps]);

  const streamOptions = useMemo(() => {
    const c = (classes || []).find((x) => String(x.id) === String(schoolClass));
    return (c?.streams || []).map((s) => ({ value: s.id, label: s.name }));
  }, [classes, schoolClass]);

  const { data: overview, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['class-results-overview', term, schoolClass, stream],
    queryFn: () => classResultsService.overview({
      term,
      school_class: schoolClass,
      stream: stream || undefined,
    }),
    enabled: Boolean(canView && term && schoolClass),
  });

  const subjects = overview?.subjects || [];
  const students = overview?.students || [];
  const pipeline = overview?.report_pipeline || {};
  const showPublishPanel = Boolean(
    term && schoolClass && (canPrint || pipeline.can_print || pipeline.can_generate || pipeline.can_publish),
  );

  const examColumns = useMemo(() => {
    const cols = [];
    subjects.forEach((sub) => {
      (sub.exams || []).forEach((exam) => {
        cols.push({
          key: exam.id,
          subjectId: sub.id,
          subject: sub.name,
          subjectCode: sub.code,
          examName: exam.name,
          paper: exam.paper,
          maxScore: exam.max_score,
          marksStatus: exam.marks_status,
          canEdit: Boolean(exam.can_edit || sub.can_edit),
        });
      });
    });
    return cols;
  }, [subjects]);

  const scoredStudentCount = useMemo(() => {
    return students.filter((s) => s.average != null && s.average !== '').length;
  }, [students]);

  const generateAndRefresh = async () => {
    if (!term || !schoolClass) {
      notify.warning('Select term and class first.');
      return;
    }
    if (!pipeline.can_generate && !(canPrint && students.length)) {
      notify.warning(
        pipeline.approved_exam_count === 0
          ? 'No approved assessments yet. Approve marks before generating report cards.'
          : 'You cannot generate report cards for this class.',
      );
      return;
    }
    const confirmed = await alert.confirm({
      title: 'Generate report cards from results?',
      text: 'Creates draft report cards from approved marks. They stay as drafts (results only) until you publish — parents will not see them yet.',
      confirmText: 'Generate drafts',
      cancelText: 'Cancel',
      icon: 'question',
    });
    if (!confirmed.isConfirmed) return;
    setBusy(true);
    try {
      const data = await academicReportCardsService.generate({
        term,
        school_class: schoolClass,
        stream: stream || undefined,
      });
      notify.success(`Generated ${data?.count ?? 0} draft report card(s). Publish when ready.`);
      await refetch();
      await queryClient.invalidateQueries({ queryKey: ['report-cards-latest'] });
      await queryClient.invalidateQueries({ queryKey: ['report-cards'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Could not generate report cards.'));
    } finally {
      setBusy(false);
    }
  };

  const publishResults = async () => {
    if (!term || !schoolClass) return;
    if (!pipeline.can_publish && !(pipeline.draft_count > 0) && (pipeline.total_cards || 0) > 0) {
      if (pipeline.published_count > 0 && pipeline.draft_count === 0) {
        notify.info('All report cards for this selection are already published.');
        return;
      }
    }
    if ((pipeline.total_cards || 0) === 0 && !pipeline.can_generate && !(canPrint && (pipeline.approved_exam_count || 0) > 0)) {
      notify.warning(
        (pipeline.approved_exam_count || 0) === 0
          ? 'Approve at least one assessment’s marks, then generate and publish.'
          : 'Generate draft report cards from results first, then publish.',
      );
      return;
    }
    const confirmed = await alert.confirm({
      title: 'Publish as report cards?',
      text: 'Published report cards appear on the Report Cards workspace and for parents (subject to fee clearance). Until then they remain internal results only.',
      confirmText: 'Yes, publish',
      cancelText: 'Cancel',
      icon: 'question',
    });
    if (!confirmed.isConfirmed) return;
    setBusy(true);
    try {
      // Generate first if none exist but we can generate
      if ((pipeline.total_cards || 0) === 0 && (pipeline.can_generate || canPrint)) {
        await academicReportCardsService.generate({
          term,
          school_class: schoolClass,
          stream: stream || undefined,
        });
      }
      const data = await academicReportCardsService.publish({
        term,
        school_class: schoolClass,
        stream: stream || undefined,
      });
      notify.success(
        `Published ${data?.published ?? 0} report card(s). They now appear under Report Cards and the parent portal.`,
      );
      await refetch();
      await queryClient.invalidateQueries({ queryKey: ['report-cards-latest'] });
      await queryClient.invalidateQueries({ queryKey: ['report-cards'] });
      await queryClient.invalidateQueries({ queryKey: ['parent-portal-academics'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Publish failed.'));
    } finally {
      setBusy(false);
    }
  };

  if (!canView && !capsLoading) {
    return (
      <div className="apex-card p-5">
        <ModuleEmptyState
          title="Results unavailable"
          message="You do not have access to examination results for any class."
        />
      </div>
    );
  }

  const visibilityNote = overview?.visibility?.approved_only_for_other_subjects
    ? 'Other subjects appear only after their marks are approved. You can edit scores only for subjects assigned to you.'
    : 'Live results matrix. Generate draft report cards, then publish when parents should see them.';

  const pipelineBadge = (() => {
    const st = pipeline.status || 'none';
    if (st === 'published') {
      return <span className="badge text-bg-success-subtle border text-success">Published report cards</span>;
    }
    if (st === 'draft') {
      return <span className="badge text-bg-warning-subtle border text-warning">Draft (results only)</span>;
    }
    if (st === 'partial') {
      return <span className="badge text-bg-info-subtle border text-info">Partially published</span>;
    }
    return <span className="badge text-bg-secondary-subtle border text-secondary">Results only</span>;
  })();

  const publishDisabled = busy || isLoading
    || (
      !pipeline.can_publish
      && (pipeline.draft_count || 0) === 0
      && !((pipeline.total_cards || 0) === 0 && (pipeline.can_generate || (canPrint && (pipeline.approved_exam_count || 0) > 0)))
    );

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/examinations" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Examinations
        </Link>
      </div>

      <PageHeader
        title="Results processing"
        subtitle="View class marks and averages. Publish here to turn results into report cards for parents and the Report Cards module."
        actions={(
          <div className="d-flex flex-wrap gap-2">
            {canEnter && (
              <Link to="/school-admin/examinations/marks" className="btn btn-outline-primary btn-sm">
                Marks entry
              </Link>
            )}
            {canEnter && (
              <Link to="/school-admin/examinations/grades" className="btn btn-outline-primary btn-sm">
                Grade calculation
              </Link>
            )}
            {(canPrint || canReadFeature('report_cards') || canReadFeature('class_report_cards')) && (
              <Link to="/school-admin/academics/report-cards" className="btn btn-outline-secondary btn-sm d-inline-flex align-items-center gap-1">
                <FiPrinter size={14} /> Report cards
              </Link>
            )}
          </div>
        )}
      />

      <div className="apex-card apex-card--responsive p-3 p-md-4 mb-4">
        <div className="row g-3 align-items-end apex-form-grid">
          <div className="col-12 col-sm-6 col-lg-3">
            <label className="form-label small fw-semibold">Term</label>
            <SearchableSelect options={termOptions} value={term} onChange={setTerm} placeholder="Select term…" />
          </div>
          <div className="col-12 col-sm-6 col-lg-3">
            <label className="form-label small fw-semibold">Class</label>
            <SearchableSelect
              options={classOptions}
              value={schoolClass}
              onChange={(v) => { setSchoolClass(v); setStream(''); }}
              placeholder="Select class…"
            />
          </div>
          {streamOptions.length > 0 && (
            <div className="col-12 col-sm-6 col-lg-3">
              <label className="form-label small fw-semibold">Stream (optional)</label>
              <SearchableSelect options={streamOptions} value={stream} onChange={setStream} placeholder="Whole class" allowClear />
            </div>
          )}
          <div className="col-12 col-sm-6 col-lg-3">
            <div className="form-check form-switch mt-4">
              <input
                type="checkbox"
                className="form-check-input"
                id="showExamDetail"
                checked={showExamDetail}
                onChange={(e) => setShowExamDetail(e.target.checked)}
              />
              <label className="form-check-label small" htmlFor="showExamDetail">
                Show per-exam columns
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Publish pipeline — primary place to turn results into report cards */}
      {showPublishPanel && (
        <div className="apex-card p-3 p-md-4 mb-4 border-start border-4 border-primary">
          <div className="d-flex flex-wrap justify-content-between align-items-start gap-3">
            <div className="min-w-0">
              <h6 className="fw-semibold mb-1 d-flex flex-wrap align-items-center gap-2">
                Publish results as report cards
                {pipelineBadge}
              </h6>
              <p className="text-muted small mb-1">
                {pipeline.label
                  || 'Results stay internal until you generate and publish report cards.'}
              </p>
              <p className="small mb-0">
                <span className="text-muted">Draft (results only):</span>{' '}
                <strong>{pipeline.draft_count ?? 0}</strong>
                <span className="text-muted ms-3">Published report cards:</span>{' '}
                <strong>{pipeline.published_count ?? 0}</strong>
                <span className="text-muted ms-3">Approved assessments:</span>{' '}
                <strong>{pipeline.approved_exam_count ?? 0}</strong>
                {students.length > 0 && (
                  <>
                    <span className="text-muted ms-3">Students with averages:</span>{' '}
                    <strong>{scoredStudentCount}/{students.length}</strong>
                  </>
                )}
              </p>
            </div>
            <div className="d-flex flex-wrap gap-2">
              <button
                type="button"
                className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1"
                disabled={busy || isLoading || ((pipeline.approved_exam_count || 0) === 0 && !pipeline.can_generate)}
                onClick={generateAndRefresh}
                title="Create draft report cards from approved marks (not visible to parents yet)"
              >
                <FiFileText size={14} />
                {busy ? 'Working…' : 'Generate drafts'}
              </button>
              <button
                type="button"
                className="btn btn-success btn-sm d-inline-flex align-items-center gap-1"
                disabled={publishDisabled}
                onClick={publishResults}
                title="Publish so cards appear under Report Cards and for parents"
              >
                <FiSend size={14} />
                {busy ? 'Publishing…' : 'Publish as report cards'}
              </button>
            </div>
          </div>
        </div>
      )}

      {!term || !schoolClass ? (
        <div className="apex-card p-5">
          <ModuleEmptyState
            icon={FiAward}
            title="Select term and class"
            message="Choose a term and class to view subject marks and averages, then publish when ready."
          />
        </div>
      ) : isLoading ? (
        <PageLoader label="Loading class results…" />
      ) : isError ? (
        <div className="alert alert-danger">
          {extractApiError(error, 'Unable to load results for this class.')}
        </div>
      ) : students.length === 0 ? (
        <div className="apex-card p-5">
          <ModuleEmptyState
            title="No students in this selection"
            message="There are no active students for the selected class and stream."
          />
        </div>
      ) : subjects.length === 0 ? (
        <div className="apex-card p-5">
          <ModuleEmptyState
            title="No assessments with marks yet"
            message={
              canEnter
                ? 'Enter marks under Marks Entry, then apply grading under Grade Calculation. Other teachers’ subjects appear once approved.'
                : 'No marks are available for this class and term yet (or none are approved for subjects outside your assignment). Ensure exams are linked to this term and class.'
            }
            actionLabel={canEnter ? 'Go to marks entry' : undefined}
            actionHref={canEnter ? '/school-admin/examinations/marks' : undefined}
          />
        </div>
      ) : (
        <div className="apex-card p-0 overflow-hidden">
          <div className="p-3 p-md-4 border-bottom bg-light-subtle d-flex flex-wrap justify-content-between gap-2 align-items-center">
            <div className="min-w-0">
              <h5 className="fw-bold mb-1 text-break">
                {overview?.school_class?.name} · {overview?.term?.name}
              </h5>
              <p className="text-muted small mb-0">
                {overview?.student_count} student(s) · {subjects.length} subject(s) · {overview?.exam_count} assessment(s)
                {pipeline.status === 'published' ? ' · Report cards published' : ' · Results (not yet report cards)'}
              </p>
              <p className="text-muted small mb-0 mt-1">{visibilityNote}</p>
            </div>
            {(canPrint || canReadFeature('report_cards')) && (
              <Link
                to="/school-admin/academics/report-cards"
                className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1 flex-shrink-0"
              >
                <FiPrinter size={14} /> Open report cards
              </Link>
            )}
          </div>
          <div className="apex-sheet-scroll results-matrix-scroll">
            <table className="table table-sm table-hover mb-0 align-middle results-matrix-table">
              <thead className="table-light">
                <tr>
                  <th className="sticky-col">Adm #</th>
                  <th className="sticky-col sticky-col-2">Student</th>
                  {subjects.map((sub) => (
                    <th key={sub.id} className="text-center" style={{ whiteSpace: 'nowrap', padding: '0.3rem 0.45rem' }}>
                      <div className="small fw-semibold text-nowrap">{sub.code || sub.name}</div>
                      <div className="text-muted text-nowrap" style={{ fontSize: '0.65rem' }}>
                        {sub.can_edit ? 'Your subject' : 'Approved'}
                      </div>
                    </th>
                  ))}
                  <th className="text-center fw-semibold">Average</th>
                  {showExamDetail && examColumns.map((col) => (
                    <th key={col.key} className="text-center" style={{ whiteSpace: 'nowrap', padding: '0.3rem 0.45rem' }}>
                      <div className="small fw-semibold text-nowrap">{col.subjectCode || col.subject}</div>
                      <div className="text-muted text-nowrap" style={{ fontSize: '0.65rem' }}>
                        {col.paper || col.examName}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {students.map((student) => (
                  <tr key={student.id}>
                    <td className="sticky-col text-muted small">{student.admission_number}</td>
                    <td className="sticky-col sticky-col-2 fw-medium text-nowrap">{student.full_name}</td>
                    {subjects.map((sub) => {
                      const total = student.subject_totals?.[sub.id];
                      return (
                        <td key={sub.id} className="text-center font-monospace small">
                          {total?.score != null && total.score !== '' ? (
                            <span title={total.grade || undefined}>
                              {total.score}
                              {total.grade ? (
                                <span className="ms-1 badge text-bg-primary-subtle border text-primary">{total.grade}</span>
                              ) : null}
                            </span>
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                        </td>
                      );
                    })}
                    <td className="text-center font-monospace small fw-semibold">
                      {student.average != null && student.average !== '' ? student.average : <span className="text-muted">—</span>}
                    </td>
                    {showExamDetail && examColumns.map((col) => {
                      const cell = student.marks?.[col.key];
                      return (
                        <td key={col.key} className="text-center font-monospace small">
                          {cell ? (
                            <span title={cell.remarks || undefined}>
                              {cell.score}
                              {cell.grade ? (
                                <span className="ms-1 badge text-bg-primary-subtle border text-primary">{cell.grade}</span>
                              ) : null}
                            </span>
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <style>{`
        .results-matrix-scroll {
          max-width: 100%;
        }
        .results-matrix-table {
          width: max-content;
          max-width: none;
          min-width: 0;
          table-layout: auto;
          border-collapse: separate;
          border-spacing: 0;
        }
        .results-matrix-table th,
        .results-matrix-table td {
          padding: 0.28rem 0.45rem;
          white-space: nowrap;
          overflow: visible;
          max-width: none;
        }
        .results-matrix-table .sticky-col {
          position: sticky;
          left: 0;
          background: var(--apex-surface, var(--bs-body-bg, #fff));
          z-index: 1;
          white-space: nowrap;
          padding-right: 0.55rem;
          box-shadow: 1px 0 0 color-mix(in srgb, var(--apex-border, #e2e8f0) 80%, transparent);
        }
        .results-matrix-table .sticky-col-2 {
          left: 4.25rem;
          white-space: nowrap;
        }
        .results-matrix-table thead .sticky-col {
          z-index: 2;
          background: var(--apex-surface-elevated, var(--bs-tertiary-bg, #f8f9fa));
        }
      `}</style>
    </div>
  );
}

export default ExaminationResults;
