import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiEdit2, FiMapPin, FiPlus, FiTrash2 } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import StatusBadge from '../../components/StatusBadge';
import { Modal } from '../../components/Modal';
import { campusesService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { alert, extractApiError, notify } from '../../utils/notify';

const EMPTY_FORM = {
  name: '',
  code: '',
  address: '',
  city: '',
  phone: '',
  email: '',
  is_main: false,
  is_active: true,
  notes: '',
};

export function Campuses() {
  const queryClient = useQueryClient();
  const { canWriteFeature, isSchoolAdmin } = usePermissions();
  const canManage = isSchoolAdmin || canWriteFeature('multi_campus_support');

  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const { data = [], isLoading, isError } = useQuery({
    queryKey: ['campuses'],
    queryFn: () => campusesService.list({ page_size: 200 }),
  });

  const openCreate = () => {
    setEditing(null);
    setForm({ ...EMPTY_FORM, is_main: data.length === 0 });
    setShowModal(true);
  };

  const openEdit = (row) => {
    setEditing(row);
    setForm({
      name: row.name || '',
      code: row.code || '',
      address: row.address || '',
      city: row.city || '',
      phone: row.phone || '',
      email: row.email || '',
      is_main: Boolean(row.is_main),
      is_active: row.is_active !== false,
      notes: row.notes || '',
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.name.trim() || !form.code.trim()) {
      notify.error('Campus name and code are required.');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        ...form,
        name: form.name.trim(),
        code: form.code.trim().toUpperCase(),
      };
      if (editing) {
        await campusesService.update(editing.id, payload);
        notify.success('Campus updated.');
      } else {
        await campusesService.create(payload);
        notify.success('Campus created.');
      }
      await queryClient.invalidateQueries({ queryKey: ['campuses'] });
      setShowModal(false);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to save campus.'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (row) => {
    const result = await alert.delete(`"${row.name || 'this campus'}"`);
    if (!result.isConfirmed) return;
    setDeletingId(row.id);
    try {
      await campusesService.delete(row.id);
      notify.success('Campus deleted.');
      await queryClient.invalidateQueries({ queryKey: ['campuses'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to delete campus.'));
    } finally {
      setDeletingId(null);
    }
  };

  const columns = [
    {
      key: 'name',
      label: 'Campus',
      accessor: 'name',
      sortable: true,
      render: (row) => (
        <div>
          <div className="fw-semibold d-flex align-items-center gap-2">
            <FiMapPin className="text-primary" size={14} />
            {row.name}
            {row.is_main && (
              <span className="badge text-bg-primary-subtle border text-primary">Main</span>
            )}
          </div>
          <div className="small text-muted">{row.code}</div>
        </div>
      ),
    },
    { key: 'city', label: 'City', accessor: 'city' },
    { key: 'phone', label: 'Phone', accessor: 'phone' },
    { key: 'email', label: 'Email', accessor: 'email' },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <StatusBadge status={row.is_active ? 'active' : 'inactive'} />,
    },
    ...(canManage ? [{
      key: 'actions',
      label: '',
      render: (row) => (
        <div className="apex-table-row-actions">
          <button
            type="button"
            className="btn btn-sm btn-outline-primary"
            onClick={(e) => { e.stopPropagation(); openEdit(row); }}
            title="Edit"
          >
            <FiEdit2 size={14} />
          </button>
          <button
            type="button"
            className="btn btn-sm btn-outline-danger"
            disabled={deletingId === row.id}
            onClick={(e) => { e.stopPropagation(); handleDelete(row); }}
            title="Delete"
          >
            {deletingId === row.id ? '…' : <FiTrash2 size={14} />}
          </button>
        </div>
      ),
    }] : []),
  ];

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/core" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Core Management
        </Link>
      </div>

      <PageHeader
        title="Multi-campus"
        subtitle="Manage branches and physical campuses under this school"
        actions={canManage && (
          <button type="button" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1" onClick={openCreate}>
            <FiPlus size={16} /> Add Campus
          </button>
        )}
      />

      {isError ? (
        <div className="alert alert-danger">Unable to load campuses. Confirm multi-campus is on your plan.</div>
      ) : (
        <div className="apex-card p-3 p-md-4">
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
            onRowClick={canManage ? openEdit : undefined}
            emptyState={(
              <ModuleEmptyState
                title="No campuses yet"
                message="Add your main campus first, then additional branches if your plan allows multi-campus."
                actionLabel={canManage ? 'Add Campus' : undefined}
                onAction={canManage ? openCreate : undefined}
              />
            )}
          />
        </div>
      )}

      <Modal
        show={showModal}
        onHide={() => setShowModal(false)}
        title={editing ? 'Edit Campus' : 'Add Campus'}
        size="lg"
        footer={(
          <button type="button" className="btn btn-primary ms-auto" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save campus'}
          </button>
        )}
      >
        <div className="row g-3">
          <div className="col-md-8">
            <label className="form-label small fw-medium">Campus name *</label>
            <input
              className="form-control"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Main Campus"
            />
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Code *</label>
            <input
              className="form-control"
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
              placeholder="MAIN"
            />
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">City</label>
            <input
              className="form-control"
              value={form.city}
              onChange={(e) => setForm({ ...form, city: e.target.value })}
            />
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Phone</label>
            <input
              className="form-control"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </div>
          <div className="col-12">
            <label className="form-label small fw-medium">Address</label>
            <textarea
              className="form-control"
              rows={2}
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
            />
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Email</label>
            <input
              type="email"
              className="form-control"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </div>
          <div className="col-md-6 d-flex align-items-end gap-4">
            <div className="form-check form-switch">
              <input
                type="checkbox"
                className="form-check-input"
                checked={form.is_main}
                onChange={(e) => setForm({ ...form, is_main: e.target.checked })}
                id="campus-main"
              />
              <label className="form-check-label small" htmlFor="campus-main">Main campus</label>
            </div>
            <div className="form-check form-switch">
              <input
                type="checkbox"
                className="form-check-input"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                id="campus-active"
              />
              <label className="form-check-label small" htmlFor="campus-active">Active</label>
            </div>
          </div>
          <div className="col-12">
            <label className="form-label small fw-medium">Notes</label>
            <textarea
              className="form-control"
              rows={2}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default Campuses;
