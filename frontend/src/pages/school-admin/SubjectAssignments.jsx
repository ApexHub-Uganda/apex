import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiEdit2, FiFilter, FiPlus, FiTrash2, FiUserCheck, FiX } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { Modal } from '../../components/Modal';
import { teachingAssignmentsService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { alert, extractApiError, notify } from '../../utils/notify';

const EMPTY_LINE = { school_class: '', subject: '' };
const EMPTY_FORM = {
  teacher: '',
  lines: [{ ...EMPTY_LINE }],
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
    || canWriteFeature('teacher_assignments');

  const [filters, setFilters] = useState({ teacher: '', school_class: '', subject: '' });
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [deletingKey, setDeletingKey] = useState(null);

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
  });

  const { data: options } = useQuery({
    queryKey: ['teaching-assignments', 'form-options'],
    queryFn: () => teachingAssignmentsService.formOptions(),
    staleTime: 60_000,
  });

  const teachers = options?.teachers ?? [];
  const classes = options?.classes ?? [];
  const subjects = options?.subjects ?? [];
  const teacherRows = useMemo(() => groupByTeacher(rows), [rows]);

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
      notify.success(result?.message || (editing ? 'Assignments updated.' : 'Assignments saved.'));
      await queryClient.invalidateQueries({ queryKey: ['teaching-assignments'] });
      setShowModal(false);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to save assignments.'));
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
      notify.success('Assignments removed.');
      await queryClient.invalidateQueries({ queryKey: ['teaching-assignments'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to remove assignments.'));
    } finally {
      setDeletingKey(null);
    }
  };

  const columns = [
    {
      key: 'teacher_name',
      label: 'Teacher',
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
            title="Edit assignments"
          >
            <FiEdit2 size={14} />
          </button>
          <button
            type="button"
            className="btn btn-sm btn-outline-danger"
            disabled={deletingKey === row.key}
            onClick={(e) => { e.stopPropagation(); handleDelete(row); }}
            title="Remove all assignments"
          >
            {deletingKey === row.key ? '…' : <FiTrash2 size={14} />}
          </button>
        </div>
      ),
    }] : []),
  ];

  const hasFilters = Boolean(filters.teacher || filters.school_class || filters.subject);
  const completeLineCount = form.lines.filter((line) => line.school_class && line.subject).length;

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/academics" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Academics
        </Link>
      </div>

      <PageHeader
        title="Subject assignments"
        subtitle="Map each teacher to the subjects they teach in each class — e.g. Mathematics in G7 and Physics in G6 for the same teacher."
        actions={canManage && (
          <button
            type="button"
            className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
            onClick={openCreate}
          >
            <FiPlus size={16} /> Assign teacher
          </button>
        )}
      />

      <div className="apex-card p-3 p-md-4 mb-4">
        <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
          <FiFilter size={14} className="text-muted" />
          <span className="small fw-semibold text-muted">Filter</span>
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
        <div className="alert alert-danger">Unable to load teaching assignments.</div>
      ) : (
        <div className="apex-card p-3 p-md-4">
          <DataTable
            columns={columns}
            data={teacherRows}
            loading={isLoading}
            onRowClick={canManage ? openEdit : undefined}
            emptyState={(
              <ModuleEmptyState
                icon={FiUserCheck}
                title={canManage ? 'No teaching assignments yet' : 'No assignments linked to you'}
                message={
                  canManage
                    ? 'Assign a teacher to one or more class–subject pairings. The same teacher can teach different subjects in different classes.'
                    : 'Your class and subject pairings appear here once the Director of Studies or school admin assigns you.'
                }
                actionLabel={canManage ? 'Assign teacher' : undefined}
                onAction={canManage ? openCreate : undefined}
              />
            )}
          />
        </div>
      )}

      <Modal
        show={showModal}
        onHide={() => setShowModal(false)}
        title={editing ? 'Edit teacher assignments' : 'Assign teacher'}
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
            <label className="form-label small fw-medium">Teacher *</label>
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
                  Add one row per class and subject — e.g. G7 + Mathematics, G6 + Physics.
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
              placeholder="Optional e.g. Part-time, shared with Ms. Wanjiku"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default SubjectAssignments;