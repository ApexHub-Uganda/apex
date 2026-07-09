import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft, FiDownload } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { hostelReportsService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';

const REPORT_TYPES = [
  { value: 'occupancy', label: 'Occupancy' },
  { value: 'maintenance', label: 'Maintenance' },
  { value: 'visitors', label: 'Visitors' },
  { value: 'fees', label: 'Fees' },
];

const COLUMNS_BY_TYPE = {
  occupancy: [
    { key: 'hostel_name', label: 'Hostel', accessor: 'hostel_name' },
    { key: 'rooms', label: 'Rooms', accessor: 'rooms' },
    { key: 'capacity', label: 'Capacity', accessor: 'capacity' },
    { key: 'occupied', label: 'Occupied', accessor: 'occupied' },
    { key: 'occupancy_rate', label: 'Rate %', accessor: 'occupancy_rate' },
  ],
  maintenance: [
    { key: 'reported_at', label: 'Reported', accessor: 'reported_at' },
    { key: 'hostel', label: 'Hostel', accessor: 'hostel' },
    { key: 'title', label: 'Title', accessor: 'title' },
    { key: 'priority', label: 'Priority', accessor: 'priority' },
    { key: 'status', label: 'Status', accessor: 'status' },
  ],
  visitors: [
    { key: 'check_in_time', label: 'Check-in', accessor: 'check_in_time' },
    { key: 'hostel', label: 'Hostel', accessor: 'hostel' },
    { key: 'visitor_name', label: 'Visitor', accessor: 'visitor_name' },
    { key: 'student', label: 'Student', accessor: 'student' },
    { key: 'status', label: 'Status', accessor: 'status' },
  ],
  fees: [
    { key: 'due_date', label: 'Due', accessor: 'due_date' },
    { key: 'hostel', label: 'Hostel', accessor: 'hostel' },
    { key: 'student', label: 'Student', accessor: 'student' },
    { key: 'amount', label: 'Amount', accessor: 'amount' },
    { key: 'status', label: 'Status', accessor: 'status' },
  ],
};

export function HostelReports() {
  const { canReadFeature } = usePermissions();
  const canExport = canReadFeature('hostel_reports');
  const [reportType, setReportType] = useState('occupancy');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['hostel-reports', reportType, startDate, endDate],
    queryFn: () => hostelReportsService.get({
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
    hostelReportsService.downloadCsv({
      type: reportType,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    });
  };

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/hostel" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Hostels
        </Link>
      </div>

      <PageHeader
        title="Hostel Reports"
        subtitle="Occupancy, maintenance, and fee reports"
        actions={canExport && (
          <button type="button" className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1" onClick={handleExport}>
            <FiDownload size={14} /> Export CSV
          </button>
        )}
      />

      {isError && <div className="alert alert-danger">Unable to load hostel reports.</div>}

      <div className="apex-card p-3 p-md-4">
        <div className="d-flex flex-wrap gap-2 mb-3">
          <select className="form-select form-select-sm" style={{ width: 200 }} value={reportType} onChange={(e) => setReportType(e.target.value)}>
            {REPORT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
          {reportType !== 'occupancy' && (
            <>
              <input type="date" className="form-control form-control-sm" style={{ width: 160 }} value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              <input type="date" className="form-control form-control-sm" style={{ width: 160 }} value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </>
          )}
        </div>

        {reportType === 'occupancy' && Object.keys(summary).length > 0 && (
          <div className="small text-muted mb-3">
            School-wide: {summary.hostels} hostels · {summary.total_occupied}/{summary.total_capacity} beds occupied ({summary.occupancy_rate}%)
          </div>
        )}

        {reportType !== 'occupancy' && Object.keys(totals).length > 0 && (
          <div className="small text-muted mb-3">
            Totals: {Object.entries(totals).map(([k, v]) => `${k}: ${v}`).join(' · ')}
          </div>
        )}

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
      </div>
    </div>
  );
}

export default HostelReports;