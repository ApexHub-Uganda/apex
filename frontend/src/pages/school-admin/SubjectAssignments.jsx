import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  FiArrowLeft,
  FiEdit2,
  FiFilter,
  FiPlus,
  FiTrash2,
  FiUserCheck,
  FiUsers,
  FiX,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { Modal } from '../../components/Modal';
import {
  classTeacherAssignmentsService,
  teachingAssignmentsService,
} from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { alert, extractApiError, notify } from '../../utils/notify';

const EMPTY_LINE = { school_class: '', subject: '' };
const EMPTY_FORM = {
  teacher: '',
  lines: [{ ...EMPTY_LINE }],
  notes: '',
};

const EMPTY_CT_FORM = {
  teacher: '',
  school_class: '',
  stream: '',
  notes: '',
};

function groupByTeacher(rows) {
  const map = new Map();
  for (const row of rows) {
    if (!map.has(row.teacher)) {
      map.set(row.teacher, {
        key: row.teacher,
        teacher: row.teacher,
        teacher_name: row.teacher_name,
        placements: [],
        assignment_ids: [],
        notes: '',
      });
    }
    const group = map.get(row.teacher);
    group.placements.push({
      assignment_id: row.id,
      school_class: row.school_class,
      school_class_name: row.school_class_name,
      school_class_code: row.school_class_code,
      subject: row.subject,
      subject_code: row.subject_code,
      subject_name: row.subject_name,
      academic_year_name: row.academic_year_name,
      line_key: `${row.school_class}:${row.subject}`,
    });
    group.assignment_ids.push(row.id);
    if (!group.notes && row.notes) group.notes = row.notes;
  }

  return [...map.values()]
    .map((group) => ({
      ...group,
      placements: [...group.placements].sort((a, b) => (
        a.school_class_name.localeCompare(b.school_class_name)
        || a.subject_code.localeCompare(b.subject_code)
      )),
    }))
    .sort((a, b) => a.teacher_name.localeCompare(b.teacher_name));
}

function hasDuplicateLines(lines) {
  const seen = new Set();
  for (const line of lines) {
    if (!line.school_class || !line.subject) continue;
    const key = `${line.school_class}:${line.subject}`;
    if (seen.has(key)) return true;
    seen.add(key);
  }
  return false;
}

export function SubjectAssignments() {
  const queryClient = useQueryClient();
  const { canWriteFeature, isSchoolAdmin } = usePermissions();
  const canManage = isSchoolAdmin
    || canWriteFeature('subject_assignment')
    || canWriteFeature('teacher_assignments')
    || canWriteFeature('classes')
    || canWriteFeature('dos_workspace');

  const [tab, setTab] = useState('subject'); // subject | class_teacher

  // ── Subject teacher state ──────────────────────────────────────────────
  const [filters, setFilters] = useState({ teacher: '', school_class: '', subject: '' });
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [deletingKey, setDeletingKey] = useState(null);

  // ── Class teacher state ────────────────────────────────────────────────
  const [ctFilters, setCtFilters] = useState({ teacher: '', school_class: '', assigned: '' });
  const [showCtModal, setShowCtModal] = useState(false);
  const [ctForm, setCtForm] = useState(EMPTY_CT_FORM);
  const [ctSaving, setCtSaving] = useState(false);
  const [ctBusyKey, setCtBusyKey] = useState(null);

  const listParams = useMemo(() => {
    const params = { page_size: 300, is_active: true };
    if (filters.teacher) params.teacher = filters.teacher;
    if (filters.school_class) params.school_class = filters.school_class;
    if (filters.subject) params.subject = filters.subject;
    return params;
  }, [filters]);

  const { data: rows = [], isLoading, isError } = useQuery({
    queryKey: ['teaching-assignments', listParams],
    queryFn: () => teachingAssignmentsService.list(listParams),
    enabled: tab === 'subject',
  });

  const { data: options } = useQuery({
    queryKey: ['teaching-assignments', 'form-options'],
    queryFn: () => teachingAssignmentsService.formOptions(),
    staleTime: 60_000,
  });

  const ctListParams = useMemo(() => {
    const params = {};
    if (ctFilters.teacher) params.teacher = ctFilters.teacher;
    if (ctFilters.school_class) params.school_class = ctFilters.school_class;
    if (ctFilters.assigned) params.assigned = ctFilters.assigned;
    return params;
  }, [ctFilters]);

  const {
    data: ctPayload,
    isLoading: ctLoading,
    isError: ctError,
  } = useQuery({
    queryKey: ['class-teacher-assignments', ctListParams],
    queryFn: () => classTeacherAssignmentsService.list(ctListParams),
    enabled: tab === 'class_teacher',
  });

  const { data: ctOptions } = useQuery({
    queryKey: ['class-teacher-assignments', 'form-options'],
    queryFn: () => classTeacherAssignmentsService.formOptions(),
    staleTime: 60_000,
    enabled: tab === 'class_teacher' || showCtModal,
  });

  const teachers = options?.teachers ?? ctOptions?.teachers ?? [];
  const classes = options?.classes ?? [];
  const subjects = options?.subjects ?? [];
  const teacherRows = useMemo(() => groupByTeacher(rows), [rows]);

  const ctRows = ctPayload?.results || [];
  const ctTeachers = ctOptions?.teachers || teachers;
  const ctClasses = ctOptions?.classes || [];
  const canManageCt = Boolean(ctPayload?.can_manage ?? ctOptions?.can_manage ?? canManage);

  const ctStreamOptions = useMemo(() => {
    const c = ctClasses.find((x) => String(x.value) === String(ctForm.school_class));
    return c?.streams || [];
  }, [ctClasses, ctForm.school_class]);

  // ── Subject teacher handlers ───────────────────────────────────────────
  const openCreate = () => {
    setEditing(null);
    setForm({ ...EMPTY_FORM, lines: [{ ...EMPTY_LINE }] });
    setShowModal(true);
  };

  const openEdit = (group) => {
    setEditing(group);
    setForm({
      teacher: group.teacher,
      lines: group.placements.map((placement) => ({
        school_class: placement.school_class,
        subject: placement.subject,
      })),
      notes: group.notes || '',
    });
    setShowModal(true);
  };

  const addLine = () => {
    setForm((prev) => ({ ...prev, lines: [...prev.lines, { ...EMPTY_LINE }] }));
  };

  const removeLine = (index) => {
    setForm((prev) => {
      if (prev.lines.length === 1) {
        return { ...prev, lines: [{ ...EMPTY_LINE }] };
      }
      return { ...prev, lines: prev.lines.filter((_, i) => i !== index) };
    });
  };

  const updateLine = (index, field, value) => {
    setForm((prev) => ({
      ...prev,
      lines: prev.lines.map((line, i) => (i === index ? { ...line, [field]: value } : line)),
    }));
  };

  const handleSave = async () => {
    const completeLines = form.lines.filter((line) => line.school_class && line.subject);
    if (!form.teacher) {
      notify.error('Select a teacher.');
      return;
    }
    if (!completeLines.length) {
      notify.error('Add at least one class and subject pairing.');
      return;
    }
    if (hasDuplicateLines(completeLines)) {
      notify.error('Each class and subject combination can only appear once.');
      return;
    }
    if (form.lines.some((line) => (line.school_class && !line.subject) || (!line.school_class && line.subject))) {
      notify.error('Complete every class and subject row, or remove empty rows.');
      return;
    }

    setSaving(true);
    try {
      const result = await teachingAssignmentsService.syncTeacher({
        teacher: form.teacher,
        assignments: completeLines.map((line) => ({
          school_class: line.school_class,
          subject: line.subject,
        })),
        notes: form.notes,
      });
      notify.success(result?.message || (editing ? 'Subject teacher assignments updated.' : 'Subject teacher assignments saved.'));
      await queryClient.invalidateQueries({ queryKey: ['teaching-assignments'] });
      setShowModal(false);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to save subject teacher assignments.'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (group) => {
    const placementLabel = group.placements
      .map((p) => `${p.school_class_name} · ${p.subject_code}`)
      .join(', ');
    const label = `${group.teacher_name} (${placementLabel})`;
    const result = await alert.delete(label);
    if (!result.isConfirmed) return;
    setDeletingKey(group.key);
    try {
      await Promise.all(
        group.assignment_ids.map((id) => teachingAssignmentsService.delete(id)),
      );
      notify.success('Subject teacher assignments removed.');
      await queryClient.invalidateQueries({ queryKey: ['teaching-assignments'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to remove assignments.'));
    } finally {
      setDeletingKey(null);
    }
  };

  // ── Class teacher handlers ─────────────────────────────────────────────
  const openCtAssign = (row = null) => {
    if (row) {
      setCtForm({
        teacher: row.teacher_id || '',
        school_class: row.school_class_id || '',
        stream: row.stream_id || '',
        notes: '',
      });
    } else {
      setCtForm({ ...EMPTY_CT_FORM });
    }
    setShowCtModal(true);
  };

  const handleCtSave = async () => {
    if (!ctForm.teacher) {
      notify.error('Select a teacher.');
      return;
    }
    if (!ctForm.school_class) {
      notify.error('Select a class.');
      return;
    }
    setCtSaving(true);
    try {
      const result = await classTeacherAssignmentsService.assign({
        teacher: ctForm.teacher,
        school_class: ctForm.school_class,
        stream: ctForm.stream || undefined,
        notes: ctForm.notes || '',
      });
      notify.success(
        result?.message
          || 'Class teacher assigned. Dual-role class teacher access is enabled on their portal account.',
      );
      await queryClient.invalidateQueries({ queryKey: ['class-teacher-assignments'] });
      setShowCtModal(false);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to assign class teacher.'));
    } finally {
      setCtSaving(false);
    }
  };

  const handleCtUnassign = async (row) => {
    if (!row?.is_assigned) return;
    const label = row.teacher_name
      ? `${row.teacher_name} from ${row.label}`
      : row.label;
    const confirmed = await alert.confirm({
      title: 'Remove class teacher?',
      text: `Unassign ${label}? Auto-granted dual-role access is removed when they no longer head any class or stream.`,
      confirmText: 'Unassign',
      cancelText: 'Cancel',
      icon: 'warning',
    });
    if (!confirmed.isConfirmed) return;
    setCtBusyKey(row.key);
    try {
      const result = await classTeacherAssignmentsService.unassign({
        school_class: row.school_class_id,
        stream: row.stream_id || undefined,
      });
      notify.success(result?.message || 'Class teacher unassigned.');
      await queryClient.invalidateQueries({ queryKey: ['class-teacher-assignments'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to unassign class teacher.'));
    } finally {
      setCtBusyKey(null);
    }
  };

  const subjectColumns = [
    {
      key: 'teacher_name',
      label: 'Subject teacher',
      accessor: 'teacher_name',
      sortable: true,
    },
    {
      key: 'placements',
      label: 'Class & subject pairings',
      truncate: false,
      render: (row) => (
        <div className="subject-assignment-table-chips">
          {row.placements.map((placement) => (
            <span
              key={placement.line_key}
              className="subject-assignment-placement-chip"
              title={`${placement.subject_name} in ${placement.school_class_name}`}
            >
              <span className="subject-assignment-placement-class">
                {placement.school_class_name}
              </span>
              <span className="subject-assignment-placement-sep">·</span>
              <span className="subject-assignment-placement-subject">
                {placement.subject_code}
              </span>
            </span>
          ))}
        </div>
      ),
    },
    {
      key: 'placement_count',
      label: 'Pairings',
      render: (row) => (
        <span className="text-muted small">{row.placements.length}</span>
      ),
    },
    ...(canManage ? [{
      key: 'actions',
      label: '',
      truncate: false,
      render: (row) => (
        <div className="apex-table-row-actions">
          <button
            type="button"
            className="btn btn-sm btn-outline-primary"
            onClick={(e) => { e.stopPropagation(); openEdit(row); }}
            title="Edit subject teacher assignments"
          >
            <FiEdit2 size={14} />
          </button>
          <button
            type="button"
            className="btn btn-sm btn-outline-danger"
            disabled={deletingKey === row.key}
            onClick={(e) => { e.stopPropagation(); handleDelete(row); }}
            title="Remove all subject assignments"
          >
            {deletingKey === row.key ? '…' : <FiTrash2 size={14} />}
          </button>
        </div>
      ),
    }] : []),
  ];

  const ctColumns = [
    {
      key: 'label',
      label: 'Class / stream',
      accessor: 'label',
      sortable: true,
      render: (row) => (
        <div>
          <div className="fw-medium">{row.label}</div>
          <div className="small text-muted">
            {row.scope === 'stream' ? 'Stream head' : 'Whole class'}
            {row.academic_year_name ? ` · ${row.academic_year_name}` : ''}
          </div>
        </div>
      ),
    },
    {
      key: 'teacher_name',
      label: 'Class teacher',
      render: (row) => (
        row.is_assigned ? (
          <span className="fw-medium">{row.teacher_name}</span>
        ) : (
          <span className="badge text-bg-warning-subtle border text-warning">Vacant</span>
        )
      ),
    },
    {
      key: 'scope',
      label: 'Scope',
      render: (row) => (
        <span className="badge text-bg-secondary-subtle border text-secondary text-capitalize">
          {row.scope === 'stream' ? 'Stream' : 'Class'}
        </span>
      ),
    },
    ...(canManageCt ? [{
      key: 'actions',
      label: '',
      truncate: false,
      render: (row) => (
        <div className="apex-table-row-actions">
          <button
            type="button"
            className="btn btn-sm btn-outline-primary"
            onClick={(e) => { e.stopPropagation(); openCtAssign(row); }}
            title={row.is_assigned ? 'Change class teacher' : 'Assign class teacher'}
          >
            <FiUserCheck size={14} />
          </button>
          {row.is_assigned && (
            <button
              type="button"
              className="btn btn-sm btn-outline-danger"
              disabled={ctBusyKey === row.key}
              onClick={(e) => { e.stopPropagation(); handleCtUnassign(row); }}
              title="Unassign class teacher"
            >
              {ctBusyKey === row.key ? '…' : <FiTrash2 size={14} />}
            </button>
          )}
        </div>
      ),
    }] : []),
  ];

  const hasFilters = Boolean(filters.teacher || filters.school_class || filters.subject);
  const hasCtFilters = Boolean(ctFilters.teacher || ctFilters.school_class || ctFilters.assigned);
  const completeLineCount = form.lines.filter((line) => line.school_class && line.subject).length;

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/academics" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Academics
        </Link>
      </div>

      <PageHeader
        title="Teacher assignments"
        subtitle="Assign subject teachers (class–subject pairings) and class teachers (whole class or stream). Class teachers receive dual-role access automatically."
        actions={(
          <div className="d-flex flex-wrap gap-2">
            {tab === 'subject' && canManage && (
              <button
                type="button"
                className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
                onClick={openCreate}
              >
                <FiPlus size={16} /> Assign subject teacher
              </button>
            )}
            {tab === 'class_teacher' && canManageCt && (
              <button
                type="button"
                className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
                onClick={() => openCtAssign(null)}
              >
                <FiPlus size={16} /> Assign class teacher
              </button>
            )}
          </div>
        )}
      />

      <ul className="nav nav-tabs mb-3">
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${tab === 'subject' ? ' active' : ''}`}
            onClick={() => setTab('subject')}
          >
            <FiUserCheck className="me-1" size={14} />
            Subject teachers
          </button>
        </li>
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${tab === 'class_teacher' ? ' active' : ''}`}
            onClick={() => setTab('class_teacher')}
          >
            <FiUsers className="me-1" size={14} />
            Class teachers
          </button>
        </li>
      </ul>

      {tab === 'subject' && (
        <>
          <div className="apex-card p-3 p-md-4 mb-4">
            <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
              <FiFilter size={14} className="text-muted" />
              <span className="small fw-semibold text-muted">Filter subject teachers</span>
            </div>
            <div className="row g-2">
              <div className="col-sm-4">
                <select
                  className="form-select form-select-sm"
                  value={filters.teacher}
                  onChange={(e) => setFilters((f) => ({ ...f, teacher: e.target.value }))}
                >
                  <option value="">All teachers</option>
                  {teachers.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
              <div className="col-sm-4">
                <select
                  className="form-select form-select-sm"
                  value={filters.school_class}
                  onChange={(e) => setFilters((f) => ({ ...f, school_class: e.target.value }))}
                >
                  <option value="">All classes</option>
                  {classes.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>
              <div className="col-sm-4">
                <select
                  className="form-select form-select-sm"
                  value={filters.subject}
                  onChange={(e) => setFilters((f) => ({ ...f, subject: e.target.value }))}
                >
                  <option value="">All subjects</option>
                  {subjects.map((s) => (
                    <option key={s.value} value={s.value}>{s.code}</option>
                  ))}
                </select>
              </div>
            </div>
            {hasFilters && (
              <button
                type="button"
                className="btn btn-link btn-sm px-0 mt-2"
                onClick={() => setFilters({ teacher: '', school_class: '', subject: '' })}
              >
                Clear filters
              </button>
            )}
          </div>

          {isError ? (
            <div className="alert alert-danger">Unable to load subject teacher assignments.</div>
          ) : (
            <div className="apex-card p-3 p-md-4">
              <DataTable
                columns={subjectColumns}
                data={teacherRows}
                loading={isLoading}
                onRowClick={canManage ? openEdit : undefined}
                emptyState={(
                  <ModuleEmptyState
                    icon={FiUserCheck}
                    title={canManage ? 'No subject teacher assignments yet' : 'No assignments linked to you'}
                    message={
                      canManage
                        ? 'Assign a subject teacher to one or more class–subject pairings. The same teacher can teach different subjects in different classes.'
                        : 'Your class and subject pairings appear here once leadership assigns you.'
                    }
                    actionLabel={canManage ? 'Assign subject teacher' : undefined}
                    onAction={canManage ? openCreate : undefined}
                  />
                )}
              />
            </div>
          )}
        </>
      )}

      {tab === 'class_teacher' && (
        <>
          <div className="alert alert-light border small mb-3">
            <strong>How class teachers work.</strong>{' '}
            Assign a teacher to a whole class, or to a stream when the class is divided.
            Their portal account keeps subject-teacher access and automatically receives
            <strong> class teacher</strong> dual-role tools (notices, report cards, class roster)
            for headed classes — no separate login.
          </div>

          <div className="apex-card p-3 p-md-4 mb-4">
            <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
              <FiFilter size={14} className="text-muted" />
              <span className="small fw-semibold text-muted">Filter class teachers</span>
            </div>
            <div className="row g-2">
              <div className="col-sm-4">
                <select
                  className="form-select form-select-sm"
                  value={ctFilters.teacher}
                  onChange={(e) => setCtFilters((f) => ({ ...f, teacher: e.target.value }))}
                >
                  <option value="">All teachers</option>
                  {ctTeachers.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
              <div className="col-sm-4">
                <select
                  className="form-select form-select-sm"
                  value={ctFilters.school_class}
                  onChange={(e) => setCtFilters((f) => ({ ...f, school_class: e.target.value }))}
                >
                  <option value="">All classes</option>
                  {ctClasses.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>
              <div className="col-sm-4">
                <select
                  className="form-select form-select-sm"
                  value={ctFilters.assigned}
                  onChange={(e) => setCtFilters((f) => ({ ...f, assigned: e.target.value }))}
                >
                  <option value="">Assigned & vacant</option>
                  <option value="1">Assigned only</option>
                  <option value="0">Vacant only</option>
                </select>
              </div>
            </div>
            {hasCtFilters && (
              <button
                type="button"
                className="btn btn-link btn-sm px-0 mt-2"
                onClick={() => setCtFilters({ teacher: '', school_class: '', assigned: '' })}
              >
                Clear filters
              </button>
            )}
          </div>

          {ctError ? (
            <div className="alert alert-danger">Unable to load class teacher assignments.</div>
          ) : (
            <div className="apex-card p-3 p-md-4">
              <DataTable
                columns={ctColumns}
                data={ctRows}
                loading={ctLoading}
                onRowClick={canManageCt ? openCtAssign : undefined}
                emptyState={(
                  <ModuleEmptyState
                    icon={FiUsers}
                    title="No classes found"
                    message="Create classes (and streams if needed) under Academics → Classes, then assign class teachers here."
                    actionLabel={canManageCt ? 'Assign class teacher' : undefined}
                    onAction={canManageCt ? () => openCtAssign(null) : undefined}
                  />
                )}
              />
            </div>
          )}
        </>
      )}

      {/* Subject teacher modal */}
      <Modal
        show={showModal}
        onHide={() => setShowModal(false)}
        title={editing ? 'Edit subject teacher assignments' : 'Assign subject teacher'}
        size="lg"
        footer={(
          <button
            type="button"
            className="btn btn-primary ms-auto"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving…' : (editing ? 'Save changes' : 'Save assignments')}
          </button>
        )}
      >
        <div className="row g-3">
          <div className="col-12">
            <label className="form-label small fw-medium">Subject teacher *</label>
            <select
              className="form-select"
              value={form.teacher}
              onChange={(e) => setForm({ ...form, teacher: e.target.value })}
              disabled={Boolean(editing)}
            >
              <option value="">Select teacher</option>
              {teachers.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}{t.designation ? ` — ${t.designation}` : ''}
                </option>
              ))}
            </select>
            {editing && (
              <p className="form-text mb-0">Teacher cannot be changed while editing. Remove and re-create to transfer assignments.</p>
            )}
          </div>

          <div className="col-12">
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-2">
              <div>
                <label className="form-label small fw-medium mb-0">Class & subject pairings *</label>
                <p className="form-text mb-0">
                  Add one row per class and subject — e.g. S.1 + Mathematics, S.2 + Physics.
                </p>
              </div>
              {completeLineCount > 0 && (
                <span className="badge text-bg-primary-subtle border text-primary">
                  {completeLineCount} pairing{completeLineCount === 1 ? '' : 's'}
                </span>
              )}
            </div>

            <div className="subject-assignment-lines">
              {form.lines.map((line, index) => (
                <div key={`line-${index}`} className="subject-assignment-line">
                  <div className="subject-assignment-line-fields">
                    <div className="subject-assignment-line-field">
                      <label className="form-label small text-muted mb-1">Class</label>
                      <select
                        className="form-select form-select-sm"
                        value={line.school_class}
                        onChange={(e) => updateLine(index, 'school_class', e.target.value)}
                      >
                        <option value="">Select class</option>
                        {classes.map((c) => (
                          <option key={c.value} value={c.value}>
                            {c.label}{c.academic_year_name ? ` · ${c.academic_year_name}` : ''}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="subject-assignment-line-field">
                      <label className="form-label small text-muted mb-1">Subject</label>
                      <select
                        className="form-select form-select-sm"
                        value={line.subject}
                        onChange={(e) => updateLine(index, 'subject', e.target.value)}
                      >
                        <option value="">Select subject</option>
                        {subjects.map((s) => (
                          <option key={s.value} value={s.value}>
                            {s.code} — {s.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-secondary subject-assignment-line-remove"
                    onClick={() => removeLine(index)}
                    title="Remove pairing"
                    aria-label="Remove pairing"
                  >
                    <FiX size={14} />
                  </button>
                </div>
              ))}
            </div>

            <button
              type="button"
              className="btn btn-sm btn-outline-primary d-inline-flex align-items-center gap-1 mt-2"
              onClick={addLine}
            >
              <FiPlus size={14} /> Add class & subject
            </button>
          </div>

          <div className="col-12">
            <label className="form-label small fw-medium">Notes</label>
            <input
              className="form-control"
              placeholder="Optional e.g. Part-time, shared load"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </div>
        </div>
      </Modal>

      {/* Class teacher modal */}
      <Modal
        show={showCtModal}
        onHide={() => setShowCtModal(false)}
        title="Assign class teacher"
        size="md"
        footer={(
          <button
            type="button"
            className="btn btn-primary ms-auto"
            onClick={handleCtSave}
            disabled={ctSaving}
          >
            {ctSaving ? 'Saving…' : 'Save class teacher'}
          </button>
        )}
      >
        <div className="row g-3">
          <div className="col-12">
            <label className="form-label small fw-medium">Teacher *</label>
            <select
              className="form-select"
              value={ctForm.teacher}
              onChange={(e) => setCtForm({ ...ctForm, teacher: e.target.value })}
            >
              <option value="">Select teacher</option>
              {ctTeachers.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                  {t.designation ? ` — ${t.designation}` : ''}
                  {t.is_class_teacher ? ' · class teacher' : ''}
                </option>
              ))}
            </select>
            <p className="form-text mb-0">
              Portal dual-role <strong>class teacher</strong> access is granted automatically for this assignment.
            </p>
          </div>
          <div className="col-12">
            <label className="form-label small fw-medium">Class *</label>
            <select
              className="form-select"
              value={ctForm.school_class}
              onChange={(e) => setCtForm({ ...ctForm, school_class: e.target.value, stream: '' })}
            >
              <option value="">Select class</option>
              {ctClasses.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                  {c.academic_year_name ? ` · ${c.academic_year_name}` : ''}
                  {c.class_teacher_name ? ` (current: ${c.class_teacher_name})` : ''}
                </option>
              ))}
            </select>
          </div>
          {ctStreamOptions.length > 0 && (
            <div className="col-12">
              <label className="form-label small fw-medium">Stream (optional)</label>
              <select
                className="form-select"
                value={ctForm.stream}
                onChange={(e) => setCtForm({ ...ctForm, stream: e.target.value })}
              >
                <option value="">Whole class (not a single stream)</option>
                {ctStreamOptions.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                    {s.class_teacher_name ? ` (current: ${s.class_teacher_name})` : ''}
                  </option>
                ))}
              </select>
              <p className="form-text mb-0">
                Leave empty to assign the whole class. Choose a stream to head only that stream (e.g. S.1 East).
              </p>
            </div>
          )}
          <div className="col-12">
            <label className="form-label small fw-medium">Notes</label>
            <input
              className="form-control"
              placeholder="Optional"
              value={ctForm.notes}
              onChange={(e) => setCtForm({ ...ctForm, notes: e.target.value })}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default SubjectAssignments;
