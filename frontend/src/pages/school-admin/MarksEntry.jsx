import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiCheck, FiRefreshCw, FiSave } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { assignmentMarksService, examsService, marksEntryService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';

const EXAM_STEPS = [
  { key: 'subject', label: 'Subject' },
  { key: 'paper', label: 'Paper' },
  { key: 'class', label: 'Class' },
  { key: 'term', label: 'Term' },
  { key: 'exam', label: 'Exam' },
  { key: 'marks', label: 'Enter Marks' },
];

const ASSIGNMENT_STEPS = [
  { key: 'subject', label: 'Subject' },
  { key: 'paper', label: 'Paper' },
  { key: 'class', label: 'Class' },
  { key: 'assessment', label: 'Assignment' },
  { key: 'marks', label: 'Enter Marks' },
];

function examStepIndex(selection, requiresPaper) {
  if (!selection.subject) return 0;
  if (requiresPaper && !selection.paper && selection.paper !== 'none') return 1;
  if (!selection.school_class) return requiresPaper ? 2 : 1;
  if (!selection.term) return requiresPaper ? 3 : 2;
  if (!selection.exam) return requiresPaper ? 4 : 3;
  return requiresPaper ? 5 : 4;
}

function assignmentStepIndex(selection, requiresPaper) {
  if (!selection.subject) return 0;
  if (requiresPaper && !selection.paper && selection.paper !== 'none') return 1;
  if (!selection.school_class) return requiresPaper ? 2 : 1;
  if (!selection.assessment) return requiresPaper ? 3 : 2;
  return requiresPaper ? 4 : 3;
}

export function MarksEntry({ context = 'examinations' }) {
  const queryClient = useQueryClient();
  const { canWriteFeature } = usePermissions();
  const canManage = canWriteFeature('marks_entry');
  const isAssignments = context === 'assignments';
  const backPath = isAssignments ? '/school-admin/academics/assignments' : '/school-admin/examinations';
  const backLabel = isAssignments ? 'Assignments' : 'Examinations';

  const [selection, setSelection] = useState({
    subject: '',
    paper: '',
    school_class: '',
    term: '',
    exam: '',
    assessment: '',
  });
  const [assignmentName, setAssignmentName] = useState('');
  const [openingAssessment, setOpeningAssessment] = useState(false);
  const [scores, setScores] = useState({});
  const [remarks, setRemarks] = useState({});
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const optionsParams = useMemo(() => {
    if (isAssignments) {
      return {
        subject: selection.subject || undefined,
        paper: selection.paper || undefined,
        school_class: selection.school_class || undefined,
        assessment: selection.assessment || undefined,
      };
    }
    return {
      subject: selection.subject || undefined,
      paper: selection.paper || undefined,
      school_class: selection.school_class || undefined,
      term: selection.term || undefined,
      exam: selection.exam || undefined,
    };
  }, [isAssignments, selection]);

  const { data: options, isLoading, isError, refetch } = useQuery({
    queryKey: [isAssignments ? 'assignment-marks-options' : 'marks-entry-options', optionsParams],
    queryFn: () => (
      isAssignments
        ? assignmentMarksService.getOptions(optionsParams)
        : marksEntryService.getOptions(optionsParams)
    ),
    staleTime: 30_000,
    enabled: !isAssignments || !openingAssessment,
  });

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
  const scopeMeta = options?.scope_meta;

  const visibleSteps = useMemo(
    () => (isAssignments ? ASSIGNMENT_STEPS : EXAM_STEPS).filter((step) => step.key !== 'paper' || requiresPaper),
    [isAssignments, requiresPaper],
  );
  const activeStep = isAssignments
    ? assignmentStepIndex(selection, requiresPaper)
    : examStepIndex(selection, requiresPaper);

  const mergedScores = useMemo(() => {
    const base = {};
    students.forEach((student) => {
      const existing = grades[student.id];
      base[student.id] = scores[student.id] ?? existing?.score ?? '';
    });
    return base;
  }, [students, grades, scores]);

  const mergedRemarks = useMemo(() => {
    const base = {};
    students.forEach((student) => {
      const existing = grades[student.id];
      base[student.id] = remarks[student.id] ?? existing?.remarks ?? '';
    });
    return base;
  }, [students, grades, remarks]);

  const updateSelection = (key, value) => {
    const next = { ...selection, [key]: value };
    if (key === 'subject') {
      next.paper = '';
      next.school_class = '';
      next.term = '';
      next.exam = '';
      next.assessment = '';
      setAssignmentName('');
    } else if (key === 'paper') {
      next.school_class = '';
      next.term = '';
      next.exam = '';
      next.assessment = '';
      setAssignmentName('');
    } else if (key === 'school_class') {
      next.term = '';
      next.exam = '';
      next.assessment = '';
      setAssignmentName('');
    } else if (key === 'term') {
      next.exam = '';
    } else if (key === 'assessment') {
      const picked = assessments.find((item) => item.value === value);
      setAssignmentName(picked?.label || '');
    }
    setSelection(next);
    setScores({});
    setRemarks({});
  };

  const resetAll = () => {
    setSelection({ subject: '', paper: '', school_class: '', term: '', exam: '', assessment: '' });
    setAssignmentName('');
    setScores({});
    setRemarks({});
    queryClient.removeQueries({ queryKey: [isAssignments ? 'assignment-marks-options' : 'marks-entry-options'] });
  };

  const activeAssessmentId = isAssignments ? selection.assessment : selection.exam;
  const marksStatus = examDetail?.marks_status || 'draft';
  const marksEditable = marksStatus === 'draft' || marksStatus === 'submitted';
  const canEditMarks = canManage && marksEditable;
  const hasSavedGrades = Object.keys(grades).length > 0;
  const canSubmit = !isAssignments && canManage && marksStatus === 'draft' && hasSavedGrades;

  const openAssignment = async () => {
    if (!selection.subject || !selection.school_class) return;

    const existing = selection.assessment
      ? assessments.find((item) => item.value === selection.assessment)
      : null;
    const name = (assignmentName || existing?.label || '').trim();
    if (!name) {
      notify.error('Enter a name for this assignment, e.g. Assignment 1.');
      return;
    }

    setOpeningAssessment(true);
    try {
      let assessmentId = selection.assessment;
      if (!assessmentId || existing?.label !== name) {
        const created = await assignmentMarksService.createAssessment({
          name,
          subject: selection.subject,
          school_class: selection.school_class,
          paper: selection.paper || undefined,
        });
        assessmentId = created?.id;
        if (!assessmentId) {
          notify.error('Unable to open assignment.');
          return;
        }
      }
      setSelection((prev) => ({ ...prev, assessment: String(assessmentId) }));
      setAssignmentName(name);
      await queryClient.invalidateQueries({ queryKey: ['assignment-marks-options'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to open assignment.'));
    } finally {
      setOpeningAssessment(false);
    }
  };

  const handleSubmit = async () => {
    if (!selection.exam || !canSubmit) return;
    setSubmitting(true);
    try {
      const result = await examsService.submitMarks(selection.exam);
      notify.success(result?.message || 'Marks submitted for approval.');
      await refetch();
      await queryClient.invalidateQueries({ queryKey: ['academic-workspace'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to submit marks.'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleSave = async () => {
    if (!activeAssessmentId) return;
    setSaving(true);
    try {
      const entries = students.map((student) => ({
        student: student.id,
        score: mergedScores[student.id] === '' ? null : mergedScores[student.id],
        remarks: mergedRemarks[student.id] || '',
      }));
      const saveService = isAssignments ? assignmentMarksService : marksEntryService;
      const result = await saveService.saveBulk({ exam: activeAssessmentId, entries });
      if (result?.errors?.length) {
        notify.warning(result.message || 'Some marks could not be saved.');
      } else {
        notify.success(result?.message || 'Marks saved.');
      }
      await refetch();
      setScores({});
      setRemarks({});
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to save marks.'));
    } finally {
      setSaving(false);
    }
  };

  const renderSelect = (id, label, value, items, disabled, required, placeholder) => (
    <div className="col-md-6 col-lg-3" key={id}>
      <label className="form-label small fw-semibold" htmlFor={id}>
        {label}
        {required && <span className="text-danger"> *</span>}
      </label>
      <select
        id={id}
        className="form-select"
        value={value}
        disabled={disabled || (id !== 'subject' && isLoading)}
        onChange={(e) => updateSelection(id, e.target.value)}
      >
        <option value="">{placeholder || `Select ${label.toLowerCase()}…`}</option>
        {items.map((item) => (
          <option key={item.value} value={item.value}>{item.label}</option>
        ))}
      </select>
    </div>
  );

  const subjectsLoading = isLoading && !options;

  return (
    <div>
      <div className="mb-3">
        <Link to={backPath} className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> {backLabel}
        </Link>
      </div>

      <PageHeader
        title={isAssignments ? 'Marks entry' : 'Marks Entry'}
        subtitle={
          isAssignments
            ? 'Choose your subject and class, name the assignment, then enter student scores. No term selection is required.'
            : 'Choose subject first, then class and school-defined term before entering scores'
        }
        actions={activeAssessmentId && (canEditMarks || canSubmit) && (
          <div className="d-flex gap-2">
            {canEditMarks && (
              <button
                type="button"
                className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
                onClick={handleSave}
                disabled={saving || students.length === 0}
              >
                <FiSave size={14} /> {saving ? 'Saving…' : 'Save All Marks'}
              </button>
            )}
            {canSubmit && (
              <button
                type="button"
                className="btn btn-success btn-sm d-inline-flex align-items-center gap-1"
                onClick={handleSubmit}
                disabled={submitting}
              >
                {submitting ? 'Submitting…' : 'Submit for Approval'}
              </button>
            )}
          </div>
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
          {selection.subject && (
            <button
              type="button"
              className="btn btn-link btn-sm text-muted ms-auto p-0"
              onClick={resetAll}
            >
              <FiRefreshCw size={14} className="me-1" /> Start over
            </button>
          )}
        </div>

        <div className="row g-3">
          {renderSelect(
            'subject',
            'Subject',
            selection.subject,
            subjects,
            subjectsLoading,
            true,
          )}
          {selection.subject && requiresPaper && renderSelect(
            'paper',
            'Paper',
            selection.paper,
            papers,
            false,
            false,
            'Whole subject (no paper)',
          )}
          {selection.subject && renderSelect(
            'school_class',
            'Class',
            selection.school_class,
            classes,
            !selection.subject,
            true,
          )}

          {isAssignments && selection.school_class && (
            <>
              <div className="col-md-6 col-lg-4">
                <label className="form-label small fw-semibold" htmlFor="assignment-name">
                  Assignment name <span className="text-danger">*</span>
                </label>
                <input
                  id="assignment-name"
                  type="text"
                  className="form-control"
                  placeholder="e.g. Assignment 1"
                  value={assignmentName}
                  onChange={(e) => {
                    setAssignmentName(e.target.value);
                    setSelection((prev) => ({ ...prev, assessment: '' }));
                    setScores({});
                    setRemarks({});
                  }}
                />
              </div>
              {assessments.length > 0 && (
                <div className="col-md-6 col-lg-4">
                  <label className="form-label small fw-semibold" htmlFor="assessment">
                    Or pick existing
                  </label>
                  <select
                    id="assessment"
                    className="form-select"
                    value={selection.assessment}
                    onChange={(e) => updateSelection('assessment', e.target.value)}
                  >
                    <option value="">Select an existing assignment…</option>
                    {assessments.map((item) => (
                      <option key={item.value} value={item.value}>{item.label}</option>
                    ))}
                  </select>
                </div>
              )}
              <div className="col-md-6 col-lg-4 d-flex align-items-end">
                <button
                  type="button"
                  className="btn btn-outline-primary w-100"
                  onClick={openAssignment}
                  disabled={openingAssessment || !assignmentName.trim()}
                >
                  {openingAssessment ? 'Opening…' : 'Open assignment'}
                </button>
              </div>
            </>
          )}

          {!isAssignments && selection.school_class && renderSelect(
            'term',
            'Term',
            selection.term,
            terms,
            !selection.school_class,
            true,
          )}
          {!isAssignments && selection.term && renderSelect(
            'exam',
            'Exam',
            selection.exam,
            exams,
            !selection.term,
            true,
          )}
        </div>

        {scopeMeta?.uses_teaching_assignments && (
          <div className="alert alert-info mt-3 mb-0 small">
            Showing only subjects and classes from your teaching assignments.
          </div>
        )}
        {selection.subject && !isLoading && classes.length === 0 && !selection.school_class && (
          <div className="alert alert-warning mt-3 mb-0 small">
            {isAssignments
              ? 'No classes are linked to this subject in your teaching assignments.'
              : 'No classes are linked to this subject yet. Assign the subject in timetables, homework, or schedule an exam first.'}
          </div>
        )}
        {!isAssignments && selection.school_class && !isLoading && terms.length === 0 && !selection.term && (
          <div className="alert alert-warning mt-3 mb-0 small">
            No terms are defined for this class&apos;s academic year. Add terms under Academics → Terms.
          </div>
        )}
        {!isAssignments && selection.term && !isLoading && exams.length === 0 && !selection.exam && (
          <div className="alert alert-warning mt-3 mb-0 small">
            No exams match this selection.{' '}
            <Link to="/school-admin/examinations">Schedule an exam</Link> for this subject, class, and term.
          </div>
        )}
      </div>

      {isError && (
        <div className="alert alert-danger">Unable to load marks entry data. Please try again.</div>
      )}

      {activeAssessmentId && (
        <div className="apex-card p-0 overflow-hidden">
          <div className="p-4 border-bottom bg-light-subtle">
            <h5 className="fw-bold mb-1">{examDetail?.name || 'Enter marks'}</h5>
            <div className="d-flex flex-wrap align-items-center gap-2">
              <p className="text-muted small mb-0">
                {examDetail?.subject_name}
                {examDetail?.paper_code ? ` · ${examDetail.paper_code}` : ''}
                {' · '}{examDetail?.school_class_name}
                {!isAssignments && examDetail?.term_name ? ` · ${examDetail.term_name}` : ''}
                {examDetail?.max_score ? ` · Max score: ${examDetail.max_score}` : ''}
              </p>
              {!isAssignments && marksStatus && (
                <span className={`badge text-bg-${marksStatus === 'draft' ? 'secondary' : marksStatus === 'submitted' ? 'warning' : marksStatus === 'locked' ? 'dark' : 'success'}-subtle border`}>
                  {marksStatus.replace('_', ' ')}
                </span>
              )}
            </div>
          </div>

          {isLoading ? (
            <div className="p-5 text-center text-muted">Loading students…</div>
          ) : students.length === 0 ? (
            <ModuleEmptyState
              title="No active students in this class"
              message="Add or assign students to the class before entering marks."
              actionLabel="View students"
              actionHref="/school-admin/students"
            />
          ) : (
            <div className="table-responsive">
              <table className="table table-hover mb-0 align-middle">
                <thead className="table-light">
                  <tr>
                    <th style={{ width: 48 }}>#</th>
                    <th>Student</th>
                    <th>Admission No.</th>
                    <th style={{ width: 120 }}>Score</th>
                    <th style={{ width: 80 }}>Grade</th>
                    <th>Remarks</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((student, idx) => {
                    const existing = grades[student.id];
                    const scoreVal = mergedScores[student.id];
                    const hasScore = scoreVal !== '' && scoreVal !== null && scoreVal !== undefined;
                    return (
                      <tr key={student.id}>
                        <td className="text-muted">{idx + 1}</td>
                        <td className="fw-medium">{student.full_name}</td>
                        <td className="text-muted small">{student.admission_number}</td>
                        <td>
                          <input
                            type="number"
                            className="form-control form-control-sm"
                            min={0}
                            max={examDetail?.max_score || 100}
                            step="0.01"
                            disabled={!canEditMarks}
                            value={scoreVal}
                            onChange={(e) => setScores((prev) => ({ ...prev, [student.id]: e.target.value }))}
                            placeholder="—"
                          />
                        </td>
                        <td>
                          {hasScore && existing?.grade ? (
                            <span className="badge text-bg-primary-subtle border text-primary">{existing.grade}</span>
                          ) : '—'}
                        </td>
                        <td>
                          <input
                            type="text"
                            className="form-control form-control-sm"
                            disabled={!canEditMarks}
                            value={mergedRemarks[student.id] || ''}
                            onChange={(e) => setRemarks((prev) => ({ ...prev, [student.id]: e.target.value }))}
                            placeholder="Optional"
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {students.length > 0 && canEditMarks && (
            <div className="p-3 border-top d-flex justify-content-end gap-2">
              <button
                type="button"
                className="btn btn-primary d-inline-flex align-items-center gap-1"
                onClick={handleSave}
                disabled={saving}
              >
                <FiCheck size={16} /> {saving ? 'Saving…' : 'Save All Marks'}
              </button>
            </div>
          )}
        </div>
      )}

      {!selection.subject && !subjectsLoading && (
        <div className="apex-card p-5">
          <ModuleEmptyState
            title={subjects.length === 0 ? 'No subjects found' : 'Choose a subject to begin'}
            message={
              subjects.length === 0
                ? 'Add subjects under Academics → Subjects. They will appear here automatically for marks entry.'
                : isAssignments
                  ? 'Select your subject and class, name the assignment, then enter scores.'
                  : 'Marks entry starts with the subject. Select one, then pick class, term, and exam.'
            }
            actionLabel={subjects.length === 0 ? 'Add subjects' : undefined}
            actionHref={subjects.length === 0 ? '/school-admin/academics/subjects' : undefined}
          />
        </div>
      )}
    </div>
  );
}

export default MarksEntry;