import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft, FiDownload } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { hrReportsService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';

const REPORT_TYPES = [
  { value: 'summary', label: 'Summary' },
  { value: 'leaves', label: 'Leave Requests' },
  { value: 'reviews', label: 'Performance Reviews' },
  { value: 'contracts', label: 'Staff Contracts' },
  { value: 'discipline', label: 'Discipline Cases' },
];

const COLUMNS_BY_TYPE = {
  leaves: [
    { key: 'staff', label: 'Staff', accessor: 'staff' },
    { key: 'leave_type', label: 'Type', accessor: 'leave_type' },
    { key: 'start_date', label: 'From', accessor: 'start_date' },
    { key: 'end_date', label: 'To', accessor: 'end_date' },
    { key: 'days', label: 'Days', accessor: 'days' },
    { key: 'status', label: 'Status', accessor: 'status' },
  ],
  reviews: [
    { key: 'staff', label: 'Staff', accessor: 'staff' },
    { key: 'period_start', label: 'From', accessor: 'period_start' },
    { key: 'period_end', label: 'To', accessor: 'period_end' },
    { key: 'overall_rating', label: 'Rating', accessor: 'overall_rating' },
    { key: 'status', label: 'Status', accessor: 'status' },
  ],
  contracts: [
    { key: 'staff', label: 'Staff', accessor: 'staff' },
    { key: 'position', label: 'Position', accessor: 'position' },
    { key: 'contract_type', label: 'Type', accessor: 'contract_type' },
    { key: 'start_date', label: 'Start', accessor: 'start_date' },
    { key: 'status', label: 'Status', accessor: 'status' },
  ],
  discipline: [
    { key: 'staff', label: 'Staff', accessor: 'staff' },
    { key: 'incident_date', label: 'Date', accessor: 'incident_date' },
    { key: 'severity', label: 'Severity', accessor: 'severity' },
    { key: 'status', label: 'Status', accessor: 'status' },
  ],
};

export function HRReports() {
  const { canReadFeature } = usePermissions();
  const canExport = canReadFeature('hr_reports');
  const [reportType, setReportType] = useState('leaves');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['hr-reports', reportType, startDate, endDate],
    queryFn: () => hrReportsService.get({
      type: reportType,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    }),
    enabled: canExport,
  });

  const rows = data?.rows || [];
  const totals = data?.totals || {};
  const summary = data?.summary || {};

  const handleExport = () => {
    if (reportType === 'summary') return;
    hrReportsService.downloadCsv({
      type: reportType,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    });
  };

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/hr" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Human Resources
        </Link>
      </div>

      <PageHeader
        title="HR Reports"
        subtitle="Generate and export human resources reports"
        actions={canExport && reportType !== 'summary' && (
          <button type="button" className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1" onClick={handleExport}>
            <FiDownload size={14} /> Export CSV
          </button>
        )}
      />

      {isError && <div className="alert alert-danger">Unable to load HR reports.</div>}

      <div className="apex-card p-3 p-md-4">
        <div className="d-flex flex-wrap gap-2 mb-3">
          <select className="form-select form-select-sm" style={{ width: 200 }} value={reportType} onChange={(e) => setReportType(e.target.value)}>
            {REPORT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
          {reportType !== 'summary' && (
            <>
              <input type="date" className="form-control form-control-sm" style={{ width: 160 }} value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              <input type="date" className="form-control form-control-sm" style={{ width: 160 }} value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </>
          )}
        </div>

        {reportType === 'summary' && Object.keys(summary).length > 0 && (
          <div className="row g-3 mb-3">
            {Object.entries(summary).map(([k, v]) => (
              <div key={k} className="col-6 col-md-3">
                <div className="apex-card p-3">
                  <div className="text-muted small text-capitalize">{k.replace(/_/g, ' ')}</div>
                  <div className="fs-5 fw-bold">{v}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {reportType !== 'summary' && Object.keys(totals).length > 0 && (
          <div className="small text-muted mb-3">
            Totals: {Object.entries(totals).map(([k, v]) => `${k}: ${v}`).join(' · ')}
          </div>
        )}

        {reportType !== 'summary' && (
          <DataTable
            columns={COLUMNS_BY_TYPE[reportType] || []}
            data={rows}
            loading={isLoading}
            emptyState={(
              <ModuleEmptyState
                title="No report data"
                message="Adjust the report type or date range to see results."
              />
            )}
          />
        )}
      </div>
    </div>
  );
}

export default HRReports;