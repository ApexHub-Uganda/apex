import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  FiChevronDown, FiChevronRight, FiLayers, FiPlus, FiUsers,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { Modal } from '../../components/Modal';
import {
  academicYearsService, classesService,
} from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { alert, extractApiError, notify } from '../../utils/notify';

const LEVEL_OPTIONS = [
  { value: '', label: 'Select level' },
  { value: 'pre_primary', label: 'Pre-Primary' },
  { value: 'primary', label: 'Primary' },
  { value: 'junior_secondary', label: 'Junior Secondary' },
  { value: 'senior_secondary', label: 'Senior Secondary' },
  { value: 'tertiary', label: 'Tertiary' },
];

const CURRICULUM_OPTIONS = [
  { value: 'cbc', label: 'CBC' },
  { value: '844', label: '8-4-4' },
  { value: 'igcse', label: 'IGCSE' },
  { value: 'other', label: 'Other' },
];

const EMPTY_FORM = {
  name: '', code: '', academic_year: '', level_type: '', curriculum: 'cbc',
  section: '', class_teacher: '', capacity: 40, room: '',
};

export function Classes() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { canReadFeature, canWriteFeature } = usePermissions();
  const canView = canReadFeature('classes');
  const canManage = canWriteFeature('classes');
  const [expanded, setExpanded] = useState(() => new Set());
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const pendingEditIdRef = useRef(null);

  const { data: classes = [], isLoading, isError } = useQuery({
    queryKey: ['classes-overview'],
    queryFn: () => classesService.listOverview(),
  });

  const { data: years = [] } = useQuery({
    queryKey: ['academic-years'],
    queryFn: () => academicYearsService.list(),
  });

  const { data: formOptions } = useQuery({
    queryKey: ['classes-form-options'],
    queryFn: () => classesService.formOptions(),
    enabled: showModal,
  });

  const teachers = formOptions?.teachers || [];

  useEffect(() => {
    const editClassId = location.state?.editClassId || pendingEditIdRef.current;
    if (!editClassId) return;
    if (!classes.length) {
      pendingEditIdRef.current = editClassId;
      return;
    }

    const row = classes.find((item) => String(item.id) === String(editClassId));
    if (!row) return;

    pendingEditIdRef.current = null;
    openEdit(row);
    navigate(location.pathname, { replace: true, state: {} });
  }, [location.state, classes, location.pathname, navigate]);

  const openCreate = () => {
    const current = years.find((y) => y.is_current);
    setEditing(null);
    setForm({ ...EMPTY_FORM, academic_year: current?.id || '' });
    setShowModal(true);
  };

  const openEdit = async (row) => {
    try {
      const detail = await classesService.get(row.id);
      setEditing(row);
      setForm({
        name: detail.name || '',
        code: detail.code || '',
        academic_year: detail.academic_year || '',
        level_type: detail.level_type || '',
        curriculum: detail.curriculum || 'cbc',
        section: detail.section || '',
        class_teacher: detail.class_teacher || '',
        capacity: detail.capacity || 40,
        room: detail.room || '',
      });
      setShowModal(true);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to load class details.'));
    }
  };

  const toggleExpanded = (classId) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(classId)) next.delete(classId);
      else next.add(classId);
      return next;
    });
  };

  const openClass = (classId, streamId = null) => {
    if (streamId) {
      navigate(`/school-admin/classes/${classId}?stream=${streamId}`);
      return;
    }
    navigate(`/school-admin/classes/${classId}`);
  };

  const handleDelete = async () => {
    if (!editing) return;
    const preview = await classesService.getDeletionPreview(editing.id);
    if (!preview?.can_delete) {
      notify.error(preview?.blockers?.[0] || 'This class cannot be deleted right now.');
      return;
    }

    const result = await alert.delete(`class "${editing.name}"`);
    if (!result.isConfirmed) return;

    setSaving(true);
    try {
      await classesService.delete(editing.id);
      notify.success('Class deleted.');
      await queryClient.invalidateQueries({ queryKey: ['classes-overview'] });
      await queryClient.invalidateQueries({ queryKey: ['classes'] });
      setShowModal(false);
      setEditing(null);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to delete class.'));
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        ...form,
        class_teacher: form.class_teacher || null,
      };
      if (editing) {
        await classesService.update(editing.id, payload);
        notify.success('Class updated.');
      } else {
        await classesService.create(payload);
        notify.success('Class created.');
      }
      await queryClient.invalidateQueries({ queryKey: ['classes-overview'] });
      await queryClient.invalidateQueries({ queryKey: ['classes'] });
      setShowModal(false);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to save class.'));
    } finally {
      setSaving(false);
    }
  };

  const totalStudents = useMemo(
    () => classes.reduce((sum, row) => sum + (row.student_count || 0), 0),
    [classes],
  );

  return (
    <div>
      <PageHeader
        title="Classes"
        subtitle="Browse classes and their streams — open any class to see the teacher, prefects, and student list"
        actions={canManage && (
          <button type="button" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1" onClick={openCreate}>
            <FiPlus size={16} /> Add Class
          </button>
        )}
      />

      {!canView ? (
        <div className="alert alert-warning">You do not have permission to view classes.</div>
      ) : isError ? (
        <div className="alert alert-danger">Unable to load classes.</div>
      ) : (
        <div className="apex-card p-3 p-md-4">
          {!isLoading && classes.length > 0 && (
            <div className="d-flex flex-wrap gap-3 mb-4 text-muted small">
              <span><strong>{classes.length}</strong> classes</span>
              <span><strong>{totalStudents}</strong> enrolled students</span>
            </div>
          )}

          {isLoading ? (
            <div className="py-5 text-center">
              <div className="spinner-border text-primary" role="status" />
            </div>
          ) : classes.length === 0 ? (
            <ModuleEmptyState
              title="No classes yet"
              message="Create classes for the current academic year before enrolling students."
              actionLabel={canManage ? 'Add Class' : undefined}
              onAction={canManage ? openCreate : undefined}
            />
          ) : (
            <div className="class-overview-list">
              {classes.map((row) => {
                const isOpen = expanded.has(row.id);
                const hasStreams = row.has_streams && row.streams?.length > 0;
                return (
                  <div key={row.id} className="class-overview-item">
                    <div className="class-overview-row">
                      {hasStreams ? (
                        <button
                          type="button"
                          className="class-overview-expand"
                          onClick={() => toggleExpanded(row.id)}
                          aria-label={isOpen ? 'Collapse streams' : 'Expand streams'}
                        >
                          {isOpen ? <FiChevronDown size={18} /> : <FiChevronRight size={18} />}
                        </button>
                      ) : (
                        <span className="class-overview-expand-placeholder" />
                      )}

                      <button
                        type="button"
                        className="class-overview-main"
                        onClick={() => openClass(row.id)}
                      >
                        <div>
                          <div className="fw-semibold">{row.name}</div>
                          <div className="text-muted small">
                            {row.code} · {row.academic_year_name}
                            {row.class_teacher?.display ? ` · ${row.class_teacher.display}` : ' · No class teacher'}
                          </div>
                        </div>
                        <div className="class-overview-meta text-end">
                          <div className="d-inline-flex align-items-center gap-1 small">
                            <FiUsers size={14} />
                            {row.student_count ?? 0}
                          </div>
                          {hasStreams && (
                            <div className="text-muted small d-inline-flex align-items-center gap-1 mt-1">
                              <FiLayers size={13} />
                              {row.stream_count} streams
                            </div>
                          )}
                        </div>
                      </button>

                      {canManage && (
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-secondary class-overview-edit"
                          onClick={() => openEdit(row)}
                        >
                          Edit
                        </button>
                      )}
                    </div>

                    {hasStreams && isOpen && (
                      <div className="class-overview-streams">
                        {row.streams.map((stream) => (
                          <button
                            key={stream.id}
                            type="button"
                            className="class-overview-stream"
                            onClick={() => openClass(row.id, stream.id)}
                          >
                            <FiLayers size={14} className="text-primary" />
                            <span className="fw-medium">{stream.name}</span>
                            <span className="text-muted small ms-auto">
                              {stream.student_count ?? 0} students
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      <Modal
        show={showModal}
        onHide={() => setShowModal(false)}
        title={editing ? 'Edit Class' : 'Add Class'}
        size="lg"
        footer={(
          <div className="d-flex gap-2 ms-auto">
            {editing && canManage && (
              <button type="button" className="btn btn-outline-danger" onClick={handleDelete} disabled={saving}>
                Delete class
              </button>
            )}
            {canManage && (
              <button type="button" className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving…' : 'Save class'}
              </button>
            )}
          </div>
        )}
      >
        <div className="row g-3">
          <div className="col-md-6">
            <label className="form-label small fw-medium">Class Name *</label>
            <input className="form-control" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Grade 7" />
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Class Code *</label>
            <input className="form-control" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="e.g. G7A" />
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Academic Year *</label>
            <select className="form-select" value={form.academic_year} onChange={(e) => setForm({ ...form, academic_year: e.target.value })}>
              <option value="">Select year</option>
              {years.map((y) => <option key={y.id} value={y.id}>{y.name}{y.is_current ? ' (current)' : ''}</option>)}
            </select>
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Class Teacher</label>
            <select className="form-select" value={form.class_teacher} onChange={(e) => setForm({ ...form, class_teacher: e.target.value })}>
              <option value="">Not assigned</option>
              {teachers.map((teacher) => (
                <option key={teacher.value} value={teacher.value}>{teacher.label}</option>
              ))}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Level</label>
            <select className="form-select" value={form.level_type} onChange={(e) => setForm({ ...form, level_type: e.target.value })}>
              {LEVEL_OPTIONS.map((o) => <option key={o.value || 'na'} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Curriculum</label>
            <select className="form-select" value={form.curriculum} onChange={(e) => setForm({ ...form, curriculum: e.target.value })}>
              {CURRICULUM_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Section</label>
            <input className="form-control" value={form.section} onChange={(e) => setForm({ ...form, section: e.target.value })} placeholder="A, B, East" />
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Capacity</label>
            <input type="number" className="form-control" value={form.capacity} onChange={(e) => setForm({ ...form, capacity: Number(e.target.value) })} />
          </div>
          <div className="col-md-8">
            <label className="form-label small fw-medium">Room</label>
            <input className="form-control" value={form.room} onChange={(e) => setForm({ ...form, room: e.target.value })} placeholder="Room number or block" />
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default Classes;