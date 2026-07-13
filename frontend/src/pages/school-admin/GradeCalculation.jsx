import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft, FiPercent, FiRefreshCw } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { assignmentGradeService, gradeCalculationService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';

const EXAM_STEPS = [
  { key: 'scheme', label: 'Scheme' },
  { key: 'subject', label: 'Subject' },
  { key: 'paper', label: 'Paper' },
  { key: 'class', label: 'Class' },
  { key: 'term', label: 'Term' },
  { key: 'exam', label: 'Assessment' },
  { key: 'results', label: 'Results' },
];

const ASSIGNMENT_STEPS = [
  { key: 'scheme', label: 'Scheme' },
  { key: 'subject', label: 'Subject' },
  { key: 'paper', label: 'Paper' },
  { key: 'class', label: 'Class' },
  { key: 'assessment', label: 'Assignment' },
  { key: 'results', label: 'Results' },
];

function examStepIndex(selection, requiresPaper) {
  if (!selection.scheme) return 0;
  if (!selection.subject) return 1;
  if (requiresPaper && !selection.paper && selection.paper !== 'none') return 2;
  if (!selection.school_class) return requiresPaper ? 3 : 2;
  if (!selection.term) return requiresPaper ? 4 : 3;
  if (!selection.exam) return requiresPaper ? 5 : 4;
  return requiresPaper ? 6 : 5;
}

function assignmentStepIndex(selection, requiresPaper) {
  if (!selection.scheme) return 0;
  if (!selection.subject) return 1;
  if (requiresPaper && !selection.paper && selection.paper !== 'none') return 2;
  if (!selection.school_class) return requiresPaper ? 3 : 2;
  if (!selection.assessment) return requiresPaper ? 4 : 3;
  return requiresPaper ? 5 : 4;
}

export function GradeCalculation({ context = 'examinations' }) {
  const { canWriteFeature } = usePermissions();
  const canApply = canWriteFeature('grade_calculation');
  const isAssignments = context === 'assignments';
  const backPath = isAssignments ? '/school-admin/academics/assignments' : '/school-admin/examinations';
  const backLabel = isAssignments ? 'Assignments' : 'Examinations';

  const [selection, setSelection] = useState({
    scheme: '',
    subject: '',
    paper: '',
    school_class: '',
    term: '',
    exam: '',
    assessment: '',
  });
  const [applying, setApplying] = useState(false);
  const [resultRows, setResultRows] = useState([]);

  const optionsParams = useMemo(() => {
    if (isAssignments) {
      return {
        scheme: selection.scheme || undefined,
        subject: selection.subject || undefined,
        paper: selection.paper || undefined,
        school_class: selection.school_class || undefined,
        assessment: selection.assessment || undefined,
      };
    }
    return {
      scheme: selection.scheme || undefined,
      subject: selection.subject || undefined,
      paper: selection.paper || undefined,
      school_class: selection.school_class || undefined,
      term: selection.term || undefined,
      exam: selection.exam || undefined,
    };
  }, [isAssignments, selection]);

  const { data: options, isLoading, isError, refetch } = useQuery({
    queryKey: [isAssignments ? 'assignment-grades-options' : 'grade-calculation-options', optionsParams],
    queryFn: () => (
      isAssignments
        ? assignmentGradeService.getOptions(optionsParams)
        : gradeCalculationService.getOptions(optionsParams)
    ),
    staleTime: 30_000,
  });

  const schemes = options?.schemes || [];
  const subjects = options?.subjects || [];
  const papers = options?.papers || [];
  const requiresPaper = options?.requires_paper || false;
  const classes = options?.classes || [];
  const terms = options?.terms || [];
  const exams = options?.exams || [];
  const assessments = options?.assessments || [];
  const students = options?.students || [];
  const grades = options?.grades || {};
  const examDetail = options?.exam_detail;
  const marksCount = options?.marks_count ?? Object.keys(grades).length;
  const selectedScheme = options?.selected_scheme;
  const scopeMeta = options?.scope_meta;

  const visibleSteps = useMemo(
    () => (isAssignments ? ASSIGNMENT_STEPS : EXAM_STEPS).filter((step) => step.key !== 'paper' || requiresPaper),
    [isAssignments, requiresPaper],
  );
  const activeStep = isAssignments
    ? assignmentStepIndex(selection, requiresPaper)
    : examStepIndex(selection, requiresPaper);

  const activeAssessmentId = isAssignments ? selection.assessment : selection.exam;

  const displayRows = useMemo(() => {
    if (resultRows.length) return resultRows;
    return students.map((student) => {
      const existing = grades[student.id];
      return {
        student_id: student.id,
        student_name: student.full_name,
        admission_number: student.admission_number,
        score: existing?.score ?? '—',
        grade: existing?.grade ?? '—',
        remarks: existing?.remarks ?? '',
        max_score: examDetail?.max_score ?? '',
      };
    });
  }, [resultRows, students, grades, examDetail]);

  const updateSelection = (key, value) => {
    const next = { ...selection, [key]: value };
    if (key === 'scheme') {
      next.subject = '';
      next.paper = '';
      next.school_class = '';
      next.term = '';
      next.exam = '';
      next.assessment = '';
    } else if (key === 'subject') {
      next.paper = '';
      next.school_class = '';
      next.term = '';
      next.exam = '';
      next.assessment = '';
    } else if (key === 'paper') {
      next.school_class = '';
      next.term = '';
      next.exam = '';
      next.assessment = '';
    } else if (key === 'school_class') {
      next.term = '';
      next.exam = '';
      next.assessment = '';
    } else if (key === 'term') {
      next.exam = '';
    }
    setSelection(next);
    setResultRows([]);
  };

  const resetAll = () => {
    setSelection({ scheme: '', subject: '', paper: '', school_class: '', term: '', exam: '', assessment: '' });
    setResultRows([]);
  };

  const handleApply = async () => {
    if (!selection.scheme || !activeAssessmentId) return;
    if (!marksCount) {
      notify.error('No marks entered yet. Enter scores in Marks Entry first.');
      return;
    }
    setApplying(true);
    try {
      const applyService = isAssignments ? assignmentGradeService : gradeCalculationService;
      const result = await applyService.apply({
        scheme: selection.scheme,
        exam: activeAssessmentId,
      });
      notify.success(result?.message || 'Grades calculated.');
      setResultRows(result?.rows || []);
      await refetch();
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to apply grading scheme.'));
    } finally {
      setApplying(false);
    }
  };

  const renderSelect = (id, label, value, items, disabled, required, placeholder) => (
    <div className="col-md-6 col-lg-4" key={id}>
      <label className="form-label small fw-semibold" htmlFor={id}>
        {label}
        {required && <span className="text-danger"> *</span>}
      </label>
      <select
        id={id}
        className="form-select"
        value={value}
        disabled={disabled || (id !== 'scheme' && isLoading)}
        onChange={(e) => updateSelection(id, e.target.value)}
      >
        <option value="">{placeholder || `Select ${label.toLowerCase()}…`}</option>
        {items.map((item) => (
          <option key={item.value} value={item.value}>{item.label}</option>
        ))}
      </select>
    </div>
  );

  const assessmentItems = isAssignments ? assessments : exams.filter((e) => e.has_marks !== false);

  return (
    <div>
      <div className="mb-3">
        <Link to={backPath} className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> {backLabel}
        </Link>
      </div>

      <PageHeader
        title="Grade calculation"
        subtitle={
          isAssignments
            ? 'Choose a grading scheme and assignment with entered marks, then apply letter grades.'
            : 'Choose a grading scheme, your subject and class, then apply it to marks already entered'
        }
        actions={activeAssessmentId && canApply && marksCount > 0 && (
          <button
            type="button"
            className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
            onClick={handleApply}
            disabled={applying}
          >
            <FiPercent size={14} /> {applying ? 'Applying…' : 'Apply grading scheme'}
          </button>
        )}
      />

      <div className="apex-card p-4 mb-4">
        <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
          {visibleSteps.map((step, idx) => (
            <div
              key={step.key}
              className={`marks-entry-step ${idx <= activeStep ? 'marks-entry-step--active' : ''} ${idx === activeStep ? 'marks-entry-step--current' : ''}`}
            >
              <span className="marks-entry-step-num">{idx + 1}</span>
              <span className="small fw-medium">{step.label}</span>
            </div>
          ))}
          {selection.scheme && (
            <button type="button" className="btn btn-link btn-sm text-muted ms-auto p-0" onClick={resetAll}>
              <FiRefreshCw size={14} className="me-1" /> Start over
            </button>
          )}
        </div>

        <div className="row g-3">
          {renderSelect('scheme', 'Grading scheme', selection.scheme, schemes, isLoading && !options, true)}
          {selection.scheme && renderSelect('subject', 'Subject', selection.subject, subjects, false, true)}
          {selection.scheme && selection.subject && requiresPaper && renderSelect(
            'paper',
            'Paper',
            selection.paper,
            papers,
            false,
            false,
            'Whole subject (no paper)',
          )}
          {selection.subject && renderSelect('school_class', 'Class', selection.school_class, classes, false, true)}

          {isAssignments && selection.school_class && renderSelect(
            'assessment',
            'Assignment',
            selection.assessment,
            assessmentItems,
            false,
            true,
            'Select assignment with marks…',
          )}

          {!isAssignments && selection.school_class && renderSelect(
            'term',
            'Term',
            selection.term,
            terms,
            false,
            true,
          )}
          {!isAssignments && selection.term && renderSelect(
            'exam',
            'Assessment',
            selection.exam,
            assessmentItems,
            false,
            true,
            'Select assessment with marks…',
          )}
        </div>

        {scopeMeta?.uses_teaching_assignments && (
          <div className="alert alert-info mt-3 mb-0 small">
            Showing only subjects and classes from your teaching assignments.
          </div>
        )}
        {selection.scheme && schemes.length === 0 && (
          <div className="alert alert-warning mt-3 mb-0 small">
            No grading schemes found.{' '}
            <Link to="/school-admin/academics/grading">Create one under Academics → Grading</Link>.
          </div>
        )}
        {selectedScheme?.bands?.length > 0 && (
          <div className="mt-3 p-3 rounded-3 border bg-light-subtle">
            <div className="small fw-semibold mb-2">{selectedScheme.name} bands</div>
            <div className="subject-assignment-table-chips">
              {selectedScheme.bands.map((band) => (
                <span key={`${band.grade}-${band.min_score}`} className="subject-assignment-table-chip">
                  {band.grade} {band.min_score}–{band.max_score}
                </span>
              ))}
            </div>
          </div>
        )}
        {selection.school_class && !isLoading && assessmentItems.length === 0 && !activeAssessmentId && (
          <div className="alert alert-warning mt-3 mb-0 small">
            {isAssignments
              ? 'No assignments with entered marks match this selection. Enter marks first under Assignments → Marks entry.'
              : 'No assessments with entered marks match this selection. Enter marks first under Examinations → Marks Entry.'}
          </div>
        )}
      </div>

      {isError && (
        <div className="alert alert-danger">Unable to load grade calculation data.</div>
      )}

      {activeAssessmentId && marksCount === 0 && (
        <ModuleEmptyState
          icon={FiPercent}
          title="No marks entered yet"
          message="Enter student scores in Marks Entry, then return here to apply a grading scheme."
          actionLabel="Go to marks entry"
          actionHref={isAssignments ? '/school-admin/academics/assignments/marks' : '/school-admin/examinations/marks'}
        />
      )}

      {activeAssessmentId && marksCount > 0 && (
        <div className="apex-card p-0 overflow-hidden">
          <div className="p-4 border-bottom bg-light-subtle">
            <h5 className="fw-bold mb-1">{examDetail?.name || 'Mark sheet'}</h5>
            <p className="text-muted small mb-0">
              {marksCount} student(s) with scores
              {examDetail?.max_score ? ` · Max ${examDetail.max_score}` : ''}
              {resultRows.length ? ' · Grades applied' : ' · Apply scheme to generate letter grades'}
            </p>
          </div>
          <div className="table-responsive">
            <table className="table table-hover mb-0 align-middle">
              <thead className="table-light">
                <tr>
                  <th>Admission No.</th>
                  <th>Student</th>
                  <th className="text-end">Score</th>
                  <th>Grade</th>
                  <th>Remarks</th>
                </tr>
              </thead>
              <tbody>
                {displayRows.map((row) => (
                  <tr key={row.student_id}>
                    <td className="text-muted small">{row.admission_number || '—'}</td>
                    <td className="fw-medium">{row.student_name}</td>
                    <td className="text-end font-monospace">
                      {row.score}{row.max_score ? ` / ${row.max_score}` : ''}
                    </td>
                    <td>
                      {row.grade && row.grade !== '—' ? (
                        <span className="badge text-bg-primary-subtle border text-primary">{row.grade}</span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="small text-muted">{row.remarks || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default GradeCalculation;