import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiDownload, FiFileText, FiSend } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import SearchableSelect from '../../components/SearchableSelect';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import {
  academicReportCardsService,
  classesService,
  termsService,
} from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';

export function AcademicReportCards() {
  const queryClient = useQueryClient();
  const { canWriteFeature, canReadFeature } = usePermissions();
  const canManage = canWriteFeature('report_cards') || canWriteFeature('class_report_cards')
    || canWriteFeature('result_processing') || canWriteFeature('dos_workspace');
  const canView = canReadFeature('report_cards') || canReadFeature('class_report_cards')
    || canReadFeature('result_processing') || canManage;

  const [term, setTerm] = useState('');
  const [schoolClass, setSchoolClass] = useState('');
  const [stream, setStream] = useState('');
  const [busy, setBusy] = useState(false);
  const [teacherRemarks, setTeacherRemarks] = useState('');
  const [dosRemarks, setDosRemarks] = useState('');
  const [principalRemarks, setPrincipalRemarks] = useState('');

  const { data: terms = [] } = useQuery({
    queryKey: ['terms', 'report-cards'],
    queryFn: () => termsService.list({ page_size: 50 }),
    enabled: canView,
  });
  const { data: classes = [] } = useQuery({
    queryKey: ['classes', 'report-cards'],
    queryFn: () => classesService.list({ page_size: 200 }),
    enabled: canView,
  });

  const { data: latest, isLoading, refetch } = useQuery({
    queryKey: ['report-cards-latest', term, schoolClass, stream],
    queryFn: () => academicReportCardsService.latest({
      term: term || undefined,
      school_class: schoolClass || undefined,
      stream: stream || undefined,
    }),
    enabled: canView && Boolean(term && schoolClass),
  });

  const termOptions = useMemo(() => (terms || []).map((t) => ({
    value: t.id,
    label: t.name,
    meta: t.academic_year_name || (t.is_current ? 'Current' : undefined),
  })), [terms]);

  const classOptions = useMemo(() => (classes || []).map((c) => ({
    value: c.id,
    label: `${c.name}${c.code ? ` (${c.code})` : ''}`,
    meta: c.academic_year_name,
  })), [classes]);

  const streamOptions = useMemo(() => {
    const c = (classes || []).find((x) => x.id === schoolClass);
    return (c?.streams || []).map((s) => ({ value: s.id, label: s.name }));
  }, [classes, schoolClass]);

  const rows = latest?.results || [];

  const generate = async () => {
    if (!term || !schoolClass) {
      notify.error('Select term and class.');
      return;
    }
    setBusy(true);
    try {
      const data = await academicReportCardsService.generate({
        term,
        school_class: schoolClass,
        stream: stream || undefined,
        teacher_remarks: teacherRemarks,
        dos_remarks: dosRemarks,
        principal_remarks: principalRemarks,
      });
      notify.success(`Generated ${data.count} report card(s).`);
      await refetch();
      await queryClient.invalidateQueries({ queryKey: ['finance-workspace'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Generation failed.'));
    } finally {
      setBusy(false);
    }
  };

  const publish = async () => {
    if (!term || !schoolClass) return;
    if (!window.confirm('Publish these report cards to the parent portal (fee gate still applies)?')) return;
    setBusy(true);
    try {
      const data = await academicReportCardsService.publish({
        term,
        school_class: schoolClass,
        stream: stream || undefined,
      });
      notify.success(`Published ${data.published} report card(s).`);
      await refetch();
    } catch (err) {
      notify.error(extractApiError(err, 'Publish failed.'));
    } finally {
      setBusy(false);
    }
  };

  const columns = [
    { key: 'admission_number', label: 'Adm #', accessor: 'admission_number', sortable: true },
    { key: 'student_name', label: 'Student', accessor: 'student_name', sortable: true },
    { key: 'average_score', label: 'Average', accessor: 'average_score' },
    { key: 'rank', label: 'Class rank', accessor: 'rank' },
    { key: 'stream_rank', label: 'Stream rank', accessor: 'stream_rank' },
    {
      key: 'is_published',
      label: 'Status',
      render: (r) => (r.is_published
        ? <span className="badge text-bg-success-subtle border text-success">Published</span>
        : <span className="badge text-bg-warning-subtle border text-warning">Draft</span>),
    },
    {
      key: 'actions',
      label: '',
      render: (r) => (
        <button
          type="button"
          className="btn btn-link btn-sm p-0"
          onClick={async () => {
            try {
              await academicReportCardsService.pdf(r.id);
              notify.success('PDF downloaded.');
            } catch (err) {
              notify.error(extractApiError(err, 'PDF failed.'));
            }
          }}
        >
          PDF
        </button>
      ),
    },
  ];

  if (!canView) {
    return (
      <div className="apex-card p-5">
        <ModuleEmptyState title="Report cards unavailable" message="Report card features are not enabled for your role." />
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
        title="Report cards & broadsheets"
        subtitle="Generate term reports from approved marks, rank by stream/class, publish to parents (fee-gated)"
      />

      <div className="row g-4 mb-4">
        <div className="col-lg-4">
          <div className="apex-card p-4">
            <h6 className="fw-semibold mb-3">Generate for class</h6>
            <div className="mb-3">
              <label className="form-label small">Term</label>
              <SearchableSelect options={termOptions} value={term} onChange={setTerm} placeholder="Select term…" />
            </div>
            <div className="mb-3">
              <label className="form-label small">Class</label>
              <SearchableSelect options={classOptions} value={schoolClass} onChange={(v) => { setSchoolClass(v); setStream(''); }} placeholder="Select class…" />
            </div>
            {streamOptions.length > 0 && (
              <div className="mb-3">
                <label className="form-label small">Stream (optional)</label>
                <SearchableSelect options={streamOptions} value={stream} onChange={setStream} placeholder="Whole class" allowClear />
              </div>
            )}
            <div className="mb-2">
              <label className="form-label small">Class teacher remarks</label>
              <textarea className="form-control form-control-sm" rows={2} value={teacherRemarks} onChange={(e) => setTeacherRemarks(e.target.value)} />
            </div>
            <div className="mb-2">
              <label className="form-label small">DoS remarks</label>
              <textarea className="form-control form-control-sm" rows={2} value={dosRemarks} onChange={(e) => setDosRemarks(e.target.value)} />
            </div>
            <div className="mb-3">
              <label className="form-label small">Head teacher remarks</label>
              <textarea className="form-control form-control-sm" rows={2} value={principalRemarks} onChange={(e) => setPrincipalRemarks(e.target.value)} />
            </div>
            {canManage && (
              <div className="d-flex flex-wrap gap-2">
                <button type="button" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1" disabled={busy} onClick={generate}>
                  <FiFileText size={14} /> Generate
                </button>
                <button type="button" className="btn btn-success btn-sm d-inline-flex align-items-center gap-1" disabled={busy || !rows.length} onClick={publish}>
                  <FiSend size={14} /> Publish
                </button>
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm d-inline-flex align-items-center gap-1"
                  disabled={!term || !schoolClass}
                  onClick={async () => {
                    try {
                      await academicReportCardsService.broadsheet({
                        term,
                        school_class: schoolClass,
                        stream: stream || undefined,
                      });
                      notify.success('Broadsheet downloaded.');
                    } catch (err) {
                      notify.error(extractApiError(err, 'Broadsheet failed — generate report cards first.'));
                    }
                  }}
                >
                  <FiDownload size={14} /> Broadsheet PDF
                </button>
              </div>
            )}
          </div>
        </div>
        <div className="col-lg-8">
          <div className="apex-card p-4">
            <h6 className="fw-semibold mb-3">Latest report cards</h6>
            <DataTable
              columns={columns}
              data={rows}
              loading={isLoading}
              searchable
              searchPlaceholder="Search student, admission, rank…"
              searchKeys={['admission_number', 'student_name', 'average_score', 'rank']}
              emptyState={(
                <ModuleEmptyState
                  title="No report cards yet"
                  message="Select term and class, then generate from approved marks."
                />
              )}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default AcademicReportCards;
