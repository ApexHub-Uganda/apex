import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiPlus } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { Modal } from '../../components/Modal';
import { hostelService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';

const formatUGX = (amount) => {
  const n = Number(amount);
  if (Number.isNaN(n) || !amount) return '—';
  return `UGX ${n.toLocaleString('en-UG')}`;
};

const GENDER_OPTIONS = [
  { value: 'male', label: 'Boys' },
  { value: 'female', label: 'Girls' },
  { value: 'mixed', label: 'Mixed' },
];

const EMPTY_FORM = {
  name: '', gender: 'male', address: '', county: '', contact_phone: '',
  monthly_fee: '', total_rooms: 0, capacity: 0,
};

export function Hostel() {
  const queryClient = useQueryClient();
  const { canWriteModule } = usePermissions();
  const canManage = canWriteModule('hostel_management');
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const { data: hostels = [], isLoading, isError } = useQuery({
    queryKey: ['hostels'],
    queryFn: () => hostelService.list(),
  });

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setShowModal(true);
  };

  const openEdit = (row) => {
    setEditing(row);
    setForm({
      name: row.name || '',
      gender: row.gender || 'male',
      address: row.address || '',
      county: row.county || '',
      contact_phone: row.contact_phone || '',
      monthly_fee: row.monthly_fee || '',
      total_rooms: row.total_rooms || 0,
      capacity: row.capacity || 0,
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        ...form,
        monthly_fee: form.monthly_fee || null,
        total_rooms: Number(form.total_rooms) || 0,
        capacity: Number(form.capacity) || 0,
      };
      if (editing) {
        await hostelService.update(editing.id, payload);
        notify.success('Hostel updated.');
      } else {
        await hostelService.create(payload);
        notify.success('Hostel added.');
      }
      await queryClient.invalidateQueries({ queryKey: ['hostels'] });
      setShowModal(false);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to save hostel.'));
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { key: 'name', label: 'Hostel', accessor: 'name', sortable: true },
    {
      key: 'gender',
      label: 'Type',
      render: (row) => GENDER_OPTIONS.find((g) => g.value === row.gender)?.label || row.gender,
    },
    { key: 'county', label: 'County', accessor: 'county' },
    { key: 'contact_phone', label: 'Contact', accessor: 'contact_phone' },
    { key: 'monthly_fee', label: 'Monthly Fee', render: (row) => formatUGX(row.monthly_fee) },
    { key: 'total_rooms', label: 'Rooms', accessor: 'total_rooms' },
    { key: 'capacity', label: 'Capacity', accessor: 'capacity' },
  ];

  return (
    <div>
      <PageHeader
        title="Hostels"
        subtitle="Boarding blocks — warden assignment, county, and monthly fees in UGX"
        actions={canManage && (
          <button type="button" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1" onClick={openCreate}>
            <FiPlus size={16} /> Add Hostel
          </button>
        )}
      />

      {isError ? (
        <div className="alert alert-danger">Unable to load hostel records.</div>
      ) : (
        <div className="apex-card p-3 p-md-4">
          <DataTable
            columns={columns}
            data={hostels}
            loading={isLoading}
            onRowClick={canManage ? openEdit : undefined}
            emptyState={(
              <ModuleEmptyState
                title="No hostels configured"
                message="Add boarding blocks before allocating students to rooms."
                actionLabel={canManage ? 'Add Hostel' : undefined}
                onAction={canManage ? openCreate : undefined}
              />
            )}
          />
        </div>
      )}

      <Modal
        show={showModal}
        onHide={() => setShowModal(false)}
        title={editing ? 'Edit Hostel' : 'Add Hostel'}
        size="lg"
        footer={(
          <button type="button" className="btn btn-primary ms-auto" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save hostel'}
          </button>
        )}
      >
        <div className="row g-3">
          <div className="col-md-6">
            <label className="form-label small fw-medium">Hostel Name *</label>
            <input className="form-control" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Gender *</label>
            <select className="form-select" value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
              {GENDER_OPTIONS.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
            </select>
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">County</label>
            <input className="form-control" value={form.county} onChange={(e) => setForm({ ...form, county: e.target.value })} />
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Contact Phone</label>
            <input className="form-control" value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} />
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Monthly Fee (UGX)</label>
            <input type="number" className="form-control" value={form.monthly_fee} onChange={(e) => setForm({ ...form, monthly_fee: e.target.value })} />
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Total Rooms</label>
            <input type="number" className="form-control" value={form.total_rooms} onChange={(e) => setForm({ ...form, total_rooms: e.target.value })} />
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Capacity</label>
            <input type="number" className="form-control" value={form.capacity} onChange={(e) => setForm({ ...form, capacity: e.target.value })} />
          </div>
          <div className="col-12">
            <label className="form-label small fw-medium">Address</label>
            <textarea className="form-control" rows={2} value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default Hostel;