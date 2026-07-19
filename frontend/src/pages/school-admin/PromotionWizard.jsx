import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiCheck, FiRotateCcw } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import SearchableSelect from '../../components/SearchableSelect';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { promotionService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';
import { ApexLoader } from '../../components/ApexLoader';

export function PromotionWizard() {
  const queryClient = useQueryClient();
  const { canWriteFeature, canReadFeature } = usePermissions();
  const canRun = canWriteFeature('student_promotion') || canWriteFeature('dos_workspace');
  const canView = canReadFeature('student_promotion') || canReadFeature('dos_workspace') || canRun;

  const [sourceClass, setSourceClass] = useState('');
  const [sourceStream, setSourceStream] = useState('');
  const [targetClass, setTargetClass] = useState('');
  const [targetStream, setTargetStream] = useState('');
  const [targetYear, setTargetYear] = useState('');
  const [preview, setPreview] = useState(null);
  const [batchId, setBatchId] = useState('');
  const [busy, setBusy] = useState(false);
  const [rowActions, setRowActions] = useState({});

  const { data: ctx, isLoading } = useQuery({
    queryKey: ['promotion-context'],
    queryFn: () => promotionService.context(),
    enabled: canView,
  });

  const classes = ctx?.classes || [];
  const years = ctx?.academic_years || [];

  const classOptions = useMemo(() => classes.map((c) => ({
    value: c.id,
    label: `${c.name} (${c.code})`,
    meta: `${c.academic_year_name || ''} · ${c.active_students} students`,
    keywords: `${c.name} ${c.code} ${c.academic_year_name || ''}`,
  })), [classes]);

  const sourceStreams = useMemo(() => {
    const c = classes.find((x) => x.id === sourceClass);
    return (c?.streams || []).map((s) => ({ value: s.id, label: s.name }));
  }, [classes, sourceClass]);

  const targetStreams = useMemo(() => {
    const c = classes.find((x) => x.id === targetClass);
    return (c?.streams || []).map((s) => ({ value: s.id, label: s.name }));
  }, [classes, targetClass]);

  const yearOptions = useMemo(() => years.map((y) => ({
    value: y.id,
    label: y.name + (y.is_current ? ' (current)' : ''),
  })), [years]);

  const runPreview = async () => {
    if (!sourceClass) {
      notify.error('Select source class.');
      return;
    }
    setBusy(true);
    try {
      const actions = Object.entries(rowActions).map(([student_id, action]) => ({
        student_id,
        action,
      }));
      const data = await promotionService.preview({
        source_class: sourceClass,
        source_stream: sourceStream || undefined,
        target_class: targetClass || undefined,
        target_stream: targetStream || undefined,
        target_academic_year: targetYear || undefined,
        actions,
      });
      setPreview(data);
      setBatchId(data.batch_id);
      notify.success(`Preview ready: ${data.preview?.count || 0} students.`);
    } catch (err) {
      notify.error(extractApiError(err, 'Preview failed.'));
    } finally {
      setBusy(false);
    }
  };

  const runCommit = async () => {
    if (!batchId) return;
    if (!window.confirm('Commit this promotion? Student class placements will change.')) return;
    setBusy(true);
    try {
      const data = await promotionService.commit(batchId);
      notify.success(`Promotion committed for ${data.applied} student(s).`);
      setPreview((p) => (p ? { ...p, status: data.status } : p));
      await queryClient.invalidateQueries({ queryKey: ['promotion-context'] });
      await queryClient.invalidateQueries({ queryKey: ['students'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Commit failed.'));
    } finally {
      setBusy(false);
    }
  };

  const runUndo = async () => {
    if (!batchId) return;
    if (!window.confirm('Undo this promotion? Only allowed if no new marks exist in the target class.')) return;
    setBusy(true);
    try {
      await promotionService.undo(batchId);
      notify.success('Promotion undone.');
      setPreview(null);
      setBatchId('');
      await queryClient.invalidateQueries({ queryKey: ['students'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Undo failed.'));
    } finally {
      setBusy(false);
    }
  };

  const rows = preview?.rows || [];
  const columns = [
    { key: 'admission_number', label: 'Adm #', accessor: 'admission_number', sortable: true },
    { key: 'full_name', label: 'Student', accessor: 'full_name', sortable: true },
    {
      key: 'from',
      label: 'From',
      render: (r) => `${r.from_class_name || ''}${r.from_stream_name ? ` · ${r.from_stream_name}` : ''}`,
    },
    {
      key: 'action',
      label: 'Action',
      render: (r) => (
        canRun && preview?.status !== 'committed' ? (
          <select
            className="form-select form-select-sm"
            value={rowActions[r.student_id] || r.action}
            onChange={(e) => setRowActions((prev) => ({ ...prev, [r.student_id]: e.target.value }))}
          >
            <option value="promote">Promote</option>
            <option value="hold">Hold / Repeat</option>
            <option value="graduate">Graduate</option>
            <option value="skip">Skip</option>
          </select>
        ) : (
          <span className="text-capitalize">{rowActions[r.student_id] || r.action}</span>
        )
      ),
    },
  ];

  if (!canView) {
    return (
      <div className="apex-card p-5">
        <ModuleEmptyState title="Promotion unavailable" message="Student promotion is not enabled for your role." />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/academics" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Academics
        </Link>
      </div>
      <PageHeader
        title="Student promotion"
        subtitle="Promote, hold back, or graduate learners by class/stream with full audit history"
      />

      {isLoading ? (
        <div className="py-5 text-center"><ApexLoader label="Loading…" /></div>
      ) : (
        <div className="row g-4">
          <div className="col-lg-4">
            <div className="apex-card p-4">
              <h6 className="fw-semibold mb-3">Source</h6>
              <div className="mb-3">
                <label className="form-label small">Source class</label>
                <SearchableSelect options={classOptions} value={sourceClass} onChange={(v) => { setSourceClass(v); setSourceStream(''); setPreview(null); }} placeholder="Search class…" />
              </div>
              {sourceStreams.length > 0 && (
                <div className="mb-3">
                  <label className="form-label small">Source stream (optional)</label>
                  <SearchableSelect options={sourceStreams} value={sourceStream} onChange={setSourceStream} placeholder="All streams" allowClear />
                </div>
              )}
              <h6 className="fw-semibold mb-3 mt-4">Target</h6>
              <div className="mb-3">
                <label className="form-label small">Target academic year</label>
                <SearchableSelect options={yearOptions} value={targetYear} onChange={setTargetYear} placeholder="Usually next year" allowClear />
              </div>
              <div className="mb-3">
                <label className="form-label small">Target class (for promote)</label>
                <SearchableSelect options={classOptions} value={targetClass} onChange={(v) => { setTargetClass(v); setTargetStream(''); }} placeholder="Search target class…" allowClear />
              </div>
              {targetStreams.length > 0 && (
                <div className="mb-3">
                  <label className="form-label small">Target stream</label>
                  <SearchableSelect options={targetStreams} value={targetStream} onChange={setTargetStream} placeholder="Optional" allowClear />
                </div>
              )}
              {canRun && (
                <div className="d-flex flex-wrap gap-2">
                  <button type="button" className="btn btn-outline-primary btn-sm" disabled={busy} onClick={runPreview}>
                    Dry-run preview
                  </button>
                  <button type="button" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1" disabled={busy || !batchId || preview?.status === 'committed'} onClick={runCommit}>
                    <FiCheck size={14} /> Commit
                  </button>
                  <button type="button" className="btn btn-outline-secondary btn-sm d-inline-flex align-items-center gap-1" disabled={busy || preview?.status !== 'committed'} onClick={runUndo}>
                    <FiRotateCcw size={14} /> Undo
                  </button>
                </div>
              )}
              {preview?.preview && (
                <div className="alert alert-info small mt-3 mb-0">
                  Promote {preview.preview.promote} · Hold {preview.preview.hold} · Graduate {preview.preview.graduate} · Skip {preview.preview.skip}
                  {preview.status === 'committed' && <div className="mt-1 fw-semibold text-success">Committed</div>}
                </div>
              )}
            </div>
          </div>
          <div className="col-lg-8">
            <div className="apex-card p-4">
              <h6 className="fw-semibold mb-3">Learners in batch</h6>
              <DataTable
                columns={columns}
                data={rows}
                searchable
                searchPlaceholder="Search student or admission number…"
                searchKeys={['admission_number', 'full_name', 'action', 'from_class_name']}
                emptyState={<ModuleEmptyState title="No preview yet" message="Select a source class and run dry-run preview." />}
              />
              {Object.keys(rowActions).length > 0 && preview?.status !== 'committed' && (
                <button type="button" className="btn btn-link btn-sm px-0 mt-2" onClick={runPreview}>
                  Re-preview with per-student actions
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default PromotionWizard;
