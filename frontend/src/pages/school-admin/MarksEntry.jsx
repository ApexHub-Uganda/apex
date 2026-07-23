import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiCheck, FiRefreshCw, FiSave } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { assignmentMarksService, examsService, marksEntryService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';

// Examination marks: subject → paper (if needed) → class → exam → marks.
// Term / academic year are fixed to the current calendar (never asked).
const EXAM_STEPS = [
  { key: 'subject', label: 'Subject' },
  { key: 'paper', label: 'Paper' },
  { key: 'class', label: 'Class' },
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
  // Paper is optional filter (shown when subject has papers); class follows subject.
  if (!selection.school_class) return 1;
  if (requiresPaper && !selection.paper && !selection.exam) {
    // Stay on paper step only if multi-paper and no exam chosen yet
  }
  if (!selection.exam) return requiresPaper ? 2 : 2;
  return 3;
}

function assignmentStepIndex(selection, requiresPaper) {
  if (!selection.subject) return 0;
  if (requiresPaper && !selection.paper && selection.paper !== 'none') return 1;
  if (!selection.school_class) return requiresPaper ? 2 : 1;
  if (!selection.assessment) return requiresPaper ? 3 : 2;
  return requiresPaper ? 4 : 3;
}

function singleValue(items) {
  if (!items || items.length !== 1) return null;
  return String(items[0].value);
}

export function MarksEntry({ context = 'examinations' }) {
  const queryClient = useQueryClient();
  const { canWriteFeature } = usePermissions();
  const featureWrite = canWriteFeature('marks_entry');
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
  const autoApplied = useRef({ subject: false, paper: false, class: false, exam: false, term: false });

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
      // term always server-side current; do not send client term
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
    staleTime: 15_000,
    enabled: !isAssignments || !openingAssessment,
  });

  const subjects = options?.subjects || [];
  const papers = options?.papers || [];
  const requiresPaper = options?.requires_paper || false;
  const classes = options?.classes || [];
  const exams = options?.exams || [];
  const assessments = options?.assessments || [];
  const students = options?.students || [];
  const grades = options?.grades || {};
  const examDetail = options?.exam_detail;
  const scopeMeta = options?.scope_meta;
  const currentTerm = options?.current_term;
  const autoSelect = options?.auto_select || {};
  const canManage = featureWrite && (scopeMeta?.can_enter_marks !== false);
  const blockedReason = scopeMeta?.message
    || (!featureWrite ? 'Marks entry is not available for your account.' : null);

  // Auto-pick fixed / single options to shorten the wizard
  useEffect(() => {
    if (!options || isAssignments) return;

    setSelection((prev) => {
      let next = prev;
      let changed = false;
      const ensure = (key, value) => {
        if (!value || next[key]) return;
        if (next === prev) next = { ...prev };
        next[key] = String(value);
        changed = true;
      };

      // Current term (always)
      const termId = autoSelect.term || scopeMeta?.current_term_id || currentTerm?.value;
      if (termId && !next.term) {
        if (next === prev) next = { ...prev };
        next.term = String(termId);
        changed = true;
      }

      // Single subject
      const onlySubject = autoSelect.subject || singleValue(subjects);
      ensure('subject', onlySubject);

      // Single paper when subject uses papers
      if (next.subject && requiresPaper) {
        const onlyPaper = autoSelect.paper || singleValue(papers);
        ensure('paper', onlyPaper);
      }

      // Single class for this subject
      if (next.subject) {
        const onlyClass = autoSelect.school_class || singleValue(classes);
        ensure('school_class', onlyClass);
      }

      // Single exam for subject/class/term
      if (next.school_class) {
        const onlyExam = autoSelect.exam || singleValue(exams);
        ensure('exam', onlyExam);
      }

      return changed ? next : prev;
    });
  }, [
    isAssignments,
    options,
    subjects,
    papers,
    classes,
    exams,
    requiresPaper,
    autoSelect.subject,
    autoSelect.paper,
    autoSelect.school_class,
    autoSelect.exam,
    autoSelect.term,
    scopeMeta?.current_term_id,
    currentTerm?.value,
  ]);

  // Assignments: auto subject/class only
  useEffect(() => {
    if (!options || !isAssignments) return;
    setSelection((prev) => {
      let next = prev;
      let changed = false;
      if (!next.subject && subjects.length === 1) {
        next = { ...next, subject: String(subjects[0].value) };
        changed = true;
      }
      if (next.subject && requiresPaper && !next.paper && papers.length === 1) {
        next = { ...next, paper: String(papers[0].value) };
        changed = true;
      }
      if (next.subject && !next.school_class && classes.length === 1) {
        next = { ...next, school_class: String(classes[0].value) };
        changed = true;
      }
      return changed ? next : prev;
    });
  }, [isAssignments, options, subjects, papers, classes, requiresPaper]);

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
      next.exam = '';
      next.assessment = '';
      setAssignmentName('');
    } else if (key === 'paper') {
      next.school_class = selection.school_class; // keep class when only changing paper
      next.exam = '';
      next.assessment = '';
      setAssignmentName('');
    } else if (key === 'school_class') {
      next.exam = '';
      next.assessment = '';
      setAssignmentName('');
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
    autoApplied.current = { subject: false, paper: false, class: false, exam: false, term: false };
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
    <div className="col-12 col-sm-6 col-xl-3" key={id}>
      <label className="form-label small fw-semibold" htmlFor={id}>
        {label}
        {required && <span className="text-danger"> *</span>}
      </label>
      <select
        id={id}
        className="form-select"
        value={value}
        disabled={disabled || (id !== 'subject' && isLoading) || items.length <= 1}
        onChange={(e) => updateSelection(id, e.target.value)}
      >
        {items.length !== 1 && (
          <option value="">{placeholder || `Select ${label.toLowerCase()}…`}</option>
        )}
        {items.map((item) => (
          <option key={item.value} value={item.value}>{item.label}</option>
        ))}
      </select>
    </div>
  );

  const subjectsLoading = isLoading && !options;

  if (!subjectsLoading && options && scopeMeta?.can_enter_marks === false) {
    return (
      <div>
        <div className="mb-3">
          <Link to={backPath} className="small text-decoration-none text-muted">
            <FiArrowLeft className="me-1" /> {backLabel}
          </Link>
        </div>
        <PageHeader title="Marks Entry" subtitle="Enter scores for your teaching assignments" />
        <div className="apex-card p-5">
          <ModuleEmptyState
            title="No marks entry available"
            message={
              blockedReason
              || 'You do not have subject–class assignments for marks entry. Use Results to review scores.'
            }
            actionLabel="View results"
            actionHref="/school-admin/examinations/results"
          />
        </div>
      </div>
    );
  }

  const termLabel = currentTerm?.label
    || (scopeMeta?.current_term_name
      ? `${scopeMeta.current_term_name}${scopeMeta.current_academic_year_name ? ` · ${scopeMeta.current_academic_year_name}` : ''}`
      : null);

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
            ? 'Enter scores for classes and subjects you teach, then apply a grading scheme under Grade Calculation.'
            : 'Enter scores for subjects and classes you teach. The current term is applied automatically.'
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

      <div className="apex-card apex-card--responsive p-3 p-md-4 mb-4">
        <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
          <div className="marks-entry-steps flex-grow-1">
            {visibleSteps.map((step, idx) => (
              <div
                key={step.key}
                className={`marks-entry-step ${idx <= activeStep ? 'marks-entry-step--active' : ''} ${idx === activeStep ? 'marks-entry-step--current' : ''}`}
              >
                <span className="marks-entry-step-num">{idx + 1}</span>
                <span className="small fw-medium marks-entry-step-label">{step.label}</span>
              </div>
            ))}
          </div>
          {selection.subject && (
            <button
              type="button"
              className="btn btn-link btn-sm text-muted p-0 flex-shrink-0"
              onClick={resetAll}
            >
              <FiRefreshCw size={14} className="me-1" /> Start over
            </button>
          )}
        </div>

        {!isAssignments && (termLabel || scopeMeta?.active_exam_period) && (
          <div className="alert alert-light border small mb-3 py-2">
            {termLabel && (
              <div className="text-break">
                <strong>Current term:</strong> {termLabel}
                <span className="text-muted d-none d-sm-inline ms-2">— applied automatically</span>
              </div>
            )}
            {scopeMeta?.active_exam_period && (
              <div className={`text-break ${termLabel ? 'mt-1' : ''}`}>
                <strong>Exam period:</strong> {scopeMeta.active_exam_period.name}
                {scopeMeta.active_exam_period.end_date
                  ? ` (until ${scopeMeta.active_exam_period.end_date})`
                  : ''}
              </div>
            )}
          </div>
        )}

        <div className="row g-3 apex-form-grid">
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
            true,
            'Select paper…',
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
              <div className="col-12 col-sm-6 col-xl-4">
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
                <div className="col-12 col-sm-6 col-xl-4">
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
              <div className="col-12 col-sm-6 col-xl-4 d-flex align-items-end">
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
            'exam',
            'Exam',
            selection.exam,
            exams,
            !selection.school_class,
            true,
          )}
        </div>

        {selection.subject && !isLoading && classes.length === 0 && !selection.school_class && (
          <div className="alert alert-warning mt-3 mb-0 small">
            No classes are linked to this subject in your teaching assignments.
            Ask the DoS or school admin to assign you this subject for a class.
          </div>
        )}
        {!isAssignments && selection.school_class && !isLoading && exams.length === 0 && !selection.exam && (
          <div className="alert alert-warning mt-3 mb-0 small">
            {scopeMeta?.has_active_exam_period
              ? 'No mark sheet could be opened for this subject and class. Confirm you are assigned to teach this pair, then try Start over.'
              : (
                <>
                  No open exam period. A school admin or DoS must create and activate an{' '}
                  <Link to="/school-admin/examinations/sessions">Exam Session</Link>
                  {' '}(exam period). Mark sheets are then created automatically when you select a subject and class you teach.
                </>
              )}
          </div>
        )}
        {!isAssignments && !scopeMeta?.current_term_id && !isLoading && (
          <div className="alert alert-warning mt-3 mb-0 small">
            No current academic term is set. A school admin must set the current term under Academics → Terms.
          </div>
        )}
        {!isAssignments && scopeMeta?.setup_hint && !scopeMeta?.has_active_exam_period && !selection.school_class && (
          <div className="alert alert-info mt-3 mb-0 small">
            {scopeMeta.setup_hint}
          </div>
        )}
      </div>

      {isError && (
        <div className="alert alert-danger">Unable to load marks entry data. Please try again.</div>
      )}

      {activeAssessmentId && (
        <div className="apex-card p-0 overflow-hidden">
          <div className="p-3 p-md-4 border-bottom bg-light-subtle">
            <h5 className="fw-bold mb-1 text-break">{examDetail?.name || 'Enter marks'}</h5>
            <div className="d-flex flex-wrap align-items-center gap-2">
              <p className="text-muted small mb-0 text-break">
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
            <div className="apex-sheet-scroll">
              <table className="table table-hover apex-sheet-table align-middle">
                <thead className="table-light">
                  <tr>
                    <th style={{ width: 40 }}>#</th>
                    <th className="apex-sheet-col-student">Student</th>
                    <th>Adm #</th>
                    <th className="apex-sheet-col-score">Score</th>
                    <th style={{ width: 72 }}>Grade</th>
                    <th className="apex-sheet-col-remarks">Remarks</th>
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
                        <td className="fw-medium apex-sheet-col-student">{student.full_name}</td>
                        <td className="text-muted small">{student.admission_number}</td>
                        <td className="apex-sheet-col-score">
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
                            inputMode="decimal"
                          />
                        </td>
                        <td>
                          {hasScore && existing?.grade ? (
                            <span className="badge text-bg-primary-subtle border text-primary">{existing.grade}</span>
                          ) : '—'}
                        </td>
                        <td className="apex-sheet-col-remarks">
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
            <div className="p-3 border-top d-flex flex-wrap justify-content-stretch justify-content-md-end gap-2">
              <button
                type="button"
                className="btn btn-primary d-inline-flex align-items-center justify-content-center gap-1 flex-grow-1 flex-md-grow-0"
                onClick={handleSave}
                disabled={saving}
              >
                <FiCheck size={16} /> {saving ? 'Saving…' : 'Save All Marks'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default MarksEntry;
