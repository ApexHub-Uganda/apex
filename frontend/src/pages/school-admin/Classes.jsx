import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiPlus } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { Modal } from '../../components/Modal';
import {
  academicYearsService, classesService,
} from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';

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
  section: '', capacity: 40, room: '',
};

export function Classes() {
  const queryClient = useQueryClient();
  const { canWriteModule } = usePermissions();
  const canManage = canWriteModule('classes') || canWriteModule('core_management');
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const { data: classes = [], isLoading, isError } = useQuery({
    queryKey: ['classes'],
    queryFn: () => classesService.list(),
  });

  const { data: years = [] } = useQuery({
    queryKey: ['academic-years'],
    queryFn: () => academicYearsService.list(),
  });

  const openCreate = () => {
    const current = years.find((y) => y.is_current);
    setEditing(null);
    setForm({ ...EMPTY_FORM, academic_year: current?.id || '' });
    setShowModal(true);
  };

  const openEdit = (row) => {
    setEditing(row);
    setForm({
      name: row.name || '',
      code: row.code || '',
      academic_year: row.academic_year || '',
      level_type: row.level_type || '',
      curriculum: row.curriculum || 'cbc',
      section: row.section || '',
      capacity: row.capacity || 40,
      room: row.room || '',
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editing) {
        await classesService.update(editing.id, form);
        notify.success('Class updated.');
      } else {
        await classesService.create(form);
        notify.success('Class created.');
      }
      await queryClient.invalidateQueries({ queryKey: ['classes'] });
      setShowModal(false);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to save class.'));
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { key: 'name', label: 'Class', accessor: 'name', sortable: true },
    { key: 'code', label: 'Code', accessor: 'code', sortable: true },
    { key: 'academic_year_name', label: 'Year', accessor: 'academic_year_name' },
    {
      key: 'level_type',
      label: 'Level',
      render: (row) => LEVEL_OPTIONS.find((o) => o.value === row.level_type)?.label || '—',
    },
    {
      key: 'curriculum',
      label: 'Curriculum',
      render: (row) => CURRICULUM_OPTIONS.find((o) => o.value === row.curriculum)?.label || row.curriculum,
    },
    { key: 'section', label: 'Section', accessor: 'section' },
    { key: 'class_teacher_name', label: 'Class Teacher', accessor: 'class_teacher_name' },
    { key: 'student_count', label: 'Students', accessor: 'student_count', sortable: true },
    { key: 'capacity', label: 'Capacity', accessor: 'capacity' },
    { key: 'room', label: 'Room', accessor: 'room' },
  ];

  return (
    <div>
      <PageHeader
        title="Classes"
        subtitle="CBC and 8-4-4 class structure with sections, capacity, and room allocation"
        actions={canManage && (
          <button type="button" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1" onClick={openCreate}>
            <FiPlus size={16} /> Add Class
          </button>
        )}
      />

      {isError ? (
        <div className="alert alert-danger">Unable to load classes.</div>
      ) : (
        <div className="apex-card p-3 p-md-4">
          <DataTable
            columns={columns}
            data={classes}
            loading={isLoading}
            onRowClick={canManage ? openEdit : undefined}
            emptyState={(
              <ModuleEmptyState
                title="No classes yet"
                message="Create classes for the current academic year before enrolling students."
                actionLabel={canManage ? 'Add Class' : undefined}
                onAction={canManage ? openCreate : undefined}
              />
            )}
          />
        </div>
      )}

      <Modal
        show={showModal}
        onHide={() => setShowModal(false)}
        title={editing ? 'Edit Class' : 'Add Class'}
        size="lg"
        footer={(
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowModal(false)}>Cancel</button>
            <button type="button" className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save class'}
            </button>
          </>
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
          <div className="col-md-6">
            <label className="form-label small fw-medium">Room</label>
            <input className="form-control" value={form.room} onChange={(e) => setForm({ ...form, room: e.target.value })} />
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default Classes;