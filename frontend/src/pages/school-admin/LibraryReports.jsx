import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft, FiDownload } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { libraryReportsService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';

const REPORT_TYPES = [
  { value: 'circulation', label: 'Circulation' },
  { value: 'overdue', label: 'Overdue Loans' },
  { value: 'fines', label: 'Fines' },
  { value: 'inventory', label: 'Inventory' },
  { value: 'reservations', label: 'Reservations' },
];

const COLUMNS_BY_TYPE = {
  circulation: [
    { key: 'borrowed_date', label: 'Borrowed', accessor: 'borrowed_date' },
    { key: 'book', label: 'Book', accessor: 'book' },
    { key: 'borrower', label: 'Borrower', accessor: 'borrower' },
    { key: 'due_date', label: 'Due', accessor: 'due_date' },
    { key: 'status', label: 'Status', accessor: 'status' },
  ],
  overdue: [
    { key: 'book', label: 'Book', accessor: 'book' },
    { key: 'borrower', label: 'Borrower', accessor: 'borrower' },
    { key: 'due_date', label: 'Due', accessor: 'due_date' },
    { key: 'days_overdue', label: 'Days Overdue', accessor: 'days_overdue' },
  ],
  fines: [
    { key: 'created_at', label: 'Date', accessor: 'created_at' },
    { key: 'book', label: 'Book', accessor: 'book' },
    { key: 'borrower', label: 'Borrower', accessor: 'borrower' },
    { key: 'amount', label: 'Amount', accessor: 'amount' },
    { key: 'status', label: 'Status', accessor: 'status' },
  ],
  inventory: [
    { key: 'title', label: 'Title', accessor: 'title' },
    { key: 'author', label: 'Author', accessor: 'author' },
    { key: 'total_copies', label: 'Total', accessor: 'total_copies' },
    { key: 'available_copies', label: 'Available', accessor: 'available_copies' },
  ],
  reservations: [
    { key: 'reserved_date', label: 'Reserved', accessor: 'reserved_date' },
    { key: 'book', label: 'Book', accessor: 'book' },
    { key: 'borrower', label: 'Borrower', accessor: 'borrower' },
    { key: 'status', label: 'Status', accessor: 'status' },
  ],
};

export function LibraryReports() {
  const { canReadFeature } = usePermissions();
  const canExport = canReadFeature('library_reports');
  const [reportType, setReportType] = useState('circulation');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['library-reports', reportType, startDate, endDate],
    queryFn: () => libraryReportsService.get({
      type: reportType,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    }),
    enabled: canExport,
  });

  const rows = data?.rows || [];
  const totals = data?.totals || {};

  const handleExport = async () => {
    try {
      await libraryReportsService.downloadCsv({
        type: reportType,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      notify.success('Report downloaded.');
    } catch (err) {
      notify.error(extractApiError(err, err?.message || 'Unable to download report.'));
    }
  };

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/library" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Library
        </Link>
      </div>

      <PageHeader
        title="Library Reports"
        subtitle="Circulation, fines, and inventory reports"
        actions={canExport && (
          <button type="button" className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1" onClick={handleExport}>
            <FiDownload size={14} /> Export CSV
          </button>
        )}
      />

      {isError && <div className="alert alert-danger">Unable to load library reports.</div>}

      <div className="apex-card p-3 p-md-4">
        <div className="d-flex flex-wrap gap-2 mb-3">
          <select className="form-select form-select-sm" style={{ width: 200 }} value={reportType} onChange={(e) => setReportType(e.target.value)}>
            {REPORT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
          {reportType !== 'inventory' && (
            <>
              <input type="date" className="form-control form-control-sm" style={{ width: 160 }} value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              <input type="date" className="form-control form-control-sm" style={{ width: 160 }} value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </>
          )}
        </div>

        {Object.keys(totals).length > 0 && (
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

export default LibraryReports;