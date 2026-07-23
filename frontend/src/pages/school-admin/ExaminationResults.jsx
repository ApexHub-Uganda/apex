import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft, FiAward, FiPrinter } from 'react-icons/fi';
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
import { extractApiError } from '../../utils/notify';

/**
 * Results workspace — view entered marks for classes in scope.
 * Capabilities drive which actions appear; role labels are never shown.
 */
export function ExaminationResults() {
  const { canReadFeature } = usePermissions();
  const featureView = canReadFeature('result_processing')
    || canReadFeature('report_cards')
    || canReadFeature('class_report_cards')
    || canReadFeature('marks_entry');

  const [term, setTerm] = useState('');
  const [schoolClass, setSchoolClass] = useState('');
  const [stream, setStream] = useState('');

  const { data: caps, isLoading: capsLoading } = useQuery({
    queryKey: ['results-capabilities'],
    queryFn: () => academicReportCardsService.capabilities(),
    staleTime: 60_000,
    enabled: Boolean(featureView),
  });

  const canPrint = Boolean(caps?.can_print_report_cards);
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

  const streamOptions = useMemo(() => {
    const c = (classes || []).find((x) => String(x.id) === String(schoolClass));
    return (c?.streams || []).map((s) => ({ value: s.id, label: s.name }));
  }, [classes, schoolClass]);

  const { data: overview, isLoading, isError, error } = useQuery({
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

  const columns = useMemo(() => {
    const cols = [];
    subjects.forEach((sub) => {
      (sub.exams || []).forEach((exam) => {
        cols.push({
          key: exam.id,
          subject: sub.name,
          subjectCode: sub.code,
          examName: exam.name,
          paper: exam.paper,
          maxScore: exam.max_score,
        });
      });
    });
    return cols;
  }, [subjects]);

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

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/examinations" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Examinations
        </Link>
      </div>

      <PageHeader
        title="Results"
        subtitle="View entered marks by term and class. This view is read-only."
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
            {canPrint && (
              <Link to="/school-admin/academics/report-cards" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1">
                <FiPrinter size={14} /> Report cards
              </Link>
            )}
          </div>
        )}
      />

      <div className="apex-card apex-card--responsive p-3 p-md-4 mb-4">
        <div className="row g-3 align-items-end apex-form-grid">
          <div className="col-12 col-sm-6 col-lg-4">
            <label className="form-label small fw-semibold">Term</label>
            <SearchableSelect options={termOptions} value={term} onChange={setTerm} placeholder="Select term…" />
          </div>
          <div className="col-12 col-sm-6 col-lg-4">
            <label className="form-label small fw-semibold">Class</label>
            <SearchableSelect
              options={classOptions}
              value={schoolClass}
              onChange={(v) => { setSchoolClass(v); setStream(''); }}
              placeholder="Select class…"
            />
          </div>
          {streamOptions.length > 0 && (
            <div className="col-12 col-sm-6 col-lg-4">
              <label className="form-label small fw-semibold">Stream (optional)</label>
              <SearchableSelect options={streamOptions} value={stream} onChange={setStream} placeholder="Whole class" allowClear />
            </div>
          )}
        </div>
      </div>

      {!term || !schoolClass ? (
        <div className="apex-card p-5">
          <ModuleEmptyState
            icon={FiAward}
            title="Select term and class"
            message="Choose a term and class to view entered subject marks."
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
      ) : columns.length === 0 ? (
        <div className="apex-card p-5">
          <ModuleEmptyState
            title="No assessments with marks yet"
            message={
              canEnter
                ? 'Enter marks under Marks Entry, then apply a grading scheme under Grade Calculation.'
                : 'No marks have been entered for this class and term yet.'
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
                {overview?.student_count} student(s) · {overview?.exam_count} assessment(s)
              </p>
            </div>
            {canPrint && (
              <Link
                to="/school-admin/academics/report-cards"
                className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1 flex-shrink-0"
              >
                <FiPrinter size={14} /> Report cards
              </Link>
            )}
          </div>
          <div className="apex-sheet-scroll results-matrix-scroll">
            <table className="table table-sm table-hover mb-0 align-middle results-matrix-table">
              <thead className="table-light">
                <tr>
                  <th className="sticky-col">Adm #</th>
                  <th className="sticky-col sticky-col-2">Student</th>
                  {columns.map((col) => (
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
                    {columns.map((col) => {
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
