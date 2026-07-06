import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiPlus, FiEdit2, FiTrash2, FiAlertTriangle } from 'react-icons/fi';
import PageHeader from './PageHeader';
import DataTable from './DataTable';
import Modal from './Modal';
import StatusBadge from './StatusBadge';
import ModuleEmptyState from './ModuleEmptyState';
import { useTenantContext } from '../context/TenantContext';
import { alert, extractApiError, notify } from '../utils/notify';

export function ModulePage({
  title,
  subtitle,
  columns,
  fetchData,
  queryKey,
  formFields,
  onCreate,
  onUpdate,
  onDelete,
  filters,
  createLabel = 'Add New',
  readOnly = false,
  featureKey = null,
  extraActions,
}) {
  const { canWriteFeature, canAccessFeature, isSchoolAdmin } = useTenantContext();
  const canRead = !featureKey || isSchoolAdmin || canAccessFeature(featureKey, false);
  const canMutate = !readOnly && canRead && (
    !featureKey || isSchoolAdmin || canWriteFeature(featureKey)
  );
  const queryClient = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: queryKey || [title],
    queryFn: () => fetchData(),
  });

  const { register, handleSubmit, reset, formState: { errors } } = useForm();

  const openCreate = () => {
    setEditing(null);
    reset({});
    setShowModal(true);
  };

  const openEdit = (row) => {
    setEditing(row);
    reset(row);
    setShowModal(true);
  };

  const onSubmit = async (formData) => {
    setSaving(true);
    try {
      if (editing) {
        await onUpdate?.(editing.id, formData);
        notify.success(`${title} updated successfully.`);
      } else {
        await onCreate?.(formData);
        notify.success(`${title} created successfully.`);
      }
      setShowModal(false);
      await queryClient.invalidateQueries({ queryKey: queryKey || [title] });
      refetch();
    } catch (err) {
      notify.error(extractApiError(err, `Unable to save ${title.toLowerCase()}.`));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (row) => {
    const result = await alert.delete(`"${row.name || row.title || title}"`);
    if (!result.isConfirmed) return;
    try {
      await onDelete?.(row.id);
      notify.success('Record deleted successfully.');
      await queryClient.invalidateQueries({ queryKey: queryKey || [title] });
      refetch();
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to delete record.'));
    }
  };

  const tableColumns = [
    ...columns,
    ...((onUpdate || onDelete || extraActions) ? [{
      key: 'actions',
      label: 'Actions',
      render: (row) => (
        <div className="apex-table-row-actions">
          {extraActions?.(row, { refetch })}
          {canMutate && onUpdate && (
            <button className="btn btn-sm btn-outline-primary" onClick={() => openEdit(row)}>
              <FiEdit2 size={14} />
            </button>
          )}
          {canMutate && onDelete && (
            <button className="btn btn-sm btn-outline-danger" onClick={() => handleDelete(row)}>
              <FiTrash2 size={14} />
            </button>
          )}
        </div>
      ),
    }] : []),
  ];

  const records = Array.isArray(data) ? data : (data?.results || data?.items || []);
  const showEmpty = !isLoading && !isError && records.length === 0;

  return (
    <div>
      <PageHeader
        title={title}
        subtitle={subtitle}
        actions={
          canMutate && onCreate ? (
            <button className="btn btn-primary d-flex align-items-center gap-2" onClick={openCreate}>
              <FiPlus /> {createLabel}
            </button>
          ) : null
        }
      />

      {canRead && !canMutate && (onCreate || onUpdate || onDelete) && (
        <div className="alert alert-light border mb-3 py-2 px-3 small">
          You have read-only access to {title.toLowerCase()}. Contact your school admin to request write permission.
        </div>
      )}

      {isError ? (
        <div className="apex-card">
          <ModuleEmptyState
            title={`${title} not set up yet`}
            message={
              canMutate
                ? `We couldn't load existing ${title.toLowerCase()} records. You can still create new data — your plan includes this module.`
                : `We couldn't load existing ${title.toLowerCase()} records.`
            }
            actionLabel={canMutate && onCreate ? createLabel : undefined}
            onAction={canMutate && onCreate ? openCreate : undefined}
            icon={FiAlertTriangle}
          />
        </div>
      ) : showEmpty ? (
        <div className="apex-card">
          <ModuleEmptyState
            title={`No ${title.toLowerCase()} yet`}
            message={
              canMutate
                ? `This module is ready on your plan, but no records exist yet. Create your first entry to populate ${title.toLowerCase()}.`
                : `No ${title.toLowerCase()} records yet. You can view entries here when they are added.`
            }
            actionLabel={canMutate && onCreate ? createLabel : undefined}
            onAction={canMutate && onCreate ? openCreate : undefined}
          />
        </div>
      ) : (
        <DataTable
          columns={tableColumns}
          data={records}
          loading={isLoading}
          filters={filters}
        />
      )}

      {canMutate && formFields?.length > 0 && (
        <Modal
          show={showModal}
          onHide={() => setShowModal(false)}
          title={editing ? `Edit ${title}` : `Add ${title}`}
          footer={
            <>
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSubmit(onSubmit)} disabled={saving}>
                {saving ? 'Saving...' : (editing ? 'Update' : 'Create')}
              </button>
            </>
          }
        >
          <form onSubmit={handleSubmit(onSubmit)}>
            {editing?.id && (
              <div className="mb-3">
                <label className="form-label small text-muted">Record ID</label>
                <input className="form-control form-control-sm font-monospace" readOnly value={editing.id} />
                <div className="form-text">Internal identifier — only visible when editing this record.</div>
              </div>
            )}
            {formFields.map((field) => (
              <div key={field.name} className="mb-3">
                <label className="form-label fw-medium">{field.label}</label>
                {field.type === 'select' ? (
                  <select className="form-select" {...register(field.name, { required: field.required })}>
                    <option value="">Select...</option>
                    {field.options?.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                ) : field.type === 'textarea' ? (
                  <textarea className="form-control" rows={3} {...register(field.name, { required: field.required })} />
                ) : field.type === 'checkbox' ? (
                  <div className="form-check">
                    <input type="checkbox" className="form-check-input" {...register(field.name)} id={field.name} />
                    <label className="form-check-label" htmlFor={field.name}>{field.checkboxLabel || field.label}</label>
                  </div>
                ) : (
                  <input
                    type={field.type || 'text'}
                    className="form-control"
                    placeholder={field.placeholder}
                    {...register(field.name, { required: field.required })}
                  />
                )}
                {errors[field.name] && <div className="text-danger small mt-1">This field is required</div>}
              </div>
            ))}
          </form>
        </Modal>
      )}
    </div>
  );
}

export { StatusBadge };
export default ModulePage;