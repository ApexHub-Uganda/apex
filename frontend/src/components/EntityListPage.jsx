import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiEdit2, FiPlus, FiSend, FiTrash2 } from 'react-icons/fi';
import PageHeader from './PageHeader';
import DataTable from './DataTable';
import ModuleEmptyState from './ModuleEmptyState';
import { Modal } from './Modal';
import StatusBadge from './StatusBadge';
import { usePermissions } from '../hooks/usePermissions';
import {
  classesService,
  termsService,
  subjectsService,
  studentsService,
  staffService,
  routesService,
  examsService,
  subjectPapersService,
  hostelService,
  roomsService,
  inventoryItemsService,
  payrollRunsService,
  supportTicketsService,
  eventsService,
  booksService,
} from '../services/moduleService';
import { validateDeliverableEmail } from '../utils/emailValidation';
import { formatTableCellValue, inferOptionsFromKey } from '../utils/tableDisplay';
import { alert, extractApiError, notify } from '../utils/notify';

const OPTION_LOADERS = {
  classes: () => classesService.list().then((rows) => rows.map((c) => ({
    value: c.id, label: `${c.name} (${c.code})`,
  }))),
  terms: () => termsService.list().then((rows) => rows.map((t) => ({
    value: t.id, label: `${t.name}${t.academic_year_name ? ` — ${t.academic_year_name}` : ''}`,
  }))),
  subjects: () => subjectsService.list().then((rows) => rows.map((s) => ({
    value: s.id, label: `${s.name} (${s.code})`,
  }))),
  students: () => studentsService.list().then((rows) => rows.map((s) => ({
    value: s.id, label: s.full_name || s.admission_number,
  }))),
  staff: () => staffService.list().then((rows) => rows.map((s) => ({
    value: s.id, label: s.full_name || `${s.first_name} ${s.last_name}`.trim(),
  }))),
  routes: () => routesService.list().then((rows) => rows.map((r) => ({
    value: r.id, label: r.name,
  }))),
  exams: () => examsService.list().then((rows) => rows.map((e) => ({
    value: e.id, label: `${e.name}${e.exam_date ? ` — ${e.exam_date}` : ''}`,
  }))),
  subjectPapers: () => subjectPapersService.list().then((rows) => rows.map((p) => ({
    value: p.id,
    label: `${p.code}${p.name ? ` — ${p.name}` : ''}`,
    subjectId: p.subject,
  }))),
  hostels: () => hostelService.list().then((rows) => rows.map((h) => ({
    value: h.id, label: h.name,
  }))),
  rooms: () => roomsService.list().then((rows) => rows.map((r) => ({
    value: r.id, label: `${r.room_number}${r.hostel ? ` (${r.hostel})` : ''}`,
  }))),
  items: () => inventoryItemsService.list().then((rows) => rows.map((i) => ({
    value: i.id, label: `${i.name} (${i.sku})`,
  }))),
  payrollRuns: () => payrollRunsService.list().then((rows) => rows.map((p) => ({
    value: p.id, label: p.title || p.period,
  }))),
  tickets: () => supportTicketsService.list().then((rows) => rows.map((t) => ({
    value: t.id, label: `${t.ticket_number} — ${t.subject}`,
  }))),
  events: () => eventsService.list().then((rows) => rows.map((e) => ({
    value: e.id, label: e.title,
  }))),
  books: () => booksService.list().then((rows) => rows.map((b) => ({
    value: b.id, label: b.title,
  }))),
};

function formatCell(col, row, optionLookups = {}) {
  const val = col.accessor ? row[col.accessor] : row[col.key];
  if (col.format === 'boolean') {
    return val ? <span className="badge text-bg-success-subtle border text-success">Yes</span> : '—';
  }
  if (col.key === 'status' || col.accessor === 'status') {
    return val ? <StatusBadge status={val} /> : '—';
  }
  return formatTableCellValue(col, row, optionLookups);
}

export function EntityListPage({
  title,
  featureKey,
  config,
}) {
  const queryClient = useQueryClient();
  const { canWriteFeature, canWriteModule, isSchoolAdmin } = usePermissions();
  const isDepartmentFeature = featureKey === 'departments' || featureKey === 'hr_departments';
  const canManage = isSchoolAdmin
    || canWriteFeature(featureKey)
    || (isDepartmentFeature && (canWriteModule('core_management') || canWriteModule('human_resource')));

  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(config.emptyForm || {});
  const [saving, setSaving] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const listParams = config.listParams || {};

  const { data: records = [], isLoading, isError } = useQuery({
    queryKey: [...config.queryKey, listParams],
    queryFn: () => config.service.list({ page_size: 200, ...listParams }),
    enabled: Boolean(config.service?.list),
  });

  const optionsFromKeys = useMemo(() => {
    const keys = new Set();
    (config.formFields || []).forEach((f) => {
      if (f.optionsFrom) keys.add(f.optionsFrom);
    });
    (config.columns || []).forEach((col) => {
      if (col.optionsFrom) keys.add(col.optionsFrom);
      const inferred = inferOptionsFromKey(col.accessor || col.key);
      if (inferred) keys.add(inferred);
    });
    return [...keys];
  }, [config.formFields, config.columns]);

  const { data: dynamicOptions = {} } = useQuery({
    queryKey: ['entity-options', ...optionsFromKeys],
    queryFn: async () => {
      const out = {};
      await Promise.all(optionsFromKeys.map(async (key) => {
        const loader = OPTION_LOADERS[key];
        if (loader) out[key] = await loader();
      }));
      return out;
    },
    enabled: optionsFromKeys.length > 0,
    staleTime: 60_000,
  });

  const openCreate = () => {
    setEditing(null);
    setForm({ ...config.emptyForm });
    setShowModal(true);
  };

  const openEdit = (row) => {
    setEditing(row);
    const next = { ...config.emptyForm };
    const aliases = config.fieldAliases || {};
    Object.keys(next).forEach((key) => {
      const sourceKey = aliases[key] || key;
      if (row[sourceKey] !== undefined && row[sourceKey] !== null) next[key] = row[sourceKey];
      else if (row[key] !== undefined && row[key] !== null) next[key] = row[key];
    });
    setForm(next);
    setShowModal(true);
  };

  const handleRowAction = async (row, actionDef) => {
    const actionName = actionDef.action;
    const serviceAction = config.service?.[actionName];
    if (!serviceAction) return;

    if (!actionDef.skipConfirm) {
      const label = row.title || row.subject || actionDef.label;
      const confirmResult = await alert.confirm(
        actionDef.confirm || {
          title: `${actionDef.label}?`,
          text: actionDef.confirmText?.(row)
            || `Continue with "${label}"?`,
          confirmText: actionDef.confirmTextButton || `Yes, ${actionDef.label.toLowerCase()}`,
          cancelText: 'Cancel',
          icon: 'question',
        },
      );
      if (!confirmResult.isConfirmed) return;
    }

    setActionLoadingId(`${row.id}-${actionDef.key}`);
    try {
      const result = await serviceAction(row.id, actionDef.payload?.(row));
      const warnings = result?.warnings || result?.data?.warnings;
      if (warnings?.length) {
        notify.warning(warnings.join(' '));
      } else {
        notify.success(result?.message || `${actionDef.label} completed.`);
      }
      await queryClient.invalidateQueries({ queryKey: config.queryKey });
    } catch (err) {
      notify.error(extractApiError(err, `Unable to ${actionDef.label.toLowerCase()}.`));
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleDelete = async (row) => {
    if (!config.service?.delete) return;
    const label = row.title || row.subject || row.recipient_email || row.recipient_phone || 'this record';
    const result = await alert.delete(`"${label}"`);
    if (!result.isConfirmed) return;

    setDeletingId(row.id);
    try {
      await config.service.delete(row.id);
      notify.success('Record deleted.');
      await queryClient.invalidateQueries({ queryKey: config.queryKey });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to delete record.'));
    } finally {
      setDeletingId(null);
    }
  };

  const handleDeleteAll = async () => {
    if (!config.service?.deleteAll) return;
    const result = await alert.confirm({
      title: `Delete all ${title.toLowerCase()}?`,
      text: `This will permanently remove all ${records.length} record(s). This cannot be undone.`,
      confirmText: 'Yes, delete all',
      cancelText: 'Cancel',
      icon: 'warning',
      danger: true,
    });
    if (!result.isConfirmed) return;

    setBulkDeleting(true);
    try {
      const result = await config.service.deleteAll();
      notify.success(result?.message || `All ${title.toLowerCase()} deleted.`);
      await queryClient.invalidateQueries({ queryKey: config.queryKey });
    } catch (err) {
      notify.error(extractApiError(err, `Unable to delete all ${title.toLowerCase()}.`));
    } finally {
      setBulkDeleting(false);
    }
  };

  const columns = [
    ...config.columns
      .filter((col) => col.key !== 'id' && col.accessor !== 'id')
      .map((col) => ({
        ...col,
        render: col.render || ((row) => formatCell(col, row, dynamicOptions)),
      })),
    ...(canManage ? [{
      key: 'actions',
      label: '',
      truncate: false,
      render: (row) => (
        <div className="apex-table-row-actions">
          {(config.rowActions || [])
            .filter((actionDef) => !actionDef.show || actionDef.show(row))
            .map((actionDef) => (
              <button
                key={actionDef.key}
                type="button"
                className={`btn btn-sm ${actionDef.variant === 'primary' ? 'btn-primary' : 'btn-outline-primary'}`}
                disabled={actionLoadingId === `${row.id}-${actionDef.key}`}
                onClick={(e) => { e.stopPropagation(); handleRowAction(row, actionDef); }}
                title={actionDef.label}
              >
                {actionLoadingId === `${row.id}-${actionDef.key}` ? '…' : <FiSend size={14} />}
              </button>
            ))}
          <button
            type="button"
            className="btn btn-sm btn-outline-primary"
            onClick={(e) => { e.stopPropagation(); openEdit(row); }}
            title="Edit"
          >
            <FiEdit2 size={14} />
          </button>
          {config.deletable !== false && config.service?.delete && (
            <button
              type="button"
              className="btn btn-sm btn-outline-danger"
              disabled={deletingId === row.id}
              onClick={(e) => { e.stopPropagation(); handleDelete(row); }}
              title="Delete"
            >
              {deletingId === row.id ? '…' : <FiTrash2 size={14} />}
            </button>
          )}
        </div>
      ),
    }] : []),
  ];

  const handleSave = async () => {
    for (const field of config.formFields || []) {
      const isEmailField = field.type === 'email' || (field.name || '').includes('email');
      if (!isEmailField) continue;
      const err = validateDeliverableEmail(form[field.name], { required: Boolean(field.required) });
      if (err) {
        notify.error(err);
        return;
      }
    }

    setSaving(true);
    try {
      let payload = { ...form };
      if (payload.day_of_week !== undefined && payload.day_of_week !== '') {
        payload.day_of_week = Number(payload.day_of_week);
      }
      if (config.mapCreate && !editing) {
        payload = config.mapCreate(payload);
      }
      if (payload.paper === '') delete payload.paper;
      if (editing) {
        await config.service.update(editing.id, payload);
        notify.success(`${title} updated.`);
      } else {
        await config.service.create(payload);
        notify.success(`${title} created.`);
      }
      await queryClient.invalidateQueries({ queryKey: config.queryKey });
      optionsFromKeys.forEach((k) => queryClient.invalidateQueries({ queryKey: ['entity-options', k] }));
      setShowModal(false);
    } catch (err) {
      notify.error(extractApiError(err, `Unable to save ${title.toLowerCase()}.`));
    } finally {
      setSaving(false);
    }
  };

  const resolveFieldOptions = (field) => {
    let options = field.optionsFrom
      ? (dynamicOptions[field.optionsFrom] || [])
      : (field.options || []);
    if (field.filterByField) {
      const parentVal = form[field.filterByField];
      options = options.filter((o) => !parentVal || o.subjectId === parentVal || o.parentId === parentVal);
    }
    return options;
  };

  const updateFormField = (field, rawValue) => {
    const next = { ...form, [field.name]: rawValue };
    (field.clears || []).forEach((key) => { next[key] = config.emptyForm?.[key] ?? ''; });
    setForm(next);
  };

  const fieldIsVisible = (field) => {
    if (typeof field.showWhen === 'function') return field.showWhen(form, dynamicOptions);
    return true;
  };

  const renderField = (field) => {
    if (field.type === 'hidden') return null;
    const value = form[field.name] ?? '';
    const options = resolveFieldOptions(field);

    if (field.type === 'select') {
      return (
        <select
          className="form-select"
          value={value}
          onChange={(e) => updateFormField(field, e.target.value)}
        >
          <option value="">{field.placeholder || 'Select…'}</option>
          {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      );
    }
    if (field.type === 'textarea') {
      return (
        <textarea
          className="form-control"
          rows={3}
          value={value}
          onChange={(e) => setForm({ ...form, [field.name]: e.target.value })}
        />
      );
    }
    if (field.type === 'checkbox') {
      return (
        <div className="form-check form-switch mt-1">
          <input
            type="checkbox"
            className="form-check-input"
            checked={Boolean(value)}
            onChange={(e) => setForm({ ...form, [field.name]: e.target.checked })}
            id={`field-${field.name}`}
          />
          <label className="form-check-label small" htmlFor={`field-${field.name}`}>
            {field.checkboxLabel || field.label}
          </label>
        </div>
      );
    }
    if (field.type === 'multiselect') {
      const selected = Array.isArray(value) ? value : [];
      return (
        <div className="d-flex flex-wrap gap-2">
          {options.map((o) => (
            <label key={o.value} className="form-check form-check-inline mb-0">
              <input
                type="checkbox"
                className="form-check-input"
                checked={selected.includes(o.value)}
                onChange={(e) => {
                  const next = e.target.checked
                    ? [...selected, o.value]
                    : selected.filter((v) => v !== o.value);
                  setForm({ ...form, [field.name]: next });
                }}
              />
              <span className="form-check-label small">{o.label}</span>
            </label>
          ))}
        </div>
      );
    }
    return (
      <input
        type={field.type || 'text'}
        className="form-control"
        placeholder={field.placeholder}
        value={value}
        onChange={(e) => setForm({ ...form, [field.name]: e.target.value })}
      />
    );
  };

  return (
    <div>
      {config.backLink && (
        <div className="mb-3">
          <Link to={config.backLink.to} className="small text-decoration-none text-muted">
            <FiArrowLeft className="me-1" /> {config.backLink.label}
          </Link>
        </div>
      )}

      <PageHeader
        title={title}
        subtitle={config.subtitle}
        actions={canManage && config.creatable !== false && (
          <div className="d-flex gap-2">
            {config.allowBulkDelete && config.service?.deleteAll && records.length > 0 && (
              <button
                type="button"
                className="btn btn-outline-danger btn-sm d-inline-flex align-items-center gap-1"
                onClick={handleDeleteAll}
                disabled={bulkDeleting}
              >
                <FiTrash2 size={14} /> {bulkDeleting ? 'Deleting…' : (config.bulkDeleteLabel || 'Delete All')}
              </button>
            )}
            <button type="button" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1" onClick={openCreate}>
              <FiPlus size={16} /> {config.createLabel || 'Add'}
            </button>
          </div>
        )}
      />

      {isError ? (
        <div className="alert alert-danger">Unable to load {title.toLowerCase()}. Check your connection and try again.</div>
      ) : (
        <DataTable
            columns={columns}
            data={records}
            loading={isLoading}
            onRowClick={canManage ? openEdit : undefined}
            emptyState={(
              <ModuleEmptyState
                title={`No ${title.toLowerCase()} yet`}
                message={`Create your first ${title.toLowerCase()} record — data is saved to your school database.`}
                actionLabel={canManage ? config.createLabel : undefined}
                onAction={canManage ? openCreate : undefined}
              />
            )}
          />
      )}

      <Modal
        show={showModal}
        onHide={() => setShowModal(false)}
        title={editing ? `Edit ${title}` : config.createLabel}
        size="lg"
        footer={(
          <>
            <button type="button" className="btn btn-outline-secondary" onClick={() => setShowModal(false)}>Cancel</button>
            <button type="button" className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </button>
          </>
        )}
      >
        <div className="row g-3">
          {editing?.id && (
            <div className="col-12">
              <label className="form-label small text-muted mb-1">Record ID</label>
              <input className="form-control form-control-sm font-monospace" readOnly value={editing.id} />
              <div className="form-text">Internal identifier — only visible when editing this record.</div>
            </div>
          )}
          {(config.formFields || []).map((field) => (
            field.type === 'hidden' || !fieldIsVisible(field) ? null : (
              <div key={field.name} className="col-md-6">
                {field.type !== 'checkbox' && (
                  <label className="form-label small fw-medium">
                    {field.label}
                    {field.required && <span className="text-danger ms-1">*</span>}
                  </label>
                )}
                {renderField(field)}
                {field.helpText && <div className="form-text">{field.helpText}</div>}
              </div>
            )
          ))}
        </div>
      </Modal>
    </div>
  );
}

export default EntityListPage;