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
import { alert, extractApiError, notify } from '../../utils/notify';

export function AcademicReportCards() {
  const queryClient = useQueryClient();
  const { canWriteFeature, canReadFeature } = usePermissions();
  const featureView = canReadFeature('report_cards') || canReadFeature('class_report_cards')
    || canReadFeature('result_processing') || canWriteFeature('dos_workspace');

  const [term, setTerm] = useState('');
  const [schoolClass, setSchoolClass] = useState('');
  const [stream, setStream] = useState('');
  /** all | published | draft — only published rows are live report cards */
  const [publishFilter, setPublishFilter] = useState('all');
  const [busy, setBusy] = useState(false);
  const [teacherRemarks, setTeacherRemarks] = useState('');
  const [dosRemarks, setDosRemarks] = useState('');
  const [principalRemarks, setPrincipalRemarks] = useState('');
  const [studentRemarks, setStudentRemarks] = useState({});

  const { data: caps } = useQuery({
    queryKey: ['results-capabilities'],
    queryFn: () => academicReportCardsService.capabilities(),
    staleTime: 60_000,
  });

  const canPrint = Boolean(caps?.can_print_report_cards);
  const canClassRemarks = Boolean(caps?.can_edit_class_teacher_remarks);
  const canDosRemarks = Boolean(caps?.is_dos || caps?.is_school_admin);
  const canPrincipalRemarks = Boolean(caps?.is_school_admin);
  // Generate/print: class teachers & DoS (not subject teachers)
  const canManage = canPrint;
  const canView = featureView || canPrint || canClassRemarks || caps?.can_enter_marks;

  const { data: terms = [] } = useQuery({
    queryKey: ['terms', 'report-cards'],
    queryFn: () => termsService.list({ page_size: 50 }),
    enabled: Boolean(canView),
  });
  const { data: classes = [] } = useQuery({
    queryKey: ['classes', 'report-cards'],
    queryFn: () => classesService.list({ page_size: 200 }),
    enabled: Boolean(canView),
  });

  const { data: latest, isLoading, refetch } = useQuery({
    queryKey: ['report-cards-latest', term, schoolClass, stream, publishFilter],
    queryFn: () => academicReportCardsService.latest({
      term: term || undefined,
      school_class: schoolClass || undefined,
      stream: stream || undefined,
      ...(publishFilter === 'published' ? { published: '1' } : {}),
      ...(publishFilter === 'draft' ? { published: '0' } : {}),
    }),
    enabled: Boolean(canView) && Boolean(term && schoolClass),
  });

  const termOptions = useMemo(() => (terms || []).map((t) => ({
    value: t.id,
    label: t.name,
    meta: t.academic_year_name || (t.is_current ? 'Current' : undefined),
  })), [terms]);

  // Filter classes to headed ones for class teachers; all for DoS/admin
  const classOptions = useMemo(() => {
    let list = classes || [];
    if (caps && !caps.can_read_all_classes) {
      const allowed = new Set([
        ...(caps.headed_class_ids || []),
        ...(caps.taught_class_ids || []),
      ]);
      if (allowed.size) {
        list = list.filter((c) => allowed.has(String(c.id)));
      }
    }
    // Prefer headed classes first when printing
    if (caps?.headed_class_ids?.length && canPrint && !caps.can_read_all_classes) {
      const headed = new Set(caps.headed_class_ids.map(String));
      list = list.filter((c) => headed.has(String(c.id)));
    }
    return list.map((c) => ({
      value: c.id,
      label: `${c.name}${c.code ? ` (${c.code})` : ''}`,
      meta: c.academic_year_name,
    }));
  }, [classes, caps, canPrint]);

  const streamOptions = useMemo(() => {
    const c = (classes || []).find((x) => x.id === schoolClass);
    return (c?.streams || []).map((s) => ({ value: s.id, label: s.name }));
  }, [classes, schoolClass]);

  const rows = latest?.results || [];
  const subjectColumns = latest?.subject_columns || [];

  const generate = async () => {
    if (!term || !schoolClass) {
      notify.error('Select term and class.');
      return;
    }
    if (!canPrint) {
      notify.error('Report card generation is not available for your account.');
      return;
    }
    setBusy(true);
    try {
      const data = await academicReportCardsService.generate({
        term,
        school_class: schoolClass,
        stream: stream || undefined,
        teacher_remarks: canClassRemarks ? teacherRemarks : '',
        dos_remarks: canDosRemarks ? dosRemarks : '',
        principal_remarks: canPrincipalRemarks ? principalRemarks : '',
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
    if (!canPrint) return;
    const confirmed = await alert.confirm({
      title: 'Publish report cards?',
      text: 'Only after publish do these become live report cards. Parents will see them when fee clearance meets your school results access policy. Unpublished rows remain results only.',
      confirmText: 'Yes, publish',
      cancelText: 'Cancel',
      icon: 'question',
    });
    if (!confirmed.isConfirmed) return;
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

  const saveStudentRemarks = async () => {
    if (!term || !schoolClass || !canClassRemarks) return;
    setBusy(true);
    try {
      const data = await academicReportCardsService.saveClassTeacherRemarks({
        term,
        school_class: schoolClass,
        remarks: studentRemarks,
      });
      notify.success(data?.message || 'Class-teacher remarks saved.');
      await refetch();
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to save remarks.'));
    } finally {
      setBusy(false);
    }
  };

  const columns = [
    { key: 'student_name', label: 'Name', accessor: 'student_name', sortable: true },
    { key: 'admission_number', label: 'Adm #', accessor: 'admission_number', sortable: true },
    // Broadsheet-style preview: each subject shows score + grade (blank if missing)
    ...subjectColumns.map((col) => ({
      key: `subj_${col.key}`,
      label: col.code || col.name,
      render: (r) => {
        const cell = r.subject_scores?.[col.key];
        if (cell?.total == null || cell?.total === '') {
          return <span className="text-muted"> </span>;
        }
        return (
          <span
            className="font-monospace small text-nowrap"
            title={[cell.remarks, col.name].filter(Boolean).join(' · ') || undefined}
          >
            {cell.total}
            {cell.grade ? (
              <span className="ms-1 badge text-bg-primary-subtle border text-primary">{cell.grade}</span>
            ) : null}
          </span>
        );
      },
    })),
    {
      key: 'overall_grade',
      label: 'Overall grade',
      render: (r) => (
        r.overall_grade
          ? <span className="badge text-bg-success-subtle border text-success">{r.overall_grade}</span>
          : <span className="text-muted">—</span>
      ),
    },
    { key: 'average_score', label: 'Average', accessor: 'average_score' },
    { key: 'rank', label: 'Class rank', accessor: 'rank' },
    { key: 'stream_rank', label: 'Stream rank', accessor: 'stream_rank' },
    ...(canClassRemarks ? [{
      key: 'teacher_remarks',
      label: 'Class teacher remark',
      render: (r) => (
        <input
          className="form-control form-control-sm"
          style={{ minWidth: 120, maxWidth: 220 }}
          value={studentRemarks[r.student_id] ?? r.teacher_remarks ?? ''}
          onChange={(e) => setStudentRemarks((prev) => ({
            ...prev,
            [r.student_id]: e.target.value,
          }))}
          placeholder="General remark…"
        />
      ),
    }] : []),
    {
      key: 'is_published',
      label: 'Status',
      render: (r) => (r.is_published
        ? <span className="badge text-bg-success-subtle border text-success">Report card</span>
        : <span className="badge text-bg-warning-subtle border text-warning">Results only</span>),
    },
    {
      key: 'actions',
      label: '',
      render: (r) => (
        canPrint ? (
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
        ) : (
          <span className="text-muted small">—</span>
        )
      ),
    },
  ];

  if (!canView) {
    return (
      <div className="apex-card p-5">
        <ModuleEmptyState title="Report cards unavailable" message="Report card features are not available for your account." />
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
        subtitle={
          canPrint
            ? 'Published cards are live report cards (parents & portal). Drafts are internal results only — publish from Results Processing or here.'
            : 'Only published report cards are live for parents. Use Results Processing for the live marks matrix and to publish.'
        }
        actions={(
          <Link to="/school-admin/examinations/results" className="btn btn-outline-secondary btn-sm">
            Results processing
          </Link>
        )}
      />

      <div className="row g-3 g-lg-4 mb-4">
        <div className="col-12 col-lg-4">
          <div className="apex-card apex-card--responsive p-3 p-md-4">
            <h6 className="fw-semibold mb-3">Class &amp; term</h6>
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
            {canClassRemarks && (
              <div className="mb-2">
                <label className="form-label small">Default class-teacher remarks (applied on generate)</label>
                <textarea
                  className="form-control form-control-sm"
                  rows={2}
                  value={teacherRemarks}
                  onChange={(e) => setTeacherRemarks(e.target.value)}
                  placeholder="General remark for the class (optional)"
                />
                <div className="form-text">Per-student remarks can be set after generation in the table.</div>
              </div>
            )}
            {canDosRemarks && (
              <div className="mb-2">
                <label className="form-label small">Academic remarks (optional on generate)</label>
                <textarea className="form-control form-control-sm" rows={2} value={dosRemarks} onChange={(e) => setDosRemarks(e.target.value)} />
              </div>
            )}
            {canPrincipalRemarks && (
              <div className="mb-3">
                <label className="form-label small">Head teacher remarks</label>
                <textarea className="form-control form-control-sm" rows={2} value={principalRemarks} onChange={(e) => setPrincipalRemarks(e.target.value)} />
              </div>
            )}
            {canManage && (
              <div className="d-flex flex-wrap gap-2">
                <button type="button" className="btn btn-primary btn-sm d-inline-flex align-items-center justify-content-center gap-1 flex-grow-1 flex-sm-grow-0" disabled={busy} onClick={generate}>
                  <FiFileText size={14} /> Generate
                </button>
                <button type="button" className="btn btn-success btn-sm d-inline-flex align-items-center justify-content-center gap-1 flex-grow-1 flex-sm-grow-0" disabled={busy || !rows.length} onClick={publish}>
                  <FiSend size={14} /> Publish
                </button>
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm d-inline-flex align-items-center justify-content-center gap-1 flex-grow-1 flex-sm-grow-0"
                  disabled={!term || !schoolClass || busy}
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
            {canClassRemarks && rows.length > 0 && (
              <button
                type="button"
                className="btn btn-outline-primary btn-sm mt-3 w-100"
                disabled={busy}
                onClick={saveStudentRemarks}
              >
                Save per-student class-teacher remarks
              </button>
            )}
          </div>
        </div>
        <div className="col-12 col-lg-8">
          <div className="apex-card apex-card--responsive p-3 p-md-4">
            <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
              <h6 className="fw-semibold mb-0">Latest cards</h6>
              <div className="btn-group btn-group-sm" role="group" aria-label="Publish filter">
                <button
                  type="button"
                  className={`btn btn-outline-secondary${publishFilter === 'all' ? ' active' : ''}`}
                  onClick={() => setPublishFilter('all')}
                >
                  All
                </button>
                <button
                  type="button"
                  className={`btn btn-outline-secondary${publishFilter === 'published' ? ' active' : ''}`}
                  onClick={() => setPublishFilter('published')}
                >
                  Report cards
                </button>
                <button
                  type="button"
                  className={`btn btn-outline-secondary${publishFilter === 'draft' ? ' active' : ''}`}
                  onClick={() => setPublishFilter('draft')}
                >
                  Results only
                </button>
              </div>
            </div>
            <p className="small text-muted mb-3">
              Preview matches printouts: <strong>Name</strong>, each subject as <strong>score + grade</strong>{' '}
              (blank if missing), <strong>overall grade</strong>, and <strong>average</strong>.
              Individual PDFs list Code · Subject · Score · Grade · Remarks, then average and overall grade.
              Subject remarks are per-subject; class teacher / DoS / head remarks are overall only.
            </p>
            <DataTable
              columns={columns}
              data={rows}
              loading={isLoading}
              searchable
              scrollable
              searchPlaceholder="Search student, admission, rank…"
              searchKeys={['admission_number', 'student_name', 'average_score', 'rank']}
              emptyState={(
                <ModuleEmptyState
                  title={publishFilter === 'published' ? 'No published report cards' : 'No cards yet'}
                  message={
                    publishFilter === 'published'
                      ? 'Publish from Results Processing (or Generate + Publish here) so cards appear for parents.'
                      : 'Select term and class, then generate from approved marks on Results Processing or here.'
                  }
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
