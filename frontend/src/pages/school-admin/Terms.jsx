import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiPlus } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { Modal } from '../../components/Modal';
import { academicYearsService, termsService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';

const EMPTY_FORM = {
  name: '', academic_year: '', term_number: '', start_date: '', end_date: '',
  reporting_date: '', closing_date: '', is_current: false,
};

export function Terms() {
  const queryClient = useQueryClient();
  const { canWriteModule } = usePermissions();
  const canManage = canWriteModule('terms') || canWriteModule('academics');
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const { data: terms = [], isLoading, isError } = useQuery({
    queryKey: ['terms'],
    queryFn: () => termsService.list(),
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
      academic_year: row.academic_year || '',
      term_number: row.term_number || '',
      start_date: row.start_date || '',
      end_date: row.end_date || '',
      reporting_date: row.reporting_date || '',
      closing_date: row.closing_date || '',
      is_current: row.is_current || false,
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        ...form,
        term_number: form.term_number ? Number(form.term_number) : null,
      };
      if (editing) {
        await termsService.update(editing.id, payload);
        notify.success('Term updated.');
      } else {
        await termsService.create(payload);
        notify.success('Term created.');
      }
      await queryClient.invalidateQueries({ queryKey: ['terms'] });
      setShowModal(false);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to save term.'));
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { key: 'name', label: 'Term', accessor: 'name', sortable: true },
    { key: 'term_number', label: 'No.', accessor: 'term_number' },
    { key: 'academic_year_name', label: 'Academic Year', accessor: 'academic_year_name' },
    { key: 'start_date', label: 'Opens', accessor: 'start_date' },
    { key: 'end_date', label: 'Closes', accessor: 'end_date' },
    { key: 'reporting_date', label: 'Reporting', accessor: 'reporting_date' },
    { key: 'closing_date', label: 'Closing Day', accessor: 'closing_date' },
    {
      key: 'is_current',
      label: 'Current',
      render: (row) => (row.is_current
        ? <span className="badge text-bg-primary-subtle border text-primary">Current</span>
        : '—'),
    },
  ];

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/academics" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Academics
        </Link>
      </div>

      <PageHeader
        title="Terms"
        subtitle="Kenyan 3-term calendar — reporting dates, mid-term breaks, and term numbers"
        actions={canManage && (
          <button type="button" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1" onClick={openCreate}>
            <FiPlus size={16} /> Add Term
          </button>
        )}
      />

      {isError ? (
        <div className="alert alert-danger">Unable to load terms.</div>
      ) : (
        <div className="apex-card p-3 p-md-4">
          <DataTable
            columns={columns}
            data={terms}
            loading={isLoading}
            onRowClick={canManage ? openEdit : undefined}
            emptyState={(
              <ModuleEmptyState
                title="No terms configured"
                message="Set up Term 1, 2, and 3 for the academic year before fee structures."
                actionLabel={canManage ? 'Add Term' : undefined}
                onAction={canManage ? openCreate : undefined}
              />
            )}
          />
        </div>
      )}

      <Modal
        show={showModal}
        onHide={() => setShowModal(false)}
        title={editing ? 'Edit Term' : 'Add Term'}
        size="lg"
        footer={(
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowModal(false)}>Cancel</button>
            <button type="button" className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save term'}
            </button>
          </>
        )}
      >
        <div className="row g-3">
          <div className="col-md-6">
            <label className="form-label small fw-medium">Term Name *</label>
            <input className="form-control" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Term 1" />
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Term Number</label>
            <select className="form-select" value={form.term_number} onChange={(e) => setForm({ ...form, term_number: e.target.value })}>
              <option value="">Select</option>
              <option value="1">1</option>
              <option value="2">2</option>
              <option value="3">3</option>
            </select>
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Academic Year *</label>
            <select className="form-select" value={form.academic_year} onChange={(e) => setForm({ ...form, academic_year: e.target.value })}>
              <option value="">Select year</option>
              {years.map((y) => <option key={y.id} value={y.id}>{y.name}</option>)}
            </select>
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium d-block">Current Term</label>
            <div className="form-check form-switch mt-2">
              <input type="checkbox" className="form-check-input" checked={form.is_current} onChange={(e) => setForm({ ...form, is_current: e.target.checked })} />
              <label className="form-check-label small">Mark as current term</label>
            </div>
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Start Date *</label>
            <input type="date" className="form-control" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">End Date *</label>
            <input type="date" className="form-control" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Reporting Date</label>
            <input type="date" className="form-control" value={form.reporting_date} onChange={(e) => setForm({ ...form, reporting_date: e.target.value })} />
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Closing Date</label>
            <input type="date" className="form-control" value={form.closing_date} onChange={(e) => setForm({ ...form, closing_date: e.target.value })} />
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default Terms;