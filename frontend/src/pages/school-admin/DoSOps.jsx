import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiDownload, FiRefreshCw } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { dosOpsService, termsService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { alert, extractApiError, notify } from '../../utils/notify';
import { ApexLoader } from '../../components/ApexLoader';

export function DoSOps() {
  const queryClient = useQueryClient();
  const { canReadFeature, canWriteFeature } = usePermissions();
  const canView = canReadFeature('dos_workspace');
  const canWrite = canWriteFeature('dos_workspace');
  const [term, setTerm] = useState('');
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState('completeness');

  const { data: terms = [] } = useQuery({
    queryKey: ['terms', 'dos-ops'],
    queryFn: () => termsService.list({ page_size: 50 }),
    enabled: canView,
  });

  const { data: completeness, isLoading: loadC } = useQuery({
    queryKey: ['dos-completeness', term],
    queryFn: () => dosOpsService.completeness({ term: term || undefined }),
    enabled: canView && tab === 'completeness',
  });

  const { data: performance, isLoading: loadP } = useQuery({
    queryKey: ['dos-performance', term],
    queryFn: () => dosOpsService.performance({ term: term || undefined }),
    enabled: canView && tab === 'performance',
  });

  const { data: load, isLoading: loadT } = useQuery({
    queryKey: ['dos-teacher-load'],
    queryFn: () => dosOpsService.teacherLoad(),
    enabled: canView && tab === 'load',
  });

  const { data: reportStatus, isLoading: loadR } = useQuery({
    queryKey: ['dos-report-status', term],
    queryFn: () => dosOpsService.reportStatus({ term: term || undefined }),
    enabled: canView && tab === 'reports',
  });

  const termOptions = useMemo(() => (terms || []).map((t) => ({
    id: t.id,
    label: t.name + (t.is_current ? ' (current)' : ''),
  })), [terms]);

  if (!canView) {
    return <ModuleEmptyState title="DoS Analytics" message="You do not have access to the Director of Studies workspace." />;
  }

  const downloadUneb = async () => {
    setBusy(true);
    try {
      const blob = await dosOpsService.unebCsv({ exam_year: new Date().getFullYear() });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `uneb-candidates-${new Date().getFullYear()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      notify.success('UNEB candidate list downloaded.');
    } catch (err) {
      notify.error(extractApiError(err, 'Export failed.'));
    } finally {
      setBusy(false);
    }
  };

  const seedUganda = async () => {
    const confirmed = await alert.confirm({
      title: 'Apply Uganda presets?',
      text: 'Adds assessment schemes, subject combinations, and D1–F9 grading presets. Existing named presets are kept.',
      confirmText: 'Yes, apply',
      cancelText: 'Cancel',
      icon: 'question',
    });
    if (!confirmed.isConfirmed) return;
    setBusy(true);
    try {
      const data = await dosOpsService.seedUganda();
      notify.success(`Uganda presets applied: ${JSON.stringify(data)}`);
      await queryClient.invalidateQueries({ queryKey: ['grading-schemes'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Seed failed.'));
    } finally {
      setBusy(false);
    }
  };

  const tabs = [
    { id: 'completeness', label: 'Marks completeness' },
    { id: 'performance', label: 'Performance' },
    { id: 'reports', label: 'Report cards' },
    { id: 'load', label: 'Teacher load' },
  ];

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/academics/dos" className="btn btn-link btn-sm text-decoration-none ps-0">
          <FiArrowLeft className="me-1" /> DoS workspace
        </Link>
      </div>
      <PageHeader
        title="DoS Analytics & UNEB"
        subtitle="Marks completeness, stream performance, teacher load, report queues, and candidate export"
        actions={(
          <div className="d-flex flex-wrap gap-2">
            <select
              className="form-select form-select-sm"
              style={{ width: 'auto' }}
              value={term}
              onChange={(e) => setTerm(e.target.value)}
            >
              <option value="">Active term</option>
              {termOptions.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
            </select>
            <button type="button" className="btn btn-outline-primary btn-sm" disabled={busy} onClick={downloadUneb}>
              <FiDownload className="me-1" /> UNEB CSV
            </button>
            {canWrite && (
              <button type="button" className="btn btn-outline-secondary btn-sm" disabled={busy} onClick={seedUganda}>
                <FiRefreshCw className="me-1" /> Uganda presets
              </button>
            )}
          </div>
        )}
      />

      <div className="d-flex flex-wrap gap-2 mb-3">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`btn btn-sm ${tab === t.id ? 'btn-primary' : 'btn-outline-secondary'}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'completeness' && (
        <div className="apex-card p-3">
          {loadC ? <ApexLoader size="sm" showDots={false} /> : (
            <>
              <div className="row g-2 mb-3">
                <div className="col-6 col-md-3"><div className="small text-muted">Exams</div><div className="fs-5 fw-bold">{completeness?.summary?.total_exams ?? 0}</div></div>
                <div className="col-6 col-md-3"><div className="small text-muted">Complete</div><div className="fs-5 fw-bold text-success">{completeness?.summary?.complete ?? 0}</div></div>
                <div className="col-6 col-md-3"><div className="small text-muted">Incomplete</div><div className="fs-5 fw-bold text-warning">{completeness?.summary?.incomplete ?? 0}</div></div>
                <div className="col-6 col-md-3"><div className="small text-muted">Pending approval</div><div className="fs-5 fw-bold">{completeness?.summary?.submitted ?? 0}</div></div>
              </div>
              <DataTable
                columns={[
                  { key: 'name', label: 'Exam' },
                  { key: 'subject', label: 'Subject' },
                  { key: 'class_name', label: 'Class' },
                  { key: 'marks_status', label: 'Status' },
                  { key: 'entered', label: 'Entered' },
                  { key: 'expected', label: 'Expected' },
                  { key: 'missing', label: 'Missing' },
                ]}
                data={completeness?.incomplete || completeness?.rows || []}
                searchable
                emptyState={<ModuleEmptyState title="All complete" message="All published exams have full marks entry." />}
              />
            </>
          )}
        </div>
      )}

      {tab === 'performance' && (
        <div className="apex-card p-3">
          {loadP ? <ApexLoader size="sm" showDots={false} /> : (
            <>
              <h6 className="mb-2">Subject means</h6>
              <DataTable
                columns={[
                  { key: 'subject_name', label: 'Subject' },
                  { key: 'mean', label: 'Mean' },
                  { key: 'entries', label: 'Entries' },
                ]}
                data={performance?.subjects || []}
                searchable
                emptyState={<ModuleEmptyState title="No data" message="No approved marks for this term." />}
              />
              <h6 className="mt-4 mb-2">Failure list (score &lt; 50 or has fails)</h6>
              <DataTable
                columns={[
                  { key: 'admission_number', label: 'Adm #' },
                  { key: 'full_name', label: 'Name' },
                  { key: 'class_name', label: 'Class' },
                  { key: 'average', label: 'Average' },
                  { key: 'fail_count', label: 'Fails' },
                ]}
                data={performance?.failure_list || []}
                searchable
                emptyState={<ModuleEmptyState title="No failures" message="No failures flagged." />}
              />
            </>
          )}
        </div>
      )}

      {tab === 'reports' && (
        <div className="apex-card p-3">
          {loadR ? <ApexLoader size="sm" showDots={false} /> : (
            <>
              <div className="row g-2 mb-3">
                <div className="col-6 col-md-3"><div className="small text-muted">Not generated</div><div className="fs-5 fw-bold">{reportStatus?.summary?.not_generated ?? 0}</div></div>
                <div className="col-6 col-md-3"><div className="small text-muted">Partial</div><div className="fs-5 fw-bold">{reportStatus?.summary?.partial ?? 0}</div></div>
                <div className="col-6 col-md-3"><div className="small text-muted">Ready</div><div className="fs-5 fw-bold text-info">{reportStatus?.summary?.ready ?? 0}</div></div>
                <div className="col-6 col-md-3"><div className="small text-muted">Published</div><div className="fs-5 fw-bold text-success">{reportStatus?.summary?.published ?? 0}</div></div>
              </div>
              <DataTable
                columns={[
                  { key: 'class_name', label: 'Class' },
                  { key: 'active_students', label: 'Students' },
                  { key: 'generated', label: 'Generated' },
                  { key: 'published', label: 'Published' },
                  { key: 'status', label: 'Status' },
                ]}
                data={reportStatus?.rows || []}
                searchable
                emptyState={<ModuleEmptyState title="No classes" message="No classes with active students." />}
              />
              <Link to="/school-admin/academics/report-cards" className="btn btn-primary btn-sm mt-3">
                Open report card pipeline
              </Link>
            </>
          )}
        </div>
      )}

      {tab === 'load' && (
        <div className="apex-card p-3">
          {loadT ? <ApexLoader size="sm" showDots={false} /> : (
            <DataTable
              columns={[
                { key: 'teacher_name', label: 'Teacher' },
                { key: 'lessons_per_week', label: 'Lessons/week' },
                { key: 'class_count', label: 'Classes' },
                { key: 'subject_count', label: 'Subjects' },
              ]}
              data={load?.rows || []}
              searchable
              emptyState={<ModuleEmptyState title="No load data" message="No timetable slots or teaching assignments." />}
            />
          )}
        </div>
      )}
    </div>
  );
}

export default DoSOps;
