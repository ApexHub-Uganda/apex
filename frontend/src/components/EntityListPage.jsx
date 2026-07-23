import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiEdit2, FiPlus, FiSend, FiTrash2 } from 'react-icons/fi';
import PageHeader from './PageHeader';
import DataTable from './DataTable';
import SearchableSelect from './SearchableSelect';
import ModuleEmptyState from './ModuleEmptyState';
import CurrentRecordPanel from './CurrentRecordPanel';
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
  academicYearsService,
  feePaymentsService,
  financialAccountsService,
} from '../services/moduleService';
import { validateDeliverableEmail } from '../utils/emailValidation';
import { COL_WIDTH, formatTableCellValue, inferOptionsFromKey, sanitizeListColumns } from '../utils/tableDisplay';
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
  students: () => studentsService.list({ page_size: 500 }).then((rows) => rows.map((s) => ({
    value: s.id,
    label: `${s.full_name || `${s.first_name || ''} ${s.last_name || ''}`.trim() || s.admission_number}${s.admission_number ? ` — ${s.admission_number}` : ''}`,
    meta: [s.school_class_name || s.class_name, s.stream_name].filter(Boolean).join(' · ') || undefined,
    keywords: [s.admission_number, s.first_name, s.last_name, s.email, s.phone, s.upi_number].filter(Boolean).join(' '),
  }))),
  staff: () => staffService.list({ page_size: 500 }).then((rows) => rows.map((s) => ({
    value: s.id,
    label: s.full_name || `${s.first_name || ''} ${s.last_name || ''}`.trim(),
    meta: [s.staff_number, s.email, s.department_name].filter(Boolean).join(' · ') || undefined,
    keywords: [s.staff_number, s.email, s.phone, s.first_name, s.last_name].filter(Boolean).join(' '),
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
  academic_years: () => academicYearsService.list().then((rows) => rows.map((y) => ({
    value: y.id, label: y.name,
  }))),
  feePayments: () => feePaymentsService.list({ page_size: 500 }).then((rows) => rows.map((p) => ({
    value: p.id,
    label: `${p.student_name || 'Payment'} — ${p.amount_paid} (${p.payment_date || ''})`,
    meta: [p.receipt_number, p.fee_name, p.student_admission].filter(Boolean).join(' · ') || undefined,
    keywords: [p.receipt_number, p.reference, p.mpesa_transaction_id, p.student_admission, p.fee_name].filter(Boolean).join(' '),
  }))),
  financialAccounts: () => financialAccountsService.list().then((rows) => rows.map((a) => ({
    value: a.id,
    label: a.code ? `${a.name} (${a.code})` : a.name,
    meta: a.account_type || undefined,
    keywords: [a.name, a.code, a.account_type].filter(Boolean).join(' '),
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
  const [endingCurrent, setEndingCurrent] = useState(false);

  const listParams = config.listParams || {};

  const { data: listPayload, isLoading, isError } = useQuery({
    queryKey: [...config.queryKey, listParams, config.singleton ? 'meta' : 'plain'],
    queryFn: async () => {
      if (config.singleton && config.service?.listWithMeta) {
        return config.service.listWithMeta({ page_size: 200, ...listParams });
      }
      const records = await config.service.list({ page_size: 200, ...listParams });
      return { records, meta: null };
    },
    enabled: Boolean(config.service?.list),
  });

  const records = listPayload?.records ?? [];
  const listMeta = listPayload?.meta ?? null;
  const creationLocked = Boolean(listMeta?.creation_locked);
  // Academic years, terms, exam periods: non-admins may create (when unlocked) then only read.
  // School admin alone may edit, delete, or change status after creation.
  const isPeriodSingleton = Boolean(
    config.singleton
    && (featureKey === 'academic_years' || featureKey === 'terms' || featureKey === 'examination_sessions'),
  );
  // Prefer API meta when present; always allow school admin
  const canMutatePeriods = Boolean(isSchoolAdmin || listMeta?.can_mutate);
  const canCreate = canManage && config.creatable !== false && !creationLocked;
  const canEditRecords = isPeriodSingleton
    ? canMutatePeriods
    : (canManage || isSchoolAdmin);
  const isReadOnlyViewer = !canEditRecords;
  // Non-admins hide the full table while a period is active (panel is enough).
  // School admins always see the table + panel actions.
  const hideSingletonTable = Boolean(
    isPeriodSingleton
    && creationLocked
    && listMeta?.active_record
    && !canMutatePeriods,
  );
  const scopedEmptyTitle = `No ${title.toLowerCase()} assigned to you`;
  const scopedEmptyMessage = 'You only see records linked to your teaching assignments. Contact the Director of Studies if something is missing.';

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
    const label = row.title || row.subject || row.name || row.recipient_email || row.recipient_phone || 'this record';
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

  const resolveActiveRow = () => {
    const active = listMeta?.active_record;
    if (!active?.id) return null;
    return records.find((r) => String(r.id) === String(active.id)) || active;
  };

  const openEditCurrent = () => {
    const row = resolveActiveRow();
    if (row) openEdit(row);
  };

  const handleEndCurrent = async () => {
    const row = resolveActiveRow();
    if (!row?.id || !config.service?.update) return;
    const singletonType = listMeta?.singleton_type
      || (typeof config.singleton === 'object' ? config.singleton.type : config.singleton);
    const today = new Date().toISOString().slice(0, 10);
    const confirm = await alert.confirm({
      title: singletonType === 'examination_session' ? 'End exam period?' : 'End current period?',
      text: singletonType === 'examination_session'
        ? `Close “${row.name}” so a new exam period can be created. Marks already entered are kept.`
        : `Mark “${row.name}” as ended so a new ${title.toLowerCase().replace(/s$/i, '')} can be created.`,
      confirmText: 'Yes, end it',
      cancelText: 'Cancel',
      icon: 'warning',
    });
    if (!confirm.isConfirmed) return;

    setEndingCurrent(true);
    try {
      const payload = singletonType === 'examination_session'
        ? { status: 'closed', end_date: today }
        : { is_current: false, end_date: today };
      await config.service.update(row.id, payload);
      notify.success(
        singletonType === 'examination_session'
          ? 'Exam period closed.'
          : `${title.replace(/s$/i, '')} ended.`,
      );
      await queryClient.invalidateQueries({ queryKey: config.queryKey });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to end this period.'));
    } finally {
      setEndingCurrent(false);
    }
  };

  const handleDeleteCurrent = async () => {
    const row = resolveActiveRow();
    if (row) await handleDelete(row);
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
    ...sanitizeListColumns(config.columns).map((col) => ({
      ...col,
      render: col.render || ((row) => formatCell(col, row, dynamicOptions)),
    })),
    ...(canEditRecords ? [{
      key: 'actions',
      label: '',
      width: COL_WIDTH.actions,
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
      // Use searchable combobox for large option sets (students, payments, etc.)
      const useSearchable = Boolean(field.searchable)
        || options.length > 8
        || ['students', 'feePayments', 'staff', 'parents'].includes(field.optionsFrom);
      if (useSearchable) {
        return (
          <SearchableSelect
            options={options.map((o) => ({
              value: o.value,
              label: o.label,
              meta: o.meta,
              keywords: o.keywords || [o.label, o.value].filter(Boolean).join(' '),
            }))}
            value={value}
            onChange={(val) => updateFormField(field, val)}
            placeholder={field.placeholder || `Search ${field.label || 'options'}…`}
            emptyLabel="No matches"
          />
        );
      }
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

      {config.singleton && listMeta?.active_record && (
        <CurrentRecordPanel
          title={
            (typeof config.singleton === 'object' ? config.singleton.title : config.singletonTitle)
            || `Current ${title.replace(/s$/i, '')}`
          }
          record={listMeta.active_record}
          lockReason={listMeta.lock_reason}
          creationLocked={creationLocked}
          type={listMeta.singleton_type || (typeof config.singleton === 'object' ? config.singleton.type : config.singleton)}
          canMutate={canEditRecords && isPeriodSingleton}
          onEdit={canEditRecords && isPeriodSingleton ? openEditCurrent : undefined}
          onEnd={canEditRecords && isPeriodSingleton ? handleEndCurrent : undefined}
          onDelete={canEditRecords && isPeriodSingleton && config.deletable !== false ? handleDeleteCurrent : undefined}
          ending={endingCurrent}
          deleting={deletingId === listMeta.active_record.id}
        />
      )}

      <PageHeader
        title={title}
        subtitle={config.subtitle}
        actions={(canCreate || (canEditRecords && config.allowBulkDelete)) && (
          <div className="d-flex gap-2">
            {canEditRecords && config.allowBulkDelete && config.service?.deleteAll && records.length > 0 && (
              <button
                type="button"
                className="btn btn-outline-danger btn-sm d-inline-flex align-items-center gap-1"
                onClick={handleDeleteAll}
                disabled={bulkDeleting}
              >
                <FiTrash2 size={14} /> {bulkDeleting ? 'Deleting…' : (config.bulkDeleteLabel || 'Delete All')}
              </button>
            )}
            {canCreate && (
              <button type="button" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1" onClick={openCreate}>
                <FiPlus size={16} /> {config.createLabel || 'Add'}
              </button>
            )}
          </div>
        )}
      />

      {isError ? (
        <div className="alert alert-danger">Unable to load {title.toLowerCase()}. Check your connection and try again.</div>
      ) : hideSingletonTable ? null : (
        <DataTable
            columns={columns}
            data={records}
            loading={isLoading}
            compact
            searchable
            scrollable={isPeriodSingleton || columns.length >= 8}
            searchPlaceholder={`Search ${title.toLowerCase()} by name, code, student, reference…`}
            searchKeys={config.searchKeys || null}
            onRowClick={canEditRecords ? openEdit : undefined}
            emptyState={(
              <ModuleEmptyState
                title={
                  creationLocked
                    ? `Active ${title.toLowerCase()} in progress`
                    : (isReadOnlyViewer ? scopedEmptyTitle : `No ${title.toLowerCase()} yet`)
                }
                message={
                  creationLocked
                    ? (listMeta?.lock_reason || 'The current period must end before a new record can be created.')
                    : (isReadOnlyViewer
                      ? scopedEmptyMessage
                      : `Create your first ${title.toLowerCase()} record — data is saved to your school database.`)
                }
                actionLabel={canCreate ? config.createLabel : undefined}
                onAction={canCreate ? openCreate : undefined}
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
          <button type="button" className="btn btn-primary ms-auto" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </button>
        )}
      >
        <div className="row g-3 apex-form-grid">
          {editing?.id && (
            <div className="col-12">
              <label className="form-label small text-muted mb-1">Record ID</label>
              <input className="form-control form-control-sm font-monospace" readOnly value={editing.id} />
              <div className="form-text">Internal identifier — only visible when editing this record.</div>
            </div>
          )}
          {(config.formFields || []).map((field) => (
            field.type === 'hidden' || !fieldIsVisible(field) ? null : (
              <div
                key={field.name}
                className={field.type === 'textarea' || field.fullWidth ? 'col-12' : 'col-12 col-md-6'}
              >
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