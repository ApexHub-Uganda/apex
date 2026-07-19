import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  FiArrowLeft, FiArrowRight, FiCheck, FiClock, FiLock, FiRefreshCw, FiShield, FiZap,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { timetableWizardService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';

const STEPS = [
  { key: 'type', label: 'Type' },
  { key: 'scope', label: 'Scope' },
  { key: 'slots', label: 'Time slots' },
  { key: 'options', label: 'Options' },
  { key: 'preview', label: 'Preview' },
];

const DAY_OPTIONS = [
  { value: 0, label: 'Mon' },
  { value: 1, label: 'Tue' },
  { value: 2, label: 'Wed' },
  { value: 3, label: 'Thu' },
  { value: 4, label: 'Fri' },
  { value: 5, label: 'Sat' },
];

function Stepper({ step }) {
  return (
    <div className="d-flex flex-wrap gap-2 mb-4">
      {STEPS.map((item, index) => {
        const active = index === step;
        const done = index < step;
        return (
          <div
            key={item.key}
            className={`d-flex align-items-center gap-2 px-3 py-2 rounded-pill border small ${
              active ? 'border-primary bg-primary-subtle text-primary fw-semibold' : done ? 'border-success text-success' : 'text-muted'
            }`}
          >
            <span
              className={`d-inline-flex align-items-center justify-content-center rounded-circle ${
                active || done ? 'bg-primary text-white' : 'bg-light'
              }`}
              style={{ width: 22, height: 22, fontSize: 11 }}
            >
              {done ? <FiCheck size={12} /> : index + 1}
            </span>
            {item.label}
          </div>
        );
      })}
    </div>
  );
}

function StatsBar({ stats, warnings }) {
  if (!stats) return null;
  return (
    <div className="row g-2 mb-3">
      {[
        { label: 'Placed', value: stats.placed_slots },
        { label: 'Requested', value: stats.requested_slots },
        { label: 'Unplaced', value: stats.unplaced_slots },
        { label: 'Rate', value: `${stats.placement_rate ?? 0}%` },
        { label: 'Classes', value: stats.classes },
        { label: 'Seed', value: stats.seed },
      ].map((item) => (
        <div key={item.label} className="col-6 col-md-2">
          <div className="apex-card p-2 text-center h-100">
            <div className="small text-muted">{item.label}</div>
            <div className="fw-bold">{item.value ?? '—'}</div>
          </div>
        </div>
      ))}
      {warnings?.length > 0 && (
        <div className="col-12">
          <div className="alert alert-warning py-2 mb-0 small">
            {warnings.map((w) => <div key={w}>{w}</div>)}
          </div>
        </div>
      )}
    </div>
  );
}

function PreviewGrid({ slots = [] }) {
  const byClass = useMemo(() => {
    const map = {};
    slots.forEach((slot) => {
      const key = slot.school_class_name || slot.school_class_id;
      map[key] = map[key] || [];
      map[key].push(slot);
    });
    Object.values(map).forEach((list) => {
      list.sort((a, b) => {
        const da = a.exam_date || a.day_of_week;
        const db = b.exam_date || b.day_of_week;
        if (da !== db) return String(da).localeCompare(String(db));
        return String(a.start_time).localeCompare(String(b.start_time));
      });
    });
    return map;
  }, [slots]);

  const classNames = Object.keys(byClass).sort();
  if (!classNames.length) {
    return <ModuleEmptyState title="No slots generated" message="Adjust options and regenerate." />;
  }

  return (
    <div className="row g-3">
      {classNames.map((className) => (
        <div key={className} className="col-lg-6">
          <div className="apex-card p-3 h-100">
            <h6 className="fw-bold mb-2">{className}</h6>
            <div className="table-responsive">
              <table className="table table-sm align-middle mb-0">
                <thead>
                  <tr className="small text-muted">
                    <th>When</th>
                    <th>Period</th>
                    <th>Subject</th>
                    <th>Teacher</th>
                  </tr>
                </thead>
                <tbody>
                  {byClass[className].slice(0, 40).map((slot, idx) => (
                    <tr key={`${className}-${idx}`}>
                      <td className="small">
                        {slot.exam_date || slot.day_label}
                        {slot.stream_name ? ` · ${slot.stream_name}` : ''}
                      </td>
                      <td className="small">{slot.period_name || `${slot.start_time}-${slot.end_time}`}</td>
                      <td className="small fw-medium">{slot.subject_code || slot.subject_name}</td>
                      <td className="small text-muted">{slot.teacher_name || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {byClass[className].length > 40 && (
                <div className="small text-muted mt-1">+{byClass[className].length - 40} more slots</div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function TimetableWizard() {
  const queryClient = useQueryClient();
  const { canWriteFeature, isSchoolAdmin } = usePermissions();
  const canGenerate = isSchoolAdmin || canWriteFeature('timetables');

  const [step, setStep] = useState(0);
  const [scheduleType, setScheduleType] = useState('lesson');
  const [termId, setTermId] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [workingDays, setWorkingDays] = useState([0, 1, 2, 3, 4]);
  const [periodIds, setPeriodIds] = useState([]);
  const [classIds, setClassIds] = useState([]);
  const [lessonsPerSubject, setLessonsPerSubject] = useState(4);
  const [examsPerDay, setExamsPerDay] = useState(2);
  const [useStreams, setUseStreams] = useState(true);
  const [name, setName] = useState('');
  const [draft, setDraft] = useState(null);

  const { data: context, isLoading: contextLoading, isError: contextError } = useQuery({
    queryKey: ['timetable-generate-context'],
    queryFn: () => timetableWizardService.getContext(),
  });

  const { data: schedules = [] } = useQuery({
    queryKey: ['timetable-schedules'],
    queryFn: () => timetableWizardService.listSchedules(),
  });

  useEffect(() => {
    if (!context) return;
    if (periodIds.length === 0 && context.defaults?.period_ids?.length) {
      setPeriodIds(context.defaults.period_ids);
    }
    if (!termId && context.active_term?.id) {
      setTermId(context.active_term.id);
    }
  }, [context]); // eslint-disable-line react-hooks/exhaustive-deps

  const readiness = context?.readiness || {};
  const periods = (context?.periods || []).filter((p) => !p.is_break);
  const breakPeriods = (context?.periods || []).filter((p) => p.is_break);

  const generateMutation = useMutation({
    mutationFn: (payload) => timetableWizardService.generate(payload),
    onSuccess: (data) => {
      setDraft(data);
      setStep(4);
      notify.success('Draft generated — review, reshuffle, or use it.');
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to generate timetable.')),
  });

  const regenerateMutation = useMutation({
    mutationFn: (id) => timetableWizardService.regenerate(id),
    onSuccess: (data) => {
      setDraft(data);
      notify.success('Slots reshuffled with a new seed.');
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to regenerate.')),
  });

  const applyMutation = useMutation({
    mutationFn: (id) => timetableWizardService.apply(id),
    onSuccess: async () => {
      notify.success('Timetable applied and locked. Only school admins can edit it now.');
      setDraft(null);
      setStep(0);
      await queryClient.invalidateQueries({ queryKey: ['timetable-schedules'] });
      await queryClient.invalidateQueries({ queryKey: ['timetables'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to apply timetable.')),
  });

  const deleteScheduleMutation = useMutation({
    mutationFn: (id) => timetableWizardService.deleteSchedule(id),
    onSuccess: async () => {
      notify.success('Schedule deleted.');
      await queryClient.invalidateQueries({ queryKey: ['timetable-schedules'] });
      await queryClient.invalidateQueries({ queryKey: ['timetables'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Only school admins can delete a locked timetable.')),
  });

  const toggleDay = (day) => {
    setWorkingDays((prev) => (
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day].sort()
    ));
  };

  const togglePeriod = (id) => {
    setPeriodIds((prev) => (
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    ));
  };

  const toggleClass = (id) => {
    setClassIds((prev) => (
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    ));
  };

  const runGenerate = () => {
    const config = {
      name: name || undefined,
      working_days: workingDays,
      period_ids: periodIds,
      class_ids: classIds,
      lessons_per_subject_per_week: lessonsPerSubject,
      exams_per_day: examsPerDay,
      use_streams: useStreams,
      term_id: scheduleType === 'lesson' ? termId : undefined,
      examination_session_id: scheduleType === 'exam' ? sessionId : undefined,
    };
    generateMutation.mutate({ schedule_type: scheduleType, config });
  };

  if (!canGenerate) {
    return (
      <div>
        <div className="mb-3">
          <Link to="/school-admin/academics" className="small text-decoration-none text-muted">
            <FiArrowLeft className="me-1" /> Academics
          </Link>
        </div>
        <div className="apex-card p-5 text-center">
          <FiShield size={28} className="text-muted mb-2" />
          <h5 className="fw-bold">Write permission required</h5>
          <p className="text-muted mb-0">
            Timetable generation is available to school admins and roles with Timetables write access.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/academics/timetable" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Timetables
        </Link>
      </div>

      <PageHeader
        title="Timetable Generation Wizard"
        subtitle="Constraint-aware scheduling for lessons or exams — regenerate until it fits, then use it"
      />

      {contextError && (
        <div className="alert alert-danger">Unable to load generation context.</div>
      )}

      <div className="apex-card p-3 p-md-4 mb-4">
        <Stepper step={step} />

        {contextLoading ? (
          <div className="text-center py-5 text-muted">Loading school constraints…</div>
        ) : (
          <>
            {step === 0 && (
              <div>
                <h5 className="fw-bold mb-3">What are you scheduling?</h5>
                <div className="row g-3">
                  {[
                    {
                      key: 'lesson',
                      title: 'Lesson timetable',
                      desc: 'Weekly class periods from teaching assignments, periods, and streams.',
                      ready: readiness.can_generate_lessons,
                    },
                    {
                      key: 'exam',
                      title: 'Exam timetable',
                      desc: 'Sittings across an examination session using class–subject assignments.',
                      ready: readiness.can_generate_exams,
                    },
                  ].map((opt) => (
                    <div key={opt.key} className="col-md-6">
                      <button
                        type="button"
                        className={`w-100 text-start apex-card p-4 border h-100 ${scheduleType === opt.key ? 'border-primary shadow-sm' : ''}`}
                        onClick={() => setScheduleType(opt.key)}
                      >
                        <div className="d-flex align-items-center gap-2 mb-2">
                          <FiZap className="text-primary" />
                          <span className="fw-bold">{opt.title}</span>
                        </div>
                        <p className="small text-muted mb-2">{opt.desc}</p>
                        <span className={`badge ${opt.ready ? 'text-bg-success-subtle text-success border' : 'text-bg-warning-subtle text-warning border'}`}>
                          {opt.ready ? 'Ready' : 'Missing prerequisites'}
                        </span>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {step === 1 && (
              <div>
                <h5 className="fw-bold mb-3">Scope</h5>
                {scheduleType === 'lesson' ? (
                  <div className="mb-3">
                    <label className="form-label small fw-medium">Academic term</label>
                    <div className="form-control bg-light">
                      {context?.active_term
                        ? `${context.active_term.name} (${context.active_term.start_date} → ${context.active_term.end_date})`
                        : 'No active term — create/activate a term first'}
                    </div>
                    <div className="form-text">Generation uses the school’s active term and teaching assignments.</div>
                  </div>
                ) : (
                  <div className="mb-3">
                    <label className="form-label small fw-medium">Examination session *</label>
                    <select
                      className="form-select"
                      value={sessionId}
                      onChange={(e) => setSessionId(e.target.value)}
                    >
                      <option value="">Select session</option>
                      {(context?.examination_sessions || []).map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name} ({s.start_date} → {s.end_date})
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="mb-3">
                  <label className="form-label small fw-medium">Optional name</label>
                  <input
                    className="form-control"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder={scheduleType === 'lesson' ? 'e.g. Term 1 Master Timetable' : 'e.g. End of Term Exams'}
                  />
                </div>

                <div className="mb-2 small fw-medium">Classes (leave empty = all)</div>
                <div className="d-flex flex-wrap gap-2">
                  {(context?.classes || []).map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      className={`btn btn-sm ${classIds.includes(c.id) ? 'btn-primary' : 'btn-outline-secondary'}`}
                      onClick={() => toggleClass(c.id)}
                    >
                      {c.name}
                      {c.stream_count ? ` · ${c.stream_count} stream(s)` : ''}
                    </button>
                  ))}
                  {!context?.classes?.length && (
                    <span className="text-muted small">No classes in the active year.</span>
                  )}
                </div>
              </div>
            )}

            {step === 2 && (
              <div>
                <h5 className="fw-bold mb-2">Time slots</h5>
                <p className="text-muted small mb-3">
                  Teaching periods are used as sittings. Breaks (e.g. breakfast) are excluded automatically.
                </p>
                <div className="row g-2 mb-3">
                  {periods.map((p) => (
                    <div key={p.id} className="col-md-4 col-lg-3">
                      <button
                        type="button"
                        className={`w-100 btn btn-sm text-start ${periodIds.includes(p.id) ? 'btn-primary' : 'btn-outline-secondary'}`}
                        onClick={() => togglePeriod(p.id)}
                      >
                        <FiClock className="me-1" />
                        {p.name}
                        <div className="small opacity-75">{p.start_time} – {p.end_time}</div>
                      </button>
                    </div>
                  ))}
                </div>
                {breakPeriods.length > 0 && (
                  <div className="small text-muted mb-3">
                    Breaks (skipped): {breakPeriods.map((p) => `${p.name} ${p.start_time}-${p.end_time}`).join(' · ')}
                  </div>
                )}
                {!periods.length && (
                  <div className="alert alert-warning">
                    No teaching periods defined. Add periods under Academics → Periods first.
                    <Link className="ms-2" to="/school-admin/academics/periods">Open periods</Link>
                  </div>
                )}

                {scheduleType === 'lesson' && (
                  <>
                    <div className="small fw-medium mb-2">Working days</div>
                    <div className="d-flex flex-wrap gap-2">
                      {DAY_OPTIONS.map((d) => (
                        <button
                          key={d.value}
                          type="button"
                          className={`btn btn-sm ${workingDays.includes(d.value) ? 'btn-primary' : 'btn-outline-secondary'}`}
                          onClick={() => toggleDay(d.value)}
                        >
                          {d.label}
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {step === 3 && (
              <div>
                <h5 className="fw-bold mb-3">Generation options</h5>
                <div className="row g-3">
                  {scheduleType === 'lesson' ? (
                    <>
                      <div className="col-md-4">
                        <label className="form-label small fw-medium">Lessons per subject / week</label>
                        <input
                          type="number"
                          min={1}
                          max={12}
                          className="form-control"
                          value={lessonsPerSubject}
                          onChange={(e) => setLessonsPerSubject(Number(e.target.value) || 1)}
                        />
                      </div>
                      <div className="col-md-8 d-flex align-items-end">
                        <div className="form-check form-switch">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            id="use-streams"
                            checked={useStreams}
                            onChange={(e) => setUseStreams(e.target.checked)}
                          />
                          <label className="form-check-label" htmlFor="use-streams">
                            Expand streams as separate groups when present
                          </label>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="col-md-4">
                      <label className="form-label small fw-medium">Exam sittings per day</label>
                      <input
                        type="number"
                        min={1}
                        max={6}
                        className="form-control"
                        value={examsPerDay}
                        onChange={(e) => setExamsPerDay(Number(e.target.value) || 1)}
                      />
                    </div>
                  )}
                </div>
                <div className="alert alert-info small mt-3 mb-0">
                  <strong>Constraints enforced:</strong> one class (and stream) per period; one teacher per period;
                  only subjects with teaching assignments; breaks never scheduled; regenerate reshuffles with a new seed.
                </div>
              </div>
            )}

            {step === 4 && (
              <div>
                <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                  <h5 className="fw-bold mb-0">Preview draft</h5>
                  <div className="d-flex gap-2">
                    <button
                      type="button"
                      className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1"
                      disabled={!draft?.id || regenerateMutation.isPending}
                      onClick={() => regenerateMutation.mutate(draft.id)}
                    >
                      <FiRefreshCw size={14} /> {regenerateMutation.isPending ? 'Shuffling…' : 'Regenerate'}
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
                      disabled={!draft?.id || applyMutation.isPending || !(draft?.stats?.placed_slots > 0)}
                      onClick={() => applyMutation.mutate(draft.id)}
                    >
                      <FiCheck size={14} /> {applyMutation.isPending ? 'Applying…' : 'Use it'}
                    </button>
                  </div>
                </div>
                <StatsBar stats={draft?.stats} warnings={draft?.warnings} />
                <PreviewGrid slots={draft?.slots || []} />
                <div className="small text-muted mt-3 d-flex align-items-center gap-1">
                  <FiLock size={12} />
                  After you use it, the schedule is locked for the term/exam session — only school admins can edit or delete.
                </div>
              </div>
            )}

            <div className="d-flex justify-content-between mt-4 pt-3 border-top">
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                disabled={step === 0}
                onClick={() => setStep((s) => Math.max(0, s - 1))}
              >
                Back
              </button>
              {step < 3 && (
                <button
                  type="button"
                  className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
                  onClick={() => setStep((s) => s + 1)}
                  disabled={
                    (step === 1 && scheduleType === 'exam' && !sessionId)
                    || (step === 1 && scheduleType === 'lesson' && !readiness.has_active_term)
                  }
                >
                  Continue <FiArrowRight size={14} />
                </button>
              )}
              {step === 3 && (
                <button
                  type="button"
                  className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
                  onClick={runGenerate}
                  disabled={generateMutation.isPending || periodIds.length === 0}
                >
                  <FiZap size={14} /> {generateMutation.isPending ? 'Generating…' : 'Generate draft'}
                </button>
              )}
              {step === 4 && (
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={() => { setDraft(null); setStep(0); }}
                >
                  Start over
                </button>
              )}
            </div>
          </>
        )}
      </div>

      <div className="apex-card p-3 p-md-4">
        <div className="d-flex align-items-center justify-content-between mb-3">
          <h5 className="fw-bold mb-0">Published schedules</h5>
          <Link to="/school-admin/academics/periods" className="small">Manage periods</Link>
        </div>
        {!schedules.length ? (
          <ModuleEmptyState
            title="No published timetables yet"
            message="Run the wizard above to generate a lesson or exam timetable."
          />
        ) : (
          <div className="table-responsive">
            <table className="table align-middle mb-0">
              <thead>
                <tr className="small text-muted">
                  <th>Name</th>
                  <th>Type</th>
                  <th>Scope</th>
                  <th>Slots</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {schedules.map((s) => (
                  <tr key={s.id}>
                    <td className="fw-medium">{s.name}</td>
                    <td className="text-capitalize">{s.schedule_type}</td>
                    <td className="small">
                      {s.term_name || s.examination_session_name || '—'}
                    </td>
                    <td>{s.entry_count ?? '—'}</td>
                    <td>
                      <span className="badge text-bg-primary-subtle border text-primary text-capitalize">
                        {s.status}{s.is_locked ? ' · locked' : ''}
                      </span>
                    </td>
                    <td className="text-end">
                      {isSchoolAdmin && (
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-danger"
                          onClick={() => deleteScheduleMutation.mutate(s.id)}
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default TimetableWizard;
