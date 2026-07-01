import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useQuery } from '@tanstack/react-query';
import { FiPlus, FiEdit2, FiTrash2, FiAlertTriangle } from 'react-icons/fi';
import PageHeader from './PageHeader';
import DataTable from './DataTable';
import Modal from './Modal';
import StatusBadge from './StatusBadge';
import ModuleEmptyState from './ModuleEmptyState';
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
  extraActions,
}) {
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
        <div className="d-flex gap-1">
          {extraActions?.(row, { refetch })}
          {!readOnly && onUpdate && (
            <button className="btn btn-sm btn-outline-primary" onClick={() => openEdit(row)}>
              <FiEdit2 size={14} />
            </button>
          )}
          {!readOnly && onDelete && (
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
          !readOnly && onCreate ? (
            <button className="btn btn-primary d-flex align-items-center gap-2" onClick={openCreate}>
              <FiPlus /> {createLabel}
            </button>
          ) : null
        }
      />

      {isError ? (
        <div className="apex-card">
          <ModuleEmptyState
            title={`${title} not set up yet`}
            message={`We couldn't load existing ${title.toLowerCase()} records. You can still create new data — your plan includes this module.`}
            actionLabel={!readOnly && onCreate ? createLabel : undefined}
            onAction={!readOnly && onCreate ? openCreate : undefined}
            icon={FiAlertTriangle}
          />
        </div>
      ) : showEmpty ? (
        <div className="apex-card">
          <ModuleEmptyState
            title={`No ${title.toLowerCase()} yet`}
            message={`This module is ready on your plan, but no records exist yet. Create your first entry to populate ${title.toLowerCase()}.`}
            actionLabel={!readOnly && onCreate ? createLabel : undefined}
            onAction={!readOnly && onCreate ? openCreate : undefined}
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

      {!readOnly && formFields?.length > 0 && (
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