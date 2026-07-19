import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiLock, FiSave, FiShield } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import { resultsAccessService } from '../../services/moduleService';
import { extractApiError, notify } from '../../utils/notify';
import { usePermissions } from '../../hooks/usePermissions';

export function ResultsAccessPolicyPage() {
  const queryClient = useQueryClient();
  const { isSchoolAdmin, canReadFeature } = usePermissions();
  const canManage = isSchoolAdmin
    || canReadFeature('bursar_workspace')
    || canReadFeature('assistant_bursar_workspace');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['results-access-policy'],
    queryFn: () => resultsAccessService.get(),
    enabled: canManage,
  });

  const [schoolPercent, setSchoolPercent] = useState('100');
  const [schoolActive, setSchoolActive] = useState(true);
  const [schoolNotes, setSchoolNotes] = useState('');
  const [classEdits, setClassEdits] = useState({});

  useEffect(() => {
    if (!data?.school) return;
    setSchoolPercent(data.school.default_cleared_percent ?? '100');
    setSchoolActive(data.school.is_active !== false);
    setSchoolNotes(data.school.notes || '');
  }, [data]);

  const saveSchool = useMutation({
    mutationFn: () => resultsAccessService.updateSchool({
      default_cleared_percent: schoolPercent,
      is_active: schoolActive,
      notes: schoolNotes,
    }),
    onSuccess: async () => {
      notify.success('School-wide results fee gate updated.');
      await queryClient.invalidateQueries({ queryKey: ['results-access-policy'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to save policy.')),
  });

  const saveClass = useMutation({
    mutationFn: ({ classId, payload }) => resultsAccessService.updateClass(classId, payload),
    onSuccess: async () => {
      notify.success('Class override saved.');
      await queryClient.invalidateQueries({ queryKey: ['results-access-policy'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to save class override.')),
  });

  const classes = data?.classes || [];

  const columns = [
    { key: 'school_class_name', label: 'Class', accessor: 'school_class_name', sortable: true },
    { key: 'school_class_code', label: 'Code', accessor: 'school_class_code' },
    {
      key: 'school_default_percent',
      label: 'School default',
      render: (row) => `${row.school_default_percent}%`,
    },
    {
      key: 'cleared_percent',
      label: 'Required %',
      render: (row) => {
        const edit = classEdits[row.school_class_id];
        const value = edit?.cleared_percent ?? row.cleared_percent;
        return (
          <input
            type="number"
            min={0}
            max={100}
            step="0.01"
            className="form-control form-control-sm"
            style={{ width: 100 }}
            value={value}
            disabled={!canManage}
            onChange={(e) => setClassEdits((prev) => ({
              ...prev,
              [row.school_class_id]: {
                ...prev[row.school_class_id],
                cleared_percent: e.target.value,
                is_active: prev[row.school_class_id]?.is_active ?? true,
              },
            }))}
          />
        );
      },
    },
    {
      key: 'is_override',
      label: 'Override',
      render: (row) => (row.is_override
        ? <span className="badge text-bg-primary-subtle border text-primary">Custom</span>
        : <span className="text-muted small">Default</span>),
    },
    {
      key: 'actions',
      label: '',
      render: (row) => canManage && (
        <button
          type="button"
          className="btn btn-sm btn-outline-primary"
          disabled={saveClass.isPending}
          onClick={() => {
            const edit = classEdits[row.school_class_id] || {};
            saveClass.mutate({
              classId: row.school_class_id,
              payload: {
                cleared_percent: edit.cleared_percent ?? row.cleared_percent,
                is_active: true,
                notes: '',
              },
            });
          }}
        >
          Save
        </button>
      ),
    },
  ];

  if (!canManage) {
    return (
      <div className="apex-card p-5 text-center">
        <FiShield size={28} className="text-muted mb-2" />
        <h5 className="fw-bold">Bursary access required</h5>
        <p className="text-muted mb-0">Only school admins and bursary staff can configure results fee clearance.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/finance" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Finance
        </Link>
      </div>

      <PageHeader
        title="Results fee gate"
        subtitle="Parents and sponsors only see marks and report cards when fee clearance meets the threshold you set"
      />

      {isError && <div className="alert alert-danger">Unable to load results access policy.</div>}

      <div className="apex-card p-3 p-md-4 mb-4">
        <div className="d-flex align-items-start gap-2 mb-3">
          <FiLock className="text-primary mt-1" />
          <div>
            <h5 className="fw-bold mb-1">School-wide default</h5>
            <p className="small text-muted mb-0">
              Applies to every class unless a class override is active. Example: 100% = full fees cleared;
              75% = parents may view results once three-quarters of billed fees are paid.
            </p>
          </div>
        </div>
        <div className="row g-3 align-items-end">
          <div className="col-md-3">
            <label className="form-label small fw-medium">Required cleared %</label>
            <input
              type="number"
              min={0}
              max={100}
              step="0.01"
              className="form-control"
              value={schoolPercent}
              onChange={(e) => setSchoolPercent(e.target.value)}
            />
          </div>
          <div className="col-md-3">
            <div className="form-check form-switch mt-4">
              <input
                type="checkbox"
                className="form-check-input"
                id="policy-active"
                checked={schoolActive}
                onChange={(e) => setSchoolActive(e.target.checked)}
              />
              <label className="form-check-label" htmlFor="policy-active">Policy active</label>
            </div>
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Notes</label>
            <input
              className="form-control"
              value={schoolNotes}
              onChange={(e) => setSchoolNotes(e.target.value)}
              placeholder="Optional policy note for bursary team"
            />
          </div>
          <div className="col-md-2">
            <button
              type="button"
              className="btn btn-primary w-100 d-inline-flex align-items-center justify-content-center gap-1"
              disabled={saveSchool.isPending || isLoading}
              onClick={() => saveSchool.mutate()}
            >
              <FiSave size={14} /> Save
            </button>
          </div>
        </div>
      </div>

      <div className="apex-card p-3 p-md-4">
        <h5 className="fw-bold mb-3">Per-class overrides</h5>
        <DataTable
          columns={columns}
          data={classes}
          loading={isLoading}
          searchable
          searchPlaceholder="Search class by name or code…"
          searchKeys={['school_class_name', 'school_class_code', 'cleared_percent']}
          emptyState={<p className="text-muted small mb-0">No classes found. Create classes first.</p>}
        />
      </div>
    </div>
  );
}

export default ResultsAccessPolicyPage;
