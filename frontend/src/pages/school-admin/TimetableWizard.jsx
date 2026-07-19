import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  FiArrowLeft, FiArrowRight, FiCheck, FiClock, FiDownload, FiEdit2, FiEye,
  FiFileText, FiLock, FiPlus, FiPrinter, FiSave, FiSend, FiTrash2,
  FiAlertTriangle, FiUnlock, FiChevronDown, FiChevronUp, FiCalendar,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import SearchableSelect from '../../components/SearchableSelect';
import { Modal } from '../../components/Modal';
import { timetableWizardService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { alert, extractApiError, notify } from '../../utils/notify';

const STEPS = [
  { key: 'periods', label: 'Periods' },
  { key: 'class', label: 'Class' },
  { key: 'grid', label: 'Fill grid' },
  { key: 'publish', label: 'Save & publish' },
];

const DAY_OPTIONS = [
  { value: 0, label: 'Mon' },
  { value: 1, label: 'Tue' },
  { value: 2, label: 'Wed' },
  { value: 3, label: 'Thu' },
  { value: 4, label: 'Fri' },
  { value: 5, label: 'Sat' },
  { value: 6, label: 'Sun' },
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

function defaultPeriodTemplate() {
  return [
    { id: null, name: 'Period 1', start_time: '08:00', end_time: '08:40', sort_order: 1, is_break: false },
    { id: null, name: 'Period 2', start_time: '08:40', end_time: '09:20', sort_order: 2, is_break: false },
    { id: null, name: 'Break', start_time: '09:20', end_time: '09:40', sort_order: 3, is_break: true },
    { id: null, name: 'Period 3', start_time: '09:40', end_time: '10:20', sort_order: 4, is_break: false },
    { id: null, name: 'Period 4', start_time: '10:20', end_time: '11:00', sort_order: 5, is_break: false },
  ];
}

function normalizeTime(value) {
  if (!value) return '';
  const s = String(value).trim();
  return s.length >= 5 ? s.slice(0, 5) : s;
}

/** day:periodId:streamId (streamId empty when single-stream) — always string keys */
function cellKey(day, periodId, streamId = '') {
  return `${String(day)}:${String(periodId || '')}:${String(streamId || '')}`;
}

/** Find a cell even if stream/period id typing differs slightly */
function findCell(cellsMap, day, periodId, streamId = '') {
  const exact = cellsMap[cellKey(day, periodId, streamId)];
  if (exact) return exact;
  const d = String(day);
  const p = String(periodId || '');
  const s = String(streamId || '');
  return (
    Object.values(cellsMap).find(
      (c) =>
        String(c.day_of_week) === d
        && String(c.period_id || '') === p
        && String(c.stream_id || '') === s,
    ) || null
  );
}

function StatusBadge({ status, isPublished }) {
  const published = isPublished || status === 'published' || status === 'active';
  if (published) {
    return (
      <span className="badge rounded-pill text-bg-success-subtle border border-success-subtle text-success px-2 py-1">
        Published
      </span>
    );
  }
  if (status === 'archived') {
    return (
      <span className="badge rounded-pill text-bg-secondary-subtle border text-secondary px-2 py-1">
        Archived
      </span>
    );
  }
  return (
    <span className="badge rounded-pill text-bg-warning-subtle border border-warning-subtle text-warning-emphasis px-2 py-1">
      Draft
    </span>
  );
}

function formatWhen(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  } catch {
    return iso;
  }
}

/** Teacher shown as text + pen to open picker (no native select arrow). */
function TeacherPenPicker({ teacherId, teacherName, teachers, onChange, disabled }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  return (
    <div className="position-relative" ref={ref}>
      <div className="d-flex align-items-center gap-1 small border rounded px-1 py-0 bg-white" style={{ minHeight: 28 }}>
        <span className="text-truncate flex-grow-1" style={{ maxWidth: 100 }} title={teacherName || ''}>
          {teacherName || <span className="text-muted">No teacher</span>}
        </span>
        {!disabled && (
          <button
            type="button"
            className="btn btn-link btn-sm p-0 text-primary"
            title="Change teacher"
            onClick={() => setOpen((v) => !v)}
          >
            <FiEdit2 size={13} />
          </button>
        )}
      </div>
      {open && (
        <div
          className="position-absolute bg-white border rounded shadow-sm p-1"
          style={{ zIndex: 20, left: 0, right: 0, minWidth: 140, maxHeight: 180, overflowY: 'auto' }}
        >
          <button
            type="button"
            className="dropdown-item small py-1 px-2"
            onClick={() => { onChange(null, ''); setOpen(false); }}
          >
            — clear —
          </button>
          {teachers.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`dropdown-item small py-1 px-2 ${t.id === teacherId ? 'active' : ''}`}
              onClick={() => { onChange(t.id, t.name); setOpen(false); }}
            >
              {t.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function emptyExamRow() {
  return {
    _key: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    exam_date: '',
    start_time: '09:00',
    end_time: '11:00',
    school_class_id: '',
    subject_id: '',
    teacher_id: '',
    teacher_name: '',
    room: '',
  };
}

export function TimetableWizard() {
  const queryClient = useQueryClient();
  const { canWriteFeature, isSchoolAdmin } = usePermissions();
  const canEdit = isSchoolAdmin || canWriteFeature('timetables');

  /** lesson | exam — dual workspace in same submodule */
  const [mode, setMode] = useState('lesson');
  const [step, setStep] = useState(0);
  const [periodRows, setPeriodRows] = useState([]);
  const [schoolClass, setSchoolClass] = useState('');
  const [stream, setStream] = useState('');
  const [workingDays, setWorkingDays] = useState([0, 1, 2, 3, 4]);
  const [cellsMap, setCellsMap] = useState({});
  const cellsMapRef = useRef({});
  const [multiStream, setMultiStream] = useState(false);
  const [classStreams, setClassStreams] = useState([]);
  const [scheduleMeta, setScheduleMeta] = useState(null);
  const [conflicts, setConflicts] = useState([]);
  const [busy, setBusy] = useState(false);
  const [printClassIds, setPrintClassIds] = useState([]);
  const [printOrientation, setPrintOrientation] = useState('landscape');
  const [printScope, setPrintScope] = useState('class');
  const [libraryFilter, setLibraryFilter] = useState('all'); // all | draft | published
  const [builderOpen, setBuilderOpen] = useState(false);
  const [preview, setPreview] = useState(null); // schedule detail
  const [previewLoading, setPreviewLoading] = useState(false);
  // Exam builder state
  const [examSlots, setExamSlots] = useState([]);
  const [examSessionId, setExamSessionId] = useState('');
  const [examConflicts, setExamConflicts] = useState([]);
  /** Teacher personal view: 'all' | 'highlight' (Show mine) | 'mine_only' (Mine only) */
  const [teacherViewMode, setTeacherViewMode] = useState('all');

  const { data: context, isLoading, isError, refetch } = useQuery({
    queryKey: ['timetable-wizard-context'],
    queryFn: () => timetableWizardService.getWizardContext(),
    enabled: mode === 'lesson',
  });

  const {
    data: examContext,
    isLoading: examCtxLoading,
    isError: examCtxError,
    refetch: refetchExamCtx,
  } = useQuery({
    queryKey: ['exam-timetable-context'],
    queryFn: () => timetableWizardService.getExamContext(),
    enabled: mode === 'exam',
  });

  const {
    data: scheduleLibrary,
    isLoading: schedulesLoading,
    refetch: refetchSchedules,
  } = useQuery({
    queryKey: ['timetable-schedules', mode],
    queryFn: () => timetableWizardService.listSchedules({ schedule_type: mode }),
    staleTime: 15_000,
  });

  const schedules = scheduleLibrary?.results || [];
  const scheduleSummary = scheduleLibrary?.summary || {};

  const termId = (mode === 'exam' ? examContext?.active_term?.id : context?.active_term?.id) || '';
  const classes = (mode === 'exam' ? examContext?.classes : context?.classes) || [];
  const subjects = (mode === 'exam' ? examContext?.subjects : context?.subjects) || [];
  const teachers = (mode === 'exam' ? examContext?.teachers : context?.teachers) || [];
  const assignmentsByClass = context?.assignments_by_class || {};
  const teacherForPair = context?.teacher_for_pair || {};
  const examSessions = examContext?.examination_sessions || [];
  const publishedBusy = examContext?.published_busy || [];
  const viewerTeacherId = (
    preview?.viewer_teacher_id
    || context?.viewer_teacher_id
    || examContext?.viewer_teacher_id
    || ''
  );
  const viewerTeacherName = (
    preview?.viewer_teacher_name
    || context?.viewer_teacher_name
    || examContext?.viewer_teacher_name
    || ''
  );
  /** Staff with a teacher profile (typical teacher role) get personal view toggles */
  const canUseTeacherView = Boolean(viewerTeacherId);

  const switchMode = (next) => {
    if (next === mode) return;
    setMode(next);
    setScheduleMeta(null);
    setBuilderOpen(false);
    setConflicts([]);
    setExamConflicts([]);
    setExamSlots([]);
    setPreview(null);
    setStep(0);
    setLibraryFilter('all');
  };

  useEffect(() => {
    if (!context) return;
    if (periodRows.length > 0) return;
    if (context.periods?.length) {
      setPeriodRows(context.periods.map((p, i) => ({
        id: p.id,
        name: p.name,
        start_time: normalizeTime(p.start_time),
        end_time: normalizeTime(p.end_time),
        sort_order: p.sort_order ?? i + 1,
        is_break: !!p.is_break,
      })));
    } else {
      setPeriodRows(defaultPeriodTemplate());
    }
  }, [context]); // eslint-disable-line react-hooks/exhaustive-deps

  const classOptions = useMemo(() => classes.map((c) => ({
    value: c.id,
    label: `${c.name}${c.code ? ` (${c.code})` : ''}`,
    meta: c.has_timetable ? `${c.filled_slots} slots` : `${c.assignment_count} subject(s)`,
  })), [classes]);

  const streamOptions = useMemo(() => {
    const c = classes.find((x) => x.id === schoolClass);
    return (c?.streams || []).map((s) => ({ value: s.id, label: s.name }));
  }, [classes, schoolClass]);

  const subjectOptions = useMemo(() => {
    const assigned = assignmentsByClass[schoolClass] || [];
    if (assigned.length) {
      return assigned.map((a) => ({
        value: a.subject_id,
        label: a.subject_name,
        meta: a.teacher_name || a.subject_code,
      }));
    }
    return subjects.map((s) => ({ value: s.id, label: s.name, meta: s.code }));
  }, [assignmentsByClass, schoolClass, subjects]);

  const periodsForGrid = useMemo(() => {
    if (periodRows.length) {
      return [...periodRows].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
    }
    return context?.periods || [];
  }, [periodRows, context]);

  const daysSorted = useMemo(() => [...workingDays].sort((a, b) => a - b), [workingDays]);

  // Keep a ref in sync so Save never reads a stale cellsMap closure
  useEffect(() => {
    cellsMapRef.current = cellsMap;
  }, [cellsMap]);

  const loadGrid = useCallback(async () => {
    if (!schoolClass) return;
    setBusy(true);
    try {
      const data = await timetableWizardService.getClassGrid({
        school_class: schoolClass,
        term: termId || undefined,
        stream: stream || undefined,
        days: workingDays.join(','),
      });
      const map = {};
      (data.cells || []).forEach((cell) => {
        const key = cellKey(cell.day_of_week, cell.period_id, cell.stream_id);
        map[key] = {
          ...cell,
          day_of_week: Number(cell.day_of_week),
          period_id: cell.period_id != null ? String(cell.period_id) : null,
          stream_id: cell.stream_id != null && cell.stream_id !== '' ? String(cell.stream_id) : null,
          subject_id: cell.subject_id != null && cell.subject_id !== '' ? String(cell.subject_id) : null,
          teacher_id: cell.teacher_id != null && cell.teacher_id !== '' ? String(cell.teacher_id) : null,
          subject_name: cell.subject_name || cell.display_subject || '',
          teacher_name: cell.teacher_name || cell.display_teacher || '',
        };
      });
      cellsMapRef.current = map;
      setCellsMap(map);
      setMultiStream(!!data.multi_stream);
      setClassStreams((data.streams || []).map((s) => ({ id: String(s.id), name: s.name })));
      setScheduleMeta(data.schedule || null);
      setConflicts([]);
      // Align local period rows with server periods so ids always match save payload
      if (data.periods?.length) {
        setPeriodRows(data.periods.map((pr, i) => ({
          id: String(pr.id),
          name: pr.name,
          start_time: normalizeTime(pr.start_time),
          end_time: normalizeTime(pr.end_time),
          sort_order: pr.sort_order ?? i + 1,
          is_break: !!pr.is_break,
        })));
      }
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to load class grid.'));
    } finally {
      setBusy(false);
    }
  }, [schoolClass, termId, stream, workingDays]);

  useEffect(() => {
    if (step === 2 && schoolClass) loadGrid();
  }, [step, schoolClass, stream]); // eslint-disable-line react-hooks/exhaustive-deps

  const updateCell = (day, periodId, streamId, patch) => {
    const sid = streamId ? String(streamId) : '';
    const pid = String(periodId || '');
    const key = cellKey(day, pid, sid);
    setCellsMap((prev) => {
      const base = findCell(prev, day, pid, sid) || {
        day_of_week: Number(day),
        period_id: pid,
        stream_id: sid || null,
        is_break: false,
        is_empty: true,
      };
      const next = {
        ...base,
        ...patch,
        day_of_week: Number(day),
        period_id: pid,
        stream_id: sid || null,
        subject_id: patch.subject_id != null && patch.subject_id !== ''
          ? String(patch.subject_id)
          : (patch.subject_id === null ? null : base.subject_id),
        teacher_id: patch.teacher_id != null && patch.teacher_id !== ''
          ? String(patch.teacher_id)
          : (patch.teacher_id === null ? null : base.teacher_id),
      };
      next.is_empty = !(next.subject_id || next.is_break);
      const merged = { ...prev, [key]: next };
      cellsMapRef.current = merged;
      return merged;
    });
  };

  const onSubjectChange = async (day, periodId, streamId, subjectId) => {
    const sid = streamId ? String(streamId) : '';
    const pid = String(periodId || '');
    if (!subjectId) {
      updateCell(day, pid, sid, {
        subject_id: null,
        subject_name: '',
        subject_code: '',
        teacher_id: null,
        teacher_name: '',
        is_empty: true,
      });
      return;
    }
    const subjId = String(subjectId);
    const subj = subjects.find((s) => String(s.id) === subjId)
      || (assignmentsByClass[schoolClass] || []).find((a) => String(a.subject_id) === subjId);
    const pairKey = `${schoolClass}:${subjId}`;
    const auto = teacherForPair[pairKey];
    let teacher_id = auto?.teacher_id ? String(auto.teacher_id) : null;
    let teacher_name = auto?.teacher_name || '';
    if (!teacher_id) {
      try {
        const def = await timetableWizardService.defaultTeacher({
          school_class: schoolClass,
          subject: subjId,
        });
        if (def?.teacher_id) {
          teacher_id = String(def.teacher_id);
          teacher_name = def.teacher_name || '';
        }
      } catch { /* optional */ }
    }
    updateCell(day, pid, sid, {
      subject_id: subjId,
      subject_name: subj?.name || subj?.subject_name || '',
      subject_code: subj?.code || subj?.subject_code || '',
      teacher_id,
      teacher_name,
      is_empty: false,
      is_break: false,
    });
  };

  useEffect(() => {
    if (step !== 2 || !schoolClass) return undefined;
    const t = setTimeout(async () => {
      try {
        const data = await timetableWizardService.validateGrid({
          school_class: schoolClass,
          term: termId,
          stream: stream || undefined,
          cells: Object.values(cellsMap),
        });
        setConflicts(data.conflicts || []);
      } catch { /* soft */ }
    }, 500);
    return () => clearTimeout(t);
  }, [cellsMap, step, schoolClass]); // eslint-disable-line react-hooks/exhaustive-deps

  const savePeriods = async () => {
    for (let i = 0; i < periodRows.length; i += 1) {
      const r = periodRows[i];
      if (!r.start_time || !r.end_time) {
        notify.error(`Period ${i + 1}: set both From and To times.`);
        return;
      }
      if (normalizeTime(r.end_time) <= normalizeTime(r.start_time)) {
        notify.error(`"${r.name || `Period ${i + 1}`}": To must be after From.`);
        return;
      }
    }
    setBusy(true);
    try {
      const payload = periodRows.map((r, i) => ({
        id: r.id || undefined,
        name: (r.name || '').trim() || `Period ${i + 1}`,
        start_time: normalizeTime(r.start_time),
        end_time: normalizeTime(r.end_time),
        sort_order: i + 1,
        is_break: !!r.is_break,
      }));
      const data = await timetableWizardService.syncPeriods(payload);
      setPeriodRows((data.periods || []).map((p, i) => ({
        id: p.id,
        name: p.name,
        start_time: normalizeTime(p.start_time),
        end_time: normalizeTime(p.end_time),
        sort_order: p.sort_order ?? i + 1,
        is_break: !!p.is_break,
      })));
      await refetch();
      await queryClient.invalidateQueries({ queryKey: ['periods'] });
      notify.success('Periods saved.');
      setStep(1);
    } catch (err) {
      notify.error(err?.response?.data?.message || extractApiError(err, 'Could not save periods.'));
    } finally {
      setBusy(false);
    }
  };

  const streamIdsForPayload = () => {
    if (multiStream && classStreams.length) return classStreams.map((s) => String(s.id));
    if (stream) return [String(stream)];
    return [''];
  };

  const buildCellsPayload = () => {
    // Always read from ref — latest user selections, not a stale render closure
    const map = cellsMapRef.current || {};
    const periods = periodsForGrid.filter((p) => p.id).map((p) => ({
      ...p,
      id: String(p.id),
    }));
    const cells = [];
    const streamIds = streamIdsForPayload();
    const withSubject = [];

    daysSorted.forEach((day) => {
      periods.forEach((period) => {
        const sids = period.is_break
          ? (multiStream && classStreams.length ? classStreams.map((s) => String(s.id)) : [''])
          : streamIds;
        sids.forEach((sid) => {
          const cell = findCell(map, day, period.id, sid)
            || findCell(map, day, period.id, '')
            || {};
          // If this period is a break period in the bell schedule, no subject
          // BUT if user somehow assigned a subject, subject wins (backend also enforces this)
          const subject_id = cell.subject_id ? String(cell.subject_id) : null;
          const isBreak = !!period.is_break && !subject_id;
          const teacher_id = isBreak ? null : (cell.teacher_id ? String(cell.teacher_id) : null);
          const row = {
            day_of_week: Number(day),
            period_id: String(period.id),
            stream_id: sid || null,
            start_time: normalizeTime(period.start_time),
            end_time: normalizeTime(period.end_time),
            is_break: isBreak,
            is_break_slot: isBreak,
            subject_id: isBreak ? null : subject_id,
            teacher_id,
            subject_name: isBreak ? (period.name || 'Break') : (cell.subject_name || cell.display_subject || ''),
            teacher_name: isBreak ? '' : (cell.teacher_name || cell.display_teacher || ''),
            display_subject: isBreak ? '' : (cell.subject_name || cell.display_subject || ''),
            display_teacher: isBreak ? '' : (cell.teacher_name || cell.display_teacher || ''),
            slot_label: isBreak ? (period.name || 'Break') : '',
            room: cell.room || '',
          };
          cells.push(row);
          if (row.subject_id) withSubject.push(row);
        });
      });
    });

    // Fold any extra filled entries from the map (defensive)
    Object.values(map).forEach((c) => {
      if (!c?.subject_id || c.is_break) return;
      const exists = cells.some(
        (x) =>
          Number(x.day_of_week) === Number(c.day_of_week)
          && String(x.period_id) === String(c.period_id)
          && String(x.stream_id || '') === String(c.stream_id || ''),
      );
      if (!exists) {
        cells.push({
          day_of_week: Number(c.day_of_week),
          period_id: String(c.period_id),
          stream_id: c.stream_id ? String(c.stream_id) : null,
          start_time: c.start_time || '',
          end_time: c.end_time || '',
          is_break: false,
          is_break_slot: false,
          subject_id: String(c.subject_id),
          teacher_id: c.teacher_id ? String(c.teacher_id) : null,
          subject_name: c.subject_name || c.display_subject || '',
          teacher_name: c.teacher_name || c.display_teacher || '',
          display_subject: c.subject_name || c.display_subject || '',
          display_teacher: c.teacher_name || c.display_teacher || '',
          slot_label: '',
          room: c.room || '',
        });
        withSubject.push(c);
      }
    });

    if (withSubject.length === 0) {
      // eslint-disable-next-line no-console
      console.warn('[timetable] no teaching subjects in payload', {
        mapKeys: Object.keys(map),
        mapSample: Object.values(map).slice(0, 5),
        periods: periods.map((p) => p.id),
        streamIds,
      });
    }
    return cells;
  };

  const saveGrid = async (force = false) => {
    if (!schoolClass) return;
    if (!periodsForGrid.some((p) => p.id)) {
      notify.error('Save periods first (step 1).');
      setStep(0);
      return;
    }
    if (!termId) {
      notify.error('Activate an academic term first.');
      return;
    }
    if (!scheduleMeta?.id) {
      // Auto-create a draft so library always stays in sync
      try {
        const draft = await timetableWizardService.createDraft({ term: termId });
        setScheduleMeta({
          id: draft.id,
          status: draft.status || 'draft',
          is_published: false,
          name: draft.name,
        });
        await refetchSchedules();
      } catch (err) {
        notify.error(err?.response?.data?.message || extractApiError(err, 'Create a draft from the library first.'));
        return;
      }
    }
    setBusy(true);
    try {
      const cells = buildCellsPayload();
      const teachingInPayload = cells.filter((c) => c.subject_id && !c.is_break).length;
      if (teachingInPayload === 0) {
        const result = await alert.confirm({
          title: 'No subjects selected',
          text: 'The grid has no teaching subjects. Save breaks and empty slots only?',
          confirmText: 'Save empty grid',
          cancelText: 'Keep editing',
          icon: 'warning',
        });
        if (!result.isConfirmed) {
          setBusy(false);
          return;
        }
      }
      const data = await timetableWizardService.saveClassGrid({
        school_class: schoolClass,
        term: termId,
        stream: multiStream ? undefined : (stream || undefined),
        working_days: workingDays,
        cells,
        force,
        schedule_id: scheduleMeta?.id || undefined,
      });
      setScheduleMeta({
        id: data.schedule_id,
        status: data.schedule_status,
        is_published: data.is_published,
      });
      await refetchSchedules();
      const n = data?.subjects_saved ?? data?.created_teaching ?? 0;
      if (teachingInPayload > 0 && n === 0) {
        notify.error(
          `Save reported 0 teaching slots (browser sent ${teachingInPayload}, `
          + `server received_with_subject=${data?.received_with_subject ?? '?'}, `
          + `skipped_period=${data?.skipped_unknown_period ?? 0}). `
          + 'Re-select subjects and save again.',
        );
      } else {
        notify.success(
          n > 0
            ? `Draft saved (${n} teaching slot(s)`
              + (data?.created_breaks ? `, ${data.created_breaks} break(s)` : '')
              + ').'
            : 'Draft saved (breaks/empty only — select subjects then save again).',
        );
      }
      await refetch();
      await loadGrid();
    } catch (err) {
      const msg = err?.response?.data?.message || extractApiError(err, 'Save failed.');
      const conflictsList = err?.response?.data?.conflicts;
      if (conflictsList?.length) {
        setConflicts(conflictsList);
        const result = await alert.confirm({
          title: 'Teacher / slot conflicts',
          text: `${msg} You can still force-save if you accept the clashes.`,
          confirmText: 'Save anyway',
          cancelText: 'Fix conflicts',
          icon: 'warning',
          danger: true,
        });
        if (result.isConfirmed) await saveGrid(true);
      } else {
        notify.error(msg);
      }
    } finally {
      setBusy(false);
    }
  };

  const publish = async () => {
    setBusy(true);
    try {
      const data = await timetableWizardService.publish({
        term: termId,
        schedule_id: scheduleMeta?.id,
      });
      setScheduleMeta((m) => ({ ...(m || {}), ...data, is_published: true, status: 'published' }));
      notify.success('Timetable published — teachers can view and download it.');
      await queryClient.invalidateQueries({ queryKey: ['timetable-schedules'] });
      await refetchSchedules();
    } catch (err) {
      notify.error(err?.response?.data?.message || extractApiError(err, 'Publish failed.'));
    } finally {
      setBusy(false);
    }
  };

  const unpublish = async () => {
    if (!scheduleMeta?.id) return;
    const result = await alert.confirm({
      title: 'Unpublish timetable?',
      text: 'Return this timetable to draft? Teachers will lose access until it is published again.',
      confirmText: 'Yes, unpublish',
      cancelText: 'Keep published',
      icon: 'warning',
    });
    if (!result.isConfirmed) return;
    setBusy(true);
    try {
      const data = await timetableWizardService.unpublish({ schedule_id: scheduleMeta.id });
      setScheduleMeta((m) => ({ ...(m || {}), ...data, is_published: false, status: 'draft' }));
      notify.success('Timetable is draft again. You can edit freely.');
      await refetchSchedules();
    } catch (err) {
      notify.error(err?.response?.data?.message || extractApiError(err, 'Unpublish failed.'));
    } finally {
      setBusy(false);
    }
  };

  const downloadPdf = async (opts = {}) => {
    const scheduleId = opts.scheduleId || scheduleMeta?.id || undefined;
    const isExam = opts.scheduleType === 'exam'
      || mode === 'exam'
      || opts.isExam
      || scheduleMeta?.schedule_type === 'exam';
    if (isExam && !scheduleId) {
      notify.error('Select or open an exam timetable to print.');
      return;
    }

    setBusy(true);
    // Fire-and-forget loader — do not await (would block the download)
    alert.loading({
      title: 'Preparing PDF…',
      text: isExam ? 'Building exam timetable printout' : 'Building timetable printout',
    });

    try {
      const mineMode = opts.teacherViewMode ?? teacherViewMode;
      const teacherParams = (canUseTeacherView && mineMode && mineMode !== 'all')
        ? {
          teacher_mode: mineMode === 'highlight' ? 'highlight' : 'mine_only',
          teacher_id: viewerTeacherId,
        }
        : {};
      let blob;
      if (isExam) {
        blob = await timetableWizardService.printExamPdf({
          schedule: scheduleId,
          orientation: opts.orientation || printOrientation,
          ...teacherParams,
        });
      } else {
        let classIds = [];
        if (!opts.scheduleId) {
          if (printScope === 'class' && schoolClass) classIds = [schoolClass];
          if (printScope === 'selected') classIds = printClassIds;
        }
        blob = await timetableWizardService.printPdf({
          term: opts.termId || termId || undefined,
          orientation: opts.orientation || printOrientation,
          days: workingDays.join(','),
          school_class: classIds.length ? classIds : undefined,
          schedule: scheduleId,
          ...teacherParams,
        });
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${isExam ? 'exam-' : ''}timetable-${scheduleId ? 'schedule' : printScope}-${opts.orientation || printOrientation}.pdf`;
      a.click();
      // Revoke on next tick so the browser can start the download first
      setTimeout(() => URL.revokeObjectURL(url), 1500);
      alert.close();
      notify.success('PDF ready — download started.');
    } catch (err) {
      alert.close();
      notify.error(extractApiError(err, 'Print failed.'));
    } finally {
      setBusy(false);
    }
  };

  const openPreview = async (scheduleId) => {
    setPreviewLoading(true);
    try {
      const data = await timetableWizardService.getSchedule(scheduleId);
      setPreview(data);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to load preview.'));
    } finally {
      setPreviewLoading(false);
    }
  };

  const loadExamSlots = async (scheduleId) => {
    if (!scheduleId) return;
    setBusy(true);
    try {
      const data = await timetableWizardService.getExamSlots({ schedule: scheduleId });
      const rows = (data.slots || []).map((s) => ({
        _key: s.id || `${s.exam_date}-${s.start_time}-${s.school_class_id}`,
        exam_date: s.exam_date || '',
        start_time: s.start_time || '09:00',
        end_time: s.end_time || '11:00',
        school_class_id: s.school_class_id || '',
        subject_id: s.subject_id || '',
        teacher_id: s.teacher_id || '',
        teacher_name: s.teacher_name || '',
        room: s.room || '',
      }));
      setExamSlots(rows.length ? rows : [emptyExamRow()]);
      if (data.schedule) {
        setScheduleMeta({
          id: data.schedule.id,
          status: data.schedule.status,
          is_published: data.schedule.is_published,
          name: data.schedule.name,
          schedule_type: 'exam',
        });
      }
      setExamConflicts([]);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to load exam sittings.'));
    } finally {
      setBusy(false);
    }
  };

  const continueEditing = (sched) => {
    const perms = sched.permissions || {};
    if (perms.can_edit === false) {
      notify.error('Only a school admin can edit a published timetable.');
      return;
    }
    const isExam = sched.schedule_type === 'exam' || mode === 'exam';
    setScheduleMeta({
      id: sched.id,
      status: sched.status,
      is_published: sched.is_published,
      name: sched.name,
      schedule_type: isExam ? 'exam' : 'lesson',
    });
    setBuilderOpen(true);
    if (isExam) {
      loadExamSlots(sched.id);
      notify.success(`Editing exam timetable “${sched.name}”.`);
    } else {
      setStep(1);
      notify.success(`Editing “${sched.name}”. Select a class, update the grid, then Save draft.`);
    }
  };

  const startNewDraft = async () => {
    if (mode === 'exam') {
      setBusy(true);
      try {
        const draft = await timetableWizardService.createExamDraft({
          term: termId || undefined,
          examination_session: examSessionId || undefined,
          name: '',
        });
        setScheduleMeta({
          id: draft.id,
          status: draft.status || 'draft',
          is_published: false,
          name: draft.name,
          schedule_type: 'exam',
        });
        setExamSlots([emptyExamRow()]);
        setBuilderOpen(true);
        await refetchSchedules();
        notify.success(`Exam draft “${draft.name}” created.`);
      } catch (err) {
        notify.error(err?.response?.data?.message || extractApiError(err, 'Could not create exam draft.'));
      } finally {
        setBusy(false);
      }
      return;
    }
    if (!termId) {
      notify.error('Activate an academic term first.');
      return;
    }
    setBusy(true);
    try {
      const draft = await timetableWizardService.createDraft({
        term: termId,
        name: '',
      });
      setScheduleMeta({
        id: draft.id,
        status: draft.status || 'draft',
        is_published: false,
        name: draft.name,
        schedule_type: 'lesson',
      });
      setBuilderOpen(true);
      setStep(0);
      await refetchSchedules();
      notify.success(`Draft “${draft.name}” created — it is in the library above.`);
    } catch (err) {
      notify.error(err?.response?.data?.message || extractApiError(err, 'Could not create draft.'));
    } finally {
      setBusy(false);
    }
  };

  const saveExamGrid = async (force = false) => {
    if (!scheduleMeta?.id) {
      notify.error('Create or open an exam draft first.');
      return;
    }
    const slots = examSlots
      .filter((r) => r.exam_date && r.start_time && r.end_time && r.school_class_id && r.subject_id)
      .map((r) => {
        const t = teachers.find((x) => String(x.id) === String(r.teacher_id));
        const subj = subjects.find((x) => String(x.id) === String(r.subject_id));
        const cls = classes.find((x) => String(x.id) === String(r.school_class_id));
        return {
          exam_date: r.exam_date,
          start_time: r.start_time,
          end_time: r.end_time,
          school_class_id: r.school_class_id,
          subject_id: r.subject_id,
          teacher_id: r.teacher_id || null,
          teacher_name: r.teacher_name || t?.name || '',
          subject_name: subj?.name || '',
          room: r.room || cls?.room || '',
        };
      });
    if (!slots.length) {
      notify.error('Add at least one complete sitting (date, time, class, subject).');
      return;
    }
    setBusy(true);
    try {
      const data = await timetableWizardService.saveExamSlots({
        schedule_id: scheduleMeta.id,
        slots,
        force,
      });
      setExamConflicts(data?.validation?.conflicts || []);
      await refetchSchedules();
      notify.success(`Saved ${data.entries_created || slots.length} exam sitting(s).`);
      await loadExamSlots(scheduleMeta.id);
    } catch (err) {
      const msg = err?.response?.data?.message || extractApiError(err, 'Save failed.');
      const conflictsList = err?.response?.data?.conflicts;
      if (conflictsList?.length) {
        setExamConflicts(conflictsList);
        const result = await alert.confirm({
          title: 'Exam sitting conflicts',
          text: `${msg} Force-save only if you accept the clashes with published schedules.`,
          confirmText: 'Save anyway',
          cancelText: 'Fix conflicts',
          icon: 'warning',
          danger: true,
        });
        if (result.isConfirmed) await saveExamGrid(true);
      } else {
        notify.error(msg);
      }
    } finally {
      setBusy(false);
    }
  };

  const publishExam = async () => {
    if (!scheduleMeta?.id) return;
    setBusy(true);
    try {
      const data = await timetableWizardService.publishExam({ schedule_id: scheduleMeta.id });
      setScheduleMeta((m) => ({ ...(m || {}), ...data, is_published: true, status: 'published', schedule_type: 'exam' }));
      notify.success('Exam timetable published.');
      await refetchSchedules();
    } catch (err) {
      notify.error(err?.response?.data?.message || extractApiError(err, 'Publish failed.'));
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteSchedule = async (sched) => {
    const perms = sched.permissions || {};
    if (perms.can_delete === false && !isSchoolAdmin) {
      notify.error('You cannot delete this timetable.');
      return;
    }
    const result = await alert.delete(`“${sched.name}”`);
    if (!result.isConfirmed) return;
    setBusy(true);
    try {
      await timetableWizardService.deleteSchedule(sched.id);
      notify.success('Timetable deleted.');
      await refetchSchedules();
      if (scheduleMeta?.id === sched.id) setScheduleMeta(null);
    } catch (err) {
      notify.error(extractApiError(err, 'Delete failed.'));
    } finally {
      setBusy(false);
    }
  };

  const handlePublishSchedule = async (sched) => {
    setBusy(true);
    try {
      if (sched.schedule_type === 'exam' || mode === 'exam') {
        await timetableWizardService.publishExam({ schedule_id: sched.id });
      } else {
        await timetableWizardService.publish({ schedule_id: sched.id, term: sched.term_id });
      }
      notify.success('Timetable published — teachers can view and download it.');
      await refetchSchedules();
    } catch (err) {
      notify.error(err?.response?.data?.message || extractApiError(err, 'Publish failed.'));
    } finally {
      setBusy(false);
    }
  };

  const handleUnpublishSchedule = async (sched) => {
    const result = await alert.confirm({
      title: 'Unpublish timetable?',
      text: `Return “${sched.name}” to draft? Teachers will lose access until it is published again.`,
      confirmText: 'Yes, unpublish',
      cancelText: 'Keep published',
      icon: 'warning',
    });
    if (!result.isConfirmed) return;
    setBusy(true);
    try {
      await timetableWizardService.unpublish({ schedule_id: sched.id });
      notify.success('Timetable is draft again.');
      await refetchSchedules();
    } catch (err) {
      notify.error(err?.response?.data?.message || extractApiError(err, 'Unpublish failed.'));
    } finally {
      setBusy(false);
    }
  };

  const filteredSchedules = useMemo(() => {
    if (libraryFilter === 'draft') return schedules.filter((s) => s.status === 'draft');
    if (libraryFilter === 'published') return schedules.filter((s) => s.is_published);
    return schedules;
  }, [schedules, libraryFilter]);

  const published = scheduleMeta?.is_published || scheduleMeta?.status === 'published' || scheduleMeta?.status === 'active';
  const gridLocked = published && !isSchoolAdmin;

  /** Grid body rows: period × stream when multi-stream; breaks = one row only */
  const gridRows = useMemo(() => {
    const periods = periodsForGrid.filter((p) => p.id).map((p) => ({ ...p, id: String(p.id) }));
    if (multiStream && classStreams.length) {
      const rows = [];
      periods.forEach((period) => {
        if (period.is_break) {
          // Single break row — time + name once for all streams
          rows.push({
            period, stream: null, streamIndex: 0, streamCount: 1, isBreakRow: true,
          });
          return;
        }
        classStreams.forEach((st, si) => {
          rows.push({
            period,
            stream: { ...st, id: String(st.id) },
            streamIndex: si,
            streamCount: classStreams.length,
            isBreakRow: false,
          });
        });
      });
      return rows;
    }
    return periods.map((period) => ({
      period, stream: null, streamIndex: 0, streamCount: 1, isBreakRow: !!period.is_break,
    }));
  }, [periodsForGrid, multiStream, classStreams]);

  const librarySection = (
    <div className="apex-card p-3 p-md-4 mb-4">
      <div className="d-flex flex-wrap justify-content-between align-items-start gap-3 mb-3">
        <div>
          <h5 className="fw-bold mb-1 d-flex align-items-center gap-2">
            {mode === 'exam' ? <FiCalendar className="text-primary" /> : <FiFileText className="text-primary" />}
            {mode === 'exam' ? 'Exam timetable library' : 'Lesson timetable library'}
          </h5>
          <p className="text-muted small mb-0">
            {mode === 'exam'
              ? 'Date + time sittings with free invigilator pick. Constraints use published lesson and exam schedules.'
              : 'Review drafts and published schedules. Print includes a QR with scope, creator and dates.'}
            {isSchoolAdmin ? ' School admins can edit published ones.' : ' Only school admins can edit published ones.'}
          </p>
        </div>
        <div className="d-flex flex-wrap gap-2 align-items-center">
          <div className="btn-group btn-group-sm" role="group">
            {[
              { id: 'all', label: 'All' },
              { id: 'draft', label: `Drafts (${scheduleSummary.drafts ?? schedules.filter((s) => s.status === 'draft').length})` },
              { id: 'published', label: `Published (${scheduleSummary.published ?? schedules.filter((s) => s.is_published).length})` },
            ].map((f) => (
              <button
                key={f.id}
                type="button"
                className={`btn ${libraryFilter === f.id ? 'btn-primary' : 'btn-outline-secondary'}`}
                onClick={() => setLibraryFilter(f.id)}
              >
                {f.label}
              </button>
            ))}
          </div>
          {canEdit && (
            <button
              type="button"
              className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
              disabled={busy}
              onClick={startNewDraft}
            >
              <FiPlus size={14} /> {mode === 'exam' ? 'New exam draft' : 'New draft timetable'}
            </button>
          )}
        </div>
      </div>

      {schedulesLoading ? (
        <div className="text-center py-4 text-muted small">Loading schedules…</div>
      ) : !filteredSchedules.length ? (
        <div className="border border-dashed rounded-3 p-4 text-center bg-light-subtle">
          <FiClock className="text-muted mb-2" size={28} />
          <div className="fw-semibold">No {libraryFilter === 'all' ? '' : libraryFilter} {mode === 'exam' ? 'exam ' : ''}timetables yet</div>
          <p className="text-muted small mb-3">
            {canEdit
              ? (mode === 'exam'
                ? 'Create a draft, add exam sittings with date and time, then publish.'
                : 'Create periods and fill a class grid below, then save as draft or publish.')
              : 'When the school publishes a timetable, it will appear here for preview and download.'}
          </p>
          {canEdit && (
            <button type="button" className="btn btn-outline-primary btn-sm" disabled={busy} onClick={startNewDraft}>
              Create first draft
            </button>
          )}
        </div>
      ) : (
        <div className="row g-3">
          {filteredSchedules.map((sched) => {
            const perms = sched.permissions || {};
            const isPub = sched.is_published;
            const isExam = sched.schedule_type === 'exam' || mode === 'exam';
            return (
              <div key={sched.id} className="col-12 col-lg-6">
                <div className={`h-100 border rounded-3 p-3 bg-white shadow-sm ${isPub ? 'border-success-subtle' : ''}`}>
                  <div className="d-flex justify-content-between align-items-start gap-2 mb-2">
                    <div className="min-w-0">
                      <div className="fw-semibold text-truncate" title={sched.name}>{sched.name}</div>
                      <div className="small text-muted">
                        {isExam && sched.examination_session_name
                          ? sched.examination_session_name
                          : (sched.term_name || 'No term')}
                        {sched.academic_year_name ? ` · ${sched.academic_year_name}` : ''}
                        {sched.created_by_name ? ` · by ${sched.created_by_name}` : ''}
                      </div>
                    </div>
                    <div className="d-flex flex-column align-items-end gap-1">
                      <StatusBadge status={sched.status} isPublished={isPub} />
                      <span className="badge rounded-pill text-bg-light border small">
                        {isExam ? 'Exam' : 'Lesson'}
                      </span>
                    </div>
                  </div>
                  <div className="d-flex flex-wrap gap-3 small text-muted mb-3">
                    {isExam ? (
                      <>
                        <span><strong className="text-body">{sched.entry_count ?? 0}</strong> sittings</span>
                        <span><strong className="text-body">{sched.class_count ?? 0}</strong> classes</span>
                      </>
                    ) : (
                      <>
                        <span><strong className="text-body">{sched.teaching_count ?? 0}</strong> lessons</span>
                        <span><strong className="text-body">{sched.class_count ?? 0}</strong> classes</span>
                        <span>{sched.entry_count ?? 0} slots</span>
                      </>
                    )}
                  </div>
                  {!!sched.class_names?.length && (
                    <div className="small text-muted mb-3 text-truncate" title={sched.class_names.join(', ')}>
                      {sched.class_names.slice(0, 4).join(', ')}
                      {sched.class_names.length > 4 ? ` +${sched.class_names.length - 4}` : ''}
                    </div>
                  )}
                  <div className="small text-muted mb-3">
                    {isPub
                      ? `Published ${formatWhen(sched.published_at || sched.updated_at)}`
                      : `Updated ${formatWhen(sched.updated_at || sched.created_at)}`}
                    {isPub && !isSchoolAdmin && (
                      <span className="ms-2 text-warning-emphasis"><FiLock size={12} className="me-1" />Admin edit only</span>
                    )}
                  </div>
                  <div className="d-flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-primary d-inline-flex align-items-center gap-1"
                      disabled={busy || previewLoading}
                      onClick={() => openPreview(sched.id)}
                    >
                      <FiEye size={14} /> Preview
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-secondary d-inline-flex align-items-center gap-1"
                      disabled={busy}
                      onClick={() => downloadPdf({
                        scheduleId: sched.id,
                        termId: sched.term_id,
                        orientation: 'landscape',
                        scheduleType: isExam ? 'exam' : 'lesson',
                        teacherViewMode,
                      })}
                    >
                      <FiPrinter size={14} /> Print
                    </button>
                    {canEdit && perms.can_edit !== false && (
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-success d-inline-flex align-items-center gap-1"
                        disabled={busy}
                        onClick={() => continueEditing(sched)}
                      >
                        <FiEdit2 size={14} /> Edit
                      </button>
                    )}
                    {canEdit && perms.can_publish && (
                      <button
                        type="button"
                        className="btn btn-sm btn-success d-inline-flex align-items-center gap-1"
                        disabled={busy}
                        onClick={() => handlePublishSchedule(sched)}
                      >
                        <FiSend size={14} /> Publish
                      </button>
                    )}
                    {perms.can_unpublish && (
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-warning d-inline-flex align-items-center gap-1"
                        disabled={busy}
                        onClick={() => handleUnpublishSchedule(sched)}
                      >
                        <FiUnlock size={14} /> Unpublish
                      </button>
                    )}
                    {(perms.can_delete || isSchoolAdmin) && (
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-danger d-inline-flex align-items-center gap-1"
                        disabled={busy}
                        onClick={() => handleDeleteSchedule(sched)}
                      >
                        <FiTrash2 size={14} /> Delete
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );

  const previewIsExam = preview?.schedule_type === 'exam';
  const previewTeacherId = preview?.viewer_teacher_id || viewerTeacherId;
  const showTeacherToggles = Boolean(previewTeacherId || canUseTeacherView);

  const previewClasses = useMemo(() => {
    const groups = preview?.preview_by_class || [];
    if (!preview || teacherViewMode === 'all' || !previewTeacherId) return groups;
    return groups
      .map((cls) => {
        const slots = (cls.slots || []).map((slot) => {
          const isMine = slot.teacher_id && String(slot.teacher_id) === String(previewTeacherId);
          if (teacherViewMode === 'mine_only' && !slot.is_break && !isMine) {
            return {
              ...slot,
              subject: '',
              teacher: '',
              _blanked: true,
              _mine: false,
            };
          }
          return { ...slot, _mine: !!isMine, _blanked: false };
        });
        const hasMine = slots.some((s) => s._mine);
        if (teacherViewMode === 'mine_only' && !hasMine && !slots.some((s) => s.is_break && s.subject)) {
          // Keep class only if any of my lessons remain visible after blanking
          const anyMine = (cls.slots || []).some(
            (s) => s.teacher_id && String(s.teacher_id) === String(previewTeacherId),
          );
          if (!anyMine) return null;
        }
        return { ...cls, slots };
      })
      .filter(Boolean);
  }, [preview, teacherViewMode, previewTeacherId]);

  const teacherViewToggle = showTeacherToggles ? (
    <div className="d-flex flex-wrap align-items-center gap-2">
      <span className="small text-muted me-1">
        {viewerTeacherName ? `My periods (${viewerTeacherName})` : 'My periods'}
      </span>
      <div className="btn-group btn-group-sm" role="group" aria-label="Teacher view">
        {[
          { id: 'all', label: 'All' },
          { id: 'highlight', label: 'Show mine' },
          { id: 'mine_only', label: 'Mine only' },
        ].map((opt) => (
          <button
            key={opt.id}
            type="button"
            className={`btn ${teacherViewMode === opt.id ? 'btn-primary' : 'btn-outline-secondary'}`}
            onClick={() => setTeacherViewMode(opt.id)}
            title={
              opt.id === 'highlight'
                ? 'Highlight your teaching periods on the full timetable'
                : opt.id === 'mine_only'
                  ? 'Blank other teachers; show only your periods'
                  : 'Full timetable'
            }
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  ) : null;

  const previewModal = (
    <Modal
      show={Boolean(preview) || previewLoading}
      onHide={() => setPreview(null)}
      title={preview?.name || 'Timetable preview'}
      size="xl"
    >
      {previewLoading && !preview ? (
        <div className="text-center py-5 text-muted">Loading preview…</div>
      ) : preview ? (
        <div>
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
            <div className="small text-muted">
              <StatusBadge status={preview.status} isPublished={preview.is_published} />
              <span className="ms-2 badge text-bg-light border">{previewIsExam ? 'Exam' : 'Lesson'}</span>
              <span className="ms-2">{preview.examination_session_name || preview.term_name}</span>
              <span className="ms-2">· {previewIsExam ? `${preview.entry_count ?? 0} sittings` : `${preview.teaching_count ?? 0} lessons`}</span>
              <span className="ms-2">· {preview.class_count ?? 0} classes</span>
              {preview.created_by_name && <span className="ms-2">· by {preview.created_by_name}</span>}
            </div>
            <button
              type="button"
              className="btn btn-sm btn-primary"
              onClick={() => downloadPdf({
                scheduleId: preview.id,
                termId: preview.term_id,
                scheduleType: previewIsExam ? 'exam' : 'lesson',
                teacherViewMode,
              })}
            >
              <FiDownload className="me-1" /> Download PDF
            </button>
          </div>

          {showTeacherToggles && (
            <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3 p-2 border rounded-3 bg-light-subtle">
              {teacherViewToggle}
              <span className="small text-muted">
                {teacherViewMode === 'highlight' && 'Your periods are highlighted in amber.'}
                {teacherViewMode === 'mine_only' && 'Only your periods are shown; others are blank.'}
                {teacherViewMode === 'all' && 'Full school timetable.'}
              </span>
            </div>
          )}

          {previewClasses.length === 0 ? (
            <p className="text-muted small mb-0">
              {teacherViewMode === 'mine_only'
                ? 'No periods assigned to you on this timetable.'
                : 'No slots in this timetable yet.'}
            </p>
          ) : (
            <div className="d-flex flex-column gap-3" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
              {previewClasses.map((cls) => (
                <div key={cls.school_class_id} className="border rounded-3 overflow-hidden">
                  <div className="px-3 py-2 bg-light fw-semibold small border-bottom">
                    {cls.school_class_name}
                  </div>
                  <div className="table-responsive">
                    <table className="table table-sm table-striped mb-0 align-middle">
                      <thead>
                        <tr className="small text-muted">
                          {previewIsExam ? <th>Date</th> : <th>Day</th>}
                          <th>Time</th>
                          {!previewIsExam && <th>Stream</th>}
                          <th>Subject / break</th>
                          <th>{previewIsExam ? 'Invigilator' : 'Teacher'}</th>
                          {previewIsExam && <th>Room</th>}
                        </tr>
                      </thead>
                      <tbody>
                        {(cls.slots || []).slice(0, 80).map((slot, i) => {
                          const mineClass = slot._mine
                            ? 'table-warning'
                            : (slot._blanked ? 'opacity-50' : '');
                          return (
                            <tr
                              key={`${cls.school_class_id}-${i}`}
                              className={`${slot.is_break ? 'table-secondary' : ''} ${mineClass}`.trim()}
                            >
                              <td className="small">{previewIsExam ? (slot.exam_date || slot.day_label) : slot.day_label}</td>
                              <td className="small text-nowrap">{slot.start_time}–{slot.end_time}</td>
                              {!previewIsExam && <td className="small">{slot.stream_name || '—'}</td>}
                              <td className="small fw-medium">
                                {slot._blanked ? <span className="text-muted">—</span> : (slot.subject || '—')}
                              </td>
                              <td className="small text-muted">
                                {slot._blanked ? '' : (slot.teacher || (slot.is_break ? '' : '—'))}
                              </td>
                              {previewIsExam && <td className="small">{slot._blanked ? '—' : (slot.room || '—')}</td>}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                  {(cls.slots || []).length > 80 && (
                    <div className="px-3 py-2 small text-muted border-top">Showing first 80 slots — use Print for full PDF.</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </Modal>
  );

  const modeSwitcher = (
    <div className="apex-card p-2 p-md-3 mb-4">
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3">
        <div className="btn-group" role="group" aria-label="Timetable type">
          <button
            type="button"
            className={`btn ${mode === 'lesson' ? 'btn-primary' : 'btn-outline-secondary'}`}
            onClick={() => switchMode('lesson')}
          >
            <FiClock className="me-1" /> Lesson timetable
          </button>
          <button
            type="button"
            className={`btn ${mode === 'exam' ? 'btn-primary' : 'btn-outline-secondary'}`}
            onClick={() => switchMode('exam')}
          >
            <FiCalendar className="me-1" /> Examination timetable
          </button>
        </div>
        <div className="small text-muted">
          {mode === 'exam'
            ? 'Capture exam date, session time, class, subject and invigilator (free pick).'
            : 'Weekly periods grid with teachers from subject assignments.'}
        </div>
      </div>
    </div>
  );

  const examBuilder = (
    <div className="apex-card p-3 p-md-4 mb-4">
      <button
        type="button"
        className="btn btn-link text-decoration-none p-0 d-flex align-items-center gap-2 w-100 text-start"
        onClick={() => setBuilderOpen((v) => !v)}
      >
        {builderOpen ? <FiChevronUp /> : <FiChevronDown />}
        <span className="fw-bold text-body">Exam sitting builder</span>
        <span className="text-muted small fw-normal">
          Date + time · free invigilator · published constraints
        </span>
      </button>

      {builderOpen && (
        <>
          <hr className="my-3" />
          {scheduleMeta ? (
            <div className={`alert py-2 small ${published ? 'alert-success' : 'alert-secondary'}`}>
              Working on: <strong>{scheduleMeta.name || 'Exam timetable'}</strong>
              {' · '}
              <span className="text-capitalize">{scheduleMeta.status || 'draft'}</span>
              {published ? ' — published (school admin may still edit).' : ' — draft.'}
              {gridLocked && ' Editing locked for non-admins.'}
            </div>
          ) : (
            <div className="alert alert-info py-2 small">
              No exam draft selected. Click <strong>New exam draft</strong> above, or <strong>Edit</strong> a card.
            </div>
          )}

          {examCtxLoading ? (
            <div className="text-center py-5 text-muted">Loading exam context…</div>
          ) : examCtxError ? (
            <div className="alert alert-danger">Unable to load exam context.</div>
          ) : (
            <>
              <div className="row g-3 mb-3">
                <div className="col-md-5">
                  <label className="form-label small">Examination session (optional)</label>
                  <select
                    className="form-select form-select-sm"
                    value={examSessionId}
                    disabled={gridLocked}
                    onChange={(e) => setExamSessionId(e.target.value)}
                  >
                    <option value="">— active term only —</option>
                    {examSessions.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.start_date} → {s.end_date})
                      </option>
                    ))}
                  </select>
                  <div className="form-text">Used when creating a new draft; link sittings to a session.</div>
                </div>
                <div className="col-md-7 d-flex flex-wrap align-items-end gap-2">
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    disabled={busy || gridLocked}
                    onClick={() => setExamSlots((rows) => [...rows, emptyExamRow()])}
                  >
                    <FiPlus className="me-1" /> Add sitting
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={busy || gridLocked || !scheduleMeta?.id}
                    onClick={() => saveExamGrid(false)}
                  >
                    <FiSave className="me-1" /> {busy ? 'Saving…' : 'Save draft'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-success btn-sm"
                    disabled={busy || !scheduleMeta?.id}
                    onClick={publishExam}
                  >
                    <FiSend className="me-1" /> Publish
                  </button>
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    disabled={busy || !scheduleMeta?.id}
                    onClick={() => downloadPdf({ scheduleId: scheduleMeta?.id, scheduleType: 'exam' })}
                  >
                    <FiPrinter className="me-1" /> Print PDF
                  </button>
                </div>
              </div>

              {examConflicts.length > 0 && (
                <div className="alert alert-warning small">
                  <FiAlertTriangle className="me-1" />
                  <strong>{examConflicts.length} clash(es)</strong> with published schedules or within this draft
                  <ul className="mb-0 mt-1">
                    {examConflicts.slice(0, 8).map((c, i) => <li key={i}>{c.message}</li>)}
                  </ul>
                </div>
              )}

              {publishedBusy.length > 0 && (
                <div className="border rounded-3 p-2 mb-3 bg-light-subtle">
                  <div className="small fw-semibold mb-1">Published occupancy (constraints)</div>
                  <div className="small text-muted" style={{ maxHeight: 72, overflowY: 'auto' }}>
                    {publishedBusy.slice(0, 12).map((b, i) => (
                      <span key={i} className="me-3">
                        {b.teacher_name || 'Teacher'}
                        {b.exam_date ? ` · ${b.exam_date}` : ` · ${['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][b.day_of_week] || ''}`}
                        {' '}{b.start_time}–{b.end_time}
                        {' '}({b.class_name})
                      </span>
                    ))}
                    {publishedBusy.length > 12 ? ` +${publishedBusy.length - 12} more` : ''}
                  </div>
                </div>
              )}

              <div className="table-responsive border rounded">
                <table className="table table-sm align-middle mb-0">
                  <thead className="table-light">
                    <tr className="small text-muted">
                      <th style={{ minWidth: 130 }}>Date</th>
                      <th style={{ minWidth: 100 }}>From</th>
                      <th style={{ minWidth: 100 }}>To</th>
                      <th style={{ minWidth: 140 }}>Class</th>
                      <th style={{ minWidth: 140 }}>Subject</th>
                      <th style={{ minWidth: 150 }}>Invigilator</th>
                      <th style={{ minWidth: 90 }}>Room</th>
                      <th style={{ width: 44 }} />
                    </tr>
                  </thead>
                  <tbody>
                    {examSlots.map((row, idx) => (
                      <tr key={row._key}>
                        <td>
                          <input
                            type="date"
                            className="form-control form-control-sm"
                            value={row.exam_date}
                            disabled={gridLocked}
                            onChange={(e) => {
                              const next = [...examSlots];
                              next[idx] = { ...row, exam_date: e.target.value };
                              setExamSlots(next);
                            }}
                          />
                        </td>
                        <td>
                          <input
                            type="time"
                            className="form-control form-control-sm"
                            value={row.start_time}
                            disabled={gridLocked}
                            onChange={(e) => {
                              const next = [...examSlots];
                              next[idx] = { ...row, start_time: e.target.value };
                              setExamSlots(next);
                            }}
                          />
                        </td>
                        <td>
                          <input
                            type="time"
                            className="form-control form-control-sm"
                            value={row.end_time}
                            disabled={gridLocked}
                            onChange={(e) => {
                              const next = [...examSlots];
                              next[idx] = { ...row, end_time: e.target.value };
                              setExamSlots(next);
                            }}
                          />
                        </td>
                        <td>
                          <select
                            className="form-select form-select-sm"
                            value={row.school_class_id}
                            disabled={gridLocked}
                            onChange={(e) => {
                              const next = [...examSlots];
                              const cls = classes.find((c) => String(c.id) === e.target.value);
                              next[idx] = {
                                ...row,
                                school_class_id: e.target.value,
                                room: row.room || cls?.room || '',
                              };
                              setExamSlots(next);
                            }}
                          >
                            <option value="">— class —</option>
                            {classes.map((c) => (
                              <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <select
                            className="form-select form-select-sm"
                            value={row.subject_id}
                            disabled={gridLocked}
                            onChange={(e) => {
                              const next = [...examSlots];
                              next[idx] = { ...row, subject_id: e.target.value };
                              setExamSlots(next);
                            }}
                          >
                            <option value="">— subject —</option>
                            {subjects.map((s) => (
                              <option key={s.id} value={s.id}>{s.name}</option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <TeacherPenPicker
                            teacherId={row.teacher_id}
                            teacherName={row.teacher_name}
                            teachers={teachers}
                            disabled={gridLocked}
                            onChange={(tid, tname) => {
                              const next = [...examSlots];
                              next[idx] = { ...row, teacher_id: tid || '', teacher_name: tname || '' };
                              setExamSlots(next);
                            }}
                          />
                        </td>
                        <td>
                          <input
                            className="form-control form-control-sm"
                            value={row.room}
                            disabled={gridLocked}
                            placeholder="Room"
                            onChange={(e) => {
                              const next = [...examSlots];
                              next[idx] = { ...row, room: e.target.value };
                              setExamSlots(next);
                            }}
                          />
                        </td>
                        <td>
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-danger"
                            disabled={gridLocked || examSlots.length <= 1}
                            onClick={() => setExamSlots(examSlots.filter((_, i) => i !== idx))}
                          >
                            <FiTrash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                    {!examSlots.length && (
                      <tr>
                        <td colSpan={8} className="text-center text-muted small py-4">
                          No sittings yet — add a row or create a new exam draft.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <p className="small text-muted mt-3 mb-0">
                Invigilators are free-picked (not forced from teaching assignments).
                Clashes against <strong>published</strong> lesson and exam schedules are blocked on save.
                Printed PDFs include a QR encoding schedule name, status, creator, dates and classes.
              </p>
            </>
          )}
        </>
      )}
    </div>
  );

  if (!canEdit && !isSchoolAdmin) {
    // Teachers / read-only: library of published only + preview/print
    return (
      <div>
        <div className="mb-3">
          <Link to="/school-admin/academics" className="small text-decoration-none text-muted">
            <FiArrowLeft className="me-1" /> Academics
          </Link>
        </div>
        <PageHeader
          title="Timetables"
          subtitle="Published schedules available for preview and download"
        />
        {modeSwitcher}
        {canUseTeacherView && (
          <div className="apex-card p-3 mb-4">
            <div className="d-flex flex-wrap justify-content-between align-items-center gap-2">
              {teacherViewToggle}
              <span className="small text-muted">
                Applies to preview and print. <strong>Show mine</strong> highlights your periods;
                {' '}<strong>Mine only</strong> blanks everyone else.
              </span>
            </div>
          </div>
        )}
        {librarySection}
        {previewModal}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/academics" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Academics
        </Link>
      </div>

      <PageHeader
        title="Timetables"
        subtitle={mode === 'exam'
          ? 'Examination sittings — date, time, free invigilator pick, published constraints'
          : 'Lesson schedules — drafts, publish lifecycle, class grids and branded printouts'}
      />

      {modeSwitcher}

      {(mode === 'lesson' ? isError : examCtxError) && (
        <div className="alert alert-danger">Unable to load wizard context.</div>
      )}

      {librarySection}
      {previewModal}

      {mode === 'exam' ? examBuilder : (
      <div className="apex-card p-3 p-md-4 mb-4">
        <button
          type="button"
          className="btn btn-link text-decoration-none p-0 d-flex align-items-center gap-2 w-100 text-start"
          onClick={() => setBuilderOpen((v) => !v)}
        >
          {builderOpen ? <FiChevronUp /> : <FiChevronDown />}
          <span className="fw-bold text-body">Lesson timetable builder</span>
          <span className="text-muted small fw-normal">
            Periods → class grid → save draft → publish
          </span>
        </button>

        {builderOpen && (
          <>
            <hr className="my-3" />
            {scheduleMeta ? (
              <div className={`alert py-2 small ${published ? 'alert-success' : 'alert-secondary'}`}>
                Working on: <strong>{scheduleMeta.name || 'Timetable'}</strong>
                {' · '}
                <span className="text-capitalize">{scheduleMeta.status || 'draft'}</span>
                {published ? ' — published (school admin may still edit).' : ' — draft (appears in library above).'}
                {gridLocked && ' Editing locked for non-admins.'}
              </div>
            ) : (
              <div className="alert alert-info py-2 small">
                No draft selected. Click <strong>New draft timetable</strong> above, or <strong>Edit</strong> an existing card.
              </div>
            )}
            <Stepper step={step} />
            {isLoading ? (
              <div className="text-center py-5 text-muted">Loading…</div>
            ) : (
              <>
            {step === 0 && (
              <div>
                <h5 className="fw-bold mb-2">Bell schedule (periods)</h5>
                <p className="text-muted small mb-3">
                  Name breaks (Lunch, Tea…). Times apply Mon–Sun. Only rule: no overlapping times.
                </p>
                <div className="table-responsive">
                  <table className="table table-sm align-middle">
                    <thead>
                      <tr className="small text-muted">
                        <th style={{ width: 40 }}>#</th>
                        <th>Name / break label</th>
                        <th style={{ width: 120 }}>From</th>
                        <th style={{ width: 120 }}>To</th>
                        <th style={{ width: 100 }}>Is break?</th>
                        <th style={{ width: 50 }} />
                      </tr>
                    </thead>
                    <tbody>
                      {periodRows.map((row, idx) => (
                        <tr key={row.id || `new-${idx}`} className={row.is_break ? 'table-light' : ''}>
                          <td className="text-muted small">{idx + 1}</td>
                          <td>
                            <input
                              className="form-control form-control-sm"
                              value={row.name}
                              placeholder={row.is_break ? 'e.g. Lunch, Tea break' : 'e.g. Period 1'}
                              onChange={(e) => {
                                const next = [...periodRows];
                                next[idx] = { ...row, name: e.target.value };
                                setPeriodRows(next);
                              }}
                            />
                          </td>
                          <td>
                            <input
                              type="time"
                              className="form-control form-control-sm"
                              value={row.start_time}
                              onChange={(e) => {
                                const next = [...periodRows];
                                next[idx] = { ...row, start_time: e.target.value };
                                setPeriodRows(next);
                              }}
                            />
                          </td>
                          <td>
                            <input
                              type="time"
                              className="form-control form-control-sm"
                              value={row.end_time}
                              onChange={(e) => {
                                const next = [...periodRows];
                                next[idx] = { ...row, end_time: e.target.value };
                                setPeriodRows(next);
                              }}
                            />
                          </td>
                          <td>
                            <div className="form-check form-switch">
                              <input
                                className="form-check-input"
                                type="checkbox"
                                checked={!!row.is_break}
                                onChange={(e) => {
                                  const next = [...periodRows];
                                  const checked = e.target.checked;
                                  const name = checked && (!row.name || /^period\s*\d*$/i.test(row.name.trim()))
                                    ? 'Lunch'
                                    : row.name;
                                  next[idx] = { ...row, is_break: checked, name };
                                  setPeriodRows(next);
                                }}
                              />
                            </div>
                          </td>
                          <td>
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-danger"
                              onClick={() => setPeriodRows(periodRows.filter((_, i) => i !== idx))}
                              disabled={periodRows.length <= 1}
                            >
                              <FiTrash2 size={14} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="d-flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => {
                      const last = periodRows[periodRows.length - 1];
                      if (last?.end_time) {
                        const [h, m] = normalizeTime(last.end_time).split(':').map(Number);
                        const startTotal = h * 60 + m;
                        const fmt = (mins) => `${String(Math.floor(mins / 60) % 24).padStart(2, '0')}:${String(mins % 60).padStart(2, '0')}`;
                        setPeriodRows([...periodRows, {
                          id: null,
                          name: `Period ${periodRows.length + 1}`,
                          start_time: fmt(startTotal),
                          end_time: fmt(startTotal + 40),
                          sort_order: periodRows.length + 1,
                          is_break: false,
                        }]);
                      } else {
                        setPeriodRows([...periodRows, {
                          id: null, name: `Period ${periodRows.length + 1}`,
                          start_time: '08:00', end_time: '08:40', sort_order: periodRows.length + 1, is_break: false,
                        }]);
                      }
                    }}
                  >
                    <FiPlus className="me-1" /> Add period
                  </button>
                  <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={savePeriods}>
                    <FiSave className="me-1" /> {busy ? 'Saving…' : 'Save periods & continue'}
                  </button>
                </div>
              </div>
            )}

            {step === 1 && (
              <div>
                <h5 className="fw-bold mb-3">Choose class</h5>
                <p className="text-muted small">
                  Leave stream empty to build the <strong>whole class</strong> — each period is split by stream (East, West…).
                  Or pick one stream for a single-stream grid.
                </p>
                <div className="row g-3">
                  <div className="col-md-6">
                    <label className="form-label small">Class *</label>
                    <SearchableSelect
                      options={classOptions}
                      value={schoolClass}
                      onChange={(v) => { setSchoolClass(v); setStream(''); }}
                      placeholder="Search class…"
                    />
                  </div>
                  {streamOptions.length > 0 && (
                    <div className="col-md-6">
                      <label className="form-label small">Stream (optional)</label>
                      <SearchableSelect
                        options={streamOptions}
                        value={stream}
                        onChange={setStream}
                        placeholder="Whole class (all streams)"
                        allowClear
                      />
                      <div className="form-text">
                        Empty = multi-stream grid for the whole class.
                      </div>
                    </div>
                  )}
                  <div className="col-12">
                    <label className="form-label small">Days</label>
                    <div className="d-flex flex-wrap gap-2">
                      {DAY_OPTIONS.map((d) => (
                        <button
                          key={d.value}
                          type="button"
                          className={`btn btn-sm ${workingDays.includes(d.value) ? 'btn-primary' : 'btn-outline-secondary'}`}
                          onClick={() => setWorkingDays((prev) => (
                            prev.includes(d.value)
                              ? prev.filter((x) => x !== d.value)
                              : [...prev, d.value].sort()
                          ))}
                        >
                          {d.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {step === 2 && (
              <div>
                <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                  <div>
                    <h5 className="fw-bold mb-0">
                      {classes.find((c) => c.id === schoolClass)?.name || 'Class'}
                      {multiStream ? ' — all streams' : stream ? ` — stream` : ''}
                    </h5>
                    <div className="small text-muted">
                      {multiStream
                        ? 'Each time slot is split by stream (column after Time).'
                        : 'Assign subjects; teacher auto-fills — use the pen to change teacher.'}
                    </div>
                  </div>
                  <div className="d-flex gap-2">
                    <button type="button" className="btn btn-outline-secondary btn-sm" disabled={busy} onClick={loadGrid}>
                      Reload
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      disabled={busy || gridLocked}
                      onClick={() => saveGrid(false)}
                    >
                      <FiSave className="me-1" /> {busy ? 'Saving…' : 'Save draft'}
                    </button>
                  </div>
                </div>

                {gridLocked && (
                  <div className="alert alert-warning small">
                    Published timetable — only school admin can edit. Ask admin to unpublish first.
                  </div>
                )}

                {conflicts.length > 0 && (
                  <div className="alert alert-warning small">
                    <FiAlertTriangle className="me-1" />
                    <strong>{conflicts.length} clash(es)</strong>
                    <ul className="mb-0 mt-1">
                      {conflicts.slice(0, 6).map((c, i) => <li key={i}>{c.message}</li>)}
                    </ul>
                  </div>
                )}

                {!schoolClass ? (
                  <ModuleEmptyState title="Select a class" message="Go back and choose a class." />
                ) : (
                  <div className="table-responsive border rounded">
                    <table className="table table-bordered table-sm mb-0" style={{ minWidth: multiStream ? 900 : 720 }}>
                      <thead className="table-light">
                        <tr>
                          <th style={{ minWidth: 88 }} className="small">Time</th>
                          {multiStream && <th style={{ minWidth: 72 }} className="small">Stream</th>}
                          {daysSorted.map((d) => (
                            <th key={d} className="text-center small">
                              {DAY_OPTIONS.find((x) => x.value === d)?.label || d}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {gridRows.map(({ period, stream: st, streamIndex, streamCount, isBreakRow }) => {
                          const sid = st?.id ? String(st.id) : '';
                          const showTime = streamIndex === 0;
                          return (
                            <tr
                              key={`${period.id}-${sid || 'break'}-${streamIndex}`}
                              className={period.is_break || isBreakRow ? 'table-secondary' : ''}
                            >
                              {showTime ? (
                                <td
                                  className="small align-middle"
                                  rowSpan={streamCount}
                                  style={{ verticalAlign: 'middle' }}
                                >
                                  <div className="fw-semibold text-nowrap">
                                    {normalizeTime(period.start_time)}–{normalizeTime(period.end_time)}
                                  </div>
                                </td>
                              ) : null}
                              {multiStream && (
                                <td className="small fw-medium align-middle bg-light">
                                  {isBreakRow ? '' : (st?.name || '—')}
                                </td>
                              )}
                              {daysSorted.map((day) => {
                                if (period.is_break || isBreakRow) {
                                  return (
                                    <td key={day} className="text-center small text-muted align-middle fw-medium">
                                      {period.name || 'Break'}
                                    </td>
                                  );
                                }
                                const cell = findCell(cellsMap, day, period.id, sid) || {
                                  day_of_week: day,
                                  period_id: period.id,
                                  stream_id: sid || null,
                                  is_break: false,
                                };
                                return (
                                  <td key={day} className="p-1 align-top" style={{ minWidth: 128 }}>
                                    <select
                                      className="form-select form-select-sm mb-1"
                                      value={cell.subject_id || ''}
                                      disabled={gridLocked}
                                      onChange={(e) => onSubjectChange(day, period.id, sid, e.target.value || null)}
                                    >
                                      <option value="">— free —</option>
                                      {subjectOptions.map((s) => (
                                        <option key={s.value} value={s.value}>{s.label}</option>
                                      ))}
                                    </select>
                                    {cell.subject_id && (
                                      <TeacherPenPicker
                                        teacherId={cell.teacher_id}
                                        teacherName={cell.teacher_name}
                                        teachers={teachers}
                                        disabled={gridLocked}
                                        onChange={(tid, tname) => updateCell(day, period.id, sid, {
                                          teacher_id: tid,
                                          teacher_name: tname,
                                        })}
                                      />
                                    )}
                                  </td>
                                );
                              })}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {step === 3 && (
              <div>
                <h5 className="fw-bold mb-3">Save, publish & print</h5>
                <div className="row g-3 mb-4">
                  <div className="col-md-6">
                    <div className="border rounded p-3 h-100">
                      <h6 className="fw-semibold">Lifecycle</h6>
                      <ol className="small text-muted mb-3">
                        <li>Fill the class grid and <strong>Save draft</strong></li>
                        <li><strong>Publish</strong> when ready — teachers get read + download access</li>
                        <li>Only school admin can edit or unpublish after publish</li>
                      </ol>
                      <div className="d-flex flex-wrap gap-2">
                        <button type="button" className="btn btn-outline-primary btn-sm" disabled={busy || gridLocked} onClick={() => saveGrid(false)}>
                          <FiSave className="me-1" /> Save draft
                        </button>
                        <button type="button" className="btn btn-success btn-sm" disabled={busy} onClick={publish}>
                          <FiSend className="me-1" /> Publish
                        </button>
                        {published && isSchoolAdmin && (
                          <button type="button" className="btn btn-outline-secondary btn-sm" disabled={busy} onClick={unpublish}>
                            <FiUnlock className="me-1" /> Unpublish
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="col-md-6">
                    <div className="border rounded p-3 h-100">
                      <h6 className="fw-semibold"><FiPrinter className="me-1" />Print PDF</h6>
                      <div className="mb-2">
                        <label className="form-label small">Scope</label>
                        <select className="form-select form-select-sm" value={printScope} onChange={(e) => setPrintScope(e.target.value)}>
                          <option value="class">Current class</option>
                          <option value="selected">Selected classes</option>
                          <option value="school">Whole school</option>
                        </select>
                      </div>
                      <div className="mb-2">
                        <label className="form-label small">Orientation</label>
                        <select className="form-select form-select-sm" value={printOrientation} onChange={(e) => setPrintOrientation(e.target.value)}>
                          <option value="landscape">Landscape</option>
                          <option value="portrait">Portrait</option>
                        </select>
                      </div>
                      {printScope === 'selected' && (
                        <div className="d-flex flex-wrap gap-1 mb-2">
                          {classes.map((c) => (
                            <button
                              key={c.id}
                              type="button"
                              className={`btn btn-sm ${printClassIds.includes(c.id) ? 'btn-primary' : 'btn-outline-secondary'}`}
                              onClick={() => setPrintClassIds((prev) => (
                                prev.includes(c.id) ? prev.filter((x) => x !== c.id) : [...prev, c.id]
                              ))}
                            >
                              {c.name}
                            </button>
                          ))}
                        </div>
                      )}
                      <button type="button" className="btn btn-primary btn-sm" disabled={busy} onClick={downloadPdf}>
                        <FiDownload className="me-1" /> Download PDF
                      </button>
                    </div>
                  </div>
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
              {step < 3 && step !== 0 && (
                <button
                  type="button"
                  className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
                  onClick={() => setStep((s) => s + 1)}
                  disabled={step === 1 && !schoolClass}
                >
                  Continue <FiArrowRight size={14} />
                </button>
              )}
              {step === 2 && (
                <button type="button" className="btn btn-outline-primary btn-sm" onClick={() => setStep(3)}>
                  Save & publish <FiArrowRight size={14} />
                </button>
              )}
            </div>
              </>
            )}
          </>
        )}
      </div>
      )}
    </div>
  );
}

export default TimetableWizard;
