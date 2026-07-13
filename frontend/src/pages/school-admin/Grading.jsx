import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiAward, FiEdit2, FiPlus, FiTrash2, FiX } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { Modal } from '../../components/Modal';
import { gradingSchemesService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { alert, extractApiError, notify } from '../../utils/notify';

const EMPTY_BAND = { min_score: '', max_score: '', grade: '', grade_point: '', remarks: '' };
const EMPTY_FORM = {
  name: '',
  description: '',
  is_default: false,
  bands: [{ ...EMPTY_BAND }],
};

export function Grading() {
  const queryClient = useQueryClient();
  const { canWriteFeature, isSchoolAdmin } = usePermissions();
  const canManage = isSchoolAdmin || canWriteFeature('grading');

  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const { data: schemes = [], isLoading, isError } = useQuery({
    queryKey: ['grading-schemes'],
    queryFn: () => gradingSchemesService.list({ page_size: 200 }),
  });

  const openCreate = () => {
    setEditing(null);
    setForm({ ...EMPTY_FORM, bands: [{ ...EMPTY_BAND }] });
    setShowModal(true);
  };

  const openEdit = (row) => {
    setEditing(row);
    setForm({
      name: row.name || '',
      description: row.description || '',
      is_default: Boolean(row.is_default),
      bands: (row.bands || []).length
        ? row.bands.map((band) => ({
          min_score: band.min_score ?? '',
          max_score: band.max_score ?? '',
          grade: band.grade || '',
          grade_point: band.grade_point ?? '',
          remarks: band.remarks || '',
        }))
        : [{ ...EMPTY_BAND }],
    });
    setShowModal(true);
  };

  const addBand = () => {
    setForm((prev) => ({ ...prev, bands: [...prev.bands, { ...EMPTY_BAND }] }));
  };

  const removeBand = (index) => {
    setForm((prev) => {
      if (prev.bands.length === 1) return { ...prev, bands: [{ ...EMPTY_BAND }] };
      return { ...prev, bands: prev.bands.filter((_, i) => i !== index) };
    });
  };

  const updateBand = (index, field, value) => {
    setForm((prev) => ({
      ...prev,
      bands: prev.bands.map((band, i) => (i === index ? { ...band, [field]: value } : band)),
    }));
  };

  const handleSave = async () => {
    const completeBands = form.bands.filter((b) => b.grade && b.min_score !== '' && b.max_score !== '');
    if (!form.name.trim()) {
      notify.error('Enter a name for the grading scheme.');
      return;
    }
    if (!completeBands.length) {
      notify.error('Add at least one complete grade band (min, max, and letter grade).');
      return;
    }

    setSaving(true);
    try {
      await gradingSchemesService.sync({
        ...(editing ? { id: editing.id } : {}),
        name: form.name.trim(),
        description: form.description,
        is_default: form.is_default,
        bands: completeBands.map((band) => ({
          min_score: Number(band.min_score),
          max_score: Number(band.max_score),
          grade: band.grade.trim(),
          grade_point: band.grade_point === '' ? null : Number(band.grade_point),
          remarks: band.remarks,
        })),
      });
      notify.success(editing ? 'Grading scheme updated.' : 'Grading scheme created.');
      await queryClient.invalidateQueries({ queryKey: ['grading-schemes'] });
      setShowModal(false);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to save grading scheme.'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (row) => {
    const result = await alert.delete(row.name);
    if (!result.isConfirmed) return;
    setDeletingId(row.id);
    try {
      await gradingSchemesService.delete(row.id);
      notify.success('Grading scheme removed.');
      await queryClient.invalidateQueries({ queryKey: ['grading-schemes'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to remove grading scheme.'));
    } finally {
      setDeletingId(null);
    }
  };

  const columns = [
    {
      key: 'name',
      label: 'Scheme',
      accessor: 'name',
      sortable: true,
    },
    {
      key: 'bands',
      label: 'Grade bands',
      truncate: false,
      render: (row) => (
        <div className="subject-assignment-table-chips">
          {(row.bands || []).map((band) => (
            <span key={`${band.grade}-${band.min_score}`} className="subject-assignment-table-chip" title={band.remarks || ''}>
              {band.grade} {band.min_score}–{band.max_score}
            </span>
          ))}
        </div>
      ),
    },
    {
      key: 'band_count',
      label: 'Bands',
      render: (row) => <span className="text-muted small">{row.band_count ?? row.bands?.length ?? 0}</span>,
    },
    {
      key: 'is_default',
      label: 'Default',
      render: (row) => (row.is_default
        ? <span className="badge text-bg-primary-subtle border text-primary">Default</span>
        : '—'),
    },
    ...(canManage ? [{
      key: 'actions',
      label: '',
      truncate: false,
      render: (row) => (
        <div className="apex-table-row-actions">
          <button type="button" className="btn btn-sm btn-outline-primary" onClick={(e) => { e.stopPropagation(); openEdit(row); }}>
            <FiEdit2 size={14} />
          </button>
          <button
            type="button"
            className="btn btn-sm btn-outline-danger"
            disabled={deletingId === row.id}
            onClick={(e) => { e.stopPropagation(); handleDelete(row); }}
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
        <Link to="/school-admin/academics" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Academics
        </Link>
      </div>

      <PageHeader
        title="Grading schemes"
        subtitle="Create named grading schemes with score ranges and letter grades. Teachers pick a scheme when calculating grades from entered marks."
        actions={canManage && (
          <button type="button" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1" onClick={openCreate}>
            <FiPlus size={16} /> New scheme
          </button>
        )}
      />

      {isError ? (
        <div className="alert alert-danger">Unable to load grading schemes.</div>
      ) : (
        <div className="apex-card p-3 p-md-4">
          <DataTable
            columns={columns}
            data={schemes}
            loading={isLoading}
            onRowClick={canManage ? openEdit : undefined}
            emptyState={(
              <ModuleEmptyState
                icon={FiAward}
                title="No grading schemes yet"
                message="Define how percentage scores map to letter grades — e.g. A (80–100), B (70–79)."
                actionLabel={canManage ? 'New scheme' : undefined}
                onAction={canManage ? openCreate : undefined}
              />
            )}
          />
        </div>
      )}

      <Modal
        show={showModal}
        onHide={() => setShowModal(false)}
        title={editing ? 'Edit grading scheme' : 'New grading scheme'}
        size="lg"
        footer={(
          <button type="button" className="btn btn-primary ms-auto" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save scheme'}
          </button>
        )}
      >
        <div className="row g-3">
          <div className="col-md-8">
            <label className="form-label small fw-medium">Scheme name *</label>
            <input
              className="form-control"
              placeholder="e.g. O-Level Grading, CBC Rubric"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div className="col-md-4 d-flex align-items-end">
            <div className="form-check mb-2">
              <input
                className="form-check-input"
                type="checkbox"
                id="grading-default"
                checked={form.is_default}
                onChange={(e) => setForm({ ...form, is_default: e.target.checked })}
              />
              <label className="form-check-label small" htmlFor="grading-default">Default scheme</label>
            </div>
          </div>
          <div className="col-12">
            <label className="form-label small fw-medium">Description</label>
            <input
              className="form-control"
              placeholder="Optional note for teachers"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <div className="col-12">
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-2">
              <div>
                <label className="form-label small fw-medium mb-0">Grade bands *</label>
                <p className="form-text mb-0">Percentage ranges (0–100) mapped to letter grades.</p>
              </div>
            </div>
            <div className="grading-band-lines">
              {form.bands.map((band, index) => (
                <div key={`band-${index}`} className="grading-band-line">
                  <div className="grading-band-fields">
                    <div>
                      <label className="form-label small text-muted mb-1">Min %</label>
                      <input
                        type="number"
                        className="form-control form-control-sm"
                        min="0"
                        max="100"
                        value={band.min_score}
                        onChange={(e) => updateBand(index, 'min_score', e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="form-label small text-muted mb-1">Max %</label>
                      <input
                        type="number"
                        className="form-control form-control-sm"
                        min="0"
                        max="100"
                        value={band.max_score}
                        onChange={(e) => updateBand(index, 'max_score', e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="form-label small text-muted mb-1">Grade</label>
                      <input
                        className="form-control form-control-sm"
                        placeholder="A"
                        value={band.grade}
                        onChange={(e) => updateBand(index, 'grade', e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="form-label small text-muted mb-1">Points</label>
                      <input
                        type="number"
                        step="0.1"
                        className="form-control form-control-sm"
                        value={band.grade_point}
                        onChange={(e) => updateBand(index, 'grade_point', e.target.value)}
                      />
                    </div>
                    <div className="grading-band-remarks">
                      <label className="form-label small text-muted mb-1">Remarks</label>
                      <input
                        className="form-control form-control-sm"
                        placeholder="Excellent"
                        value={band.remarks}
                        onChange={(e) => updateBand(index, 'remarks', e.target.value)}
                      />
                    </div>
                  </div>
                  <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => removeBand(index)} aria-label="Remove band">
                    <FiX size={14} />
                  </button>
                </div>
              ))}
            </div>
            <button type="button" className="btn btn-sm btn-outline-primary d-inline-flex align-items-center gap-1 mt-2" onClick={addBand}>
              <FiPlus size={14} /> Add band
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default Grading;