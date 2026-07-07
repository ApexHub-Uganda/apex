import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowLeft, FiDownload } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { financeReportsService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';

const REPORT_TYPES = [
  { value: 'collections', label: 'Fee Collections' },
  { value: 'debtors', label: 'Outstanding Debtors' },
  { value: 'expenses', label: 'Expenses' },
];

const formatUGX = (amount) => {
  const n = Number(amount);
  if (Number.isNaN(n)) return amount ?? '—';
  return `UGX ${n.toLocaleString('en-UG', { minimumFractionDigits: 0 })}`;
};

const COLUMNS_BY_TYPE = {
  collections: [
    { key: 'payment_date', label: 'Date', accessor: 'payment_date' },
    { key: 'student', label: 'Student', accessor: 'student' },
    { key: 'admission_number', label: 'Admission', accessor: 'admission_number' },
    { key: 'fee_item', label: 'Fee Item', accessor: 'fee_item' },
    { key: 'amount', label: 'Amount', render: (row) => formatUGX(row.amount) },
    { key: 'payment_method', label: 'Method', accessor: 'payment_method' },
    { key: 'receipt_number', label: 'Receipt', accessor: 'receipt_number' },
  ],
  debtors: [
    { key: 'student', label: 'Student', accessor: 'student' },
    { key: 'admission_number', label: 'Admission', accessor: 'admission_number' },
    { key: 'class_name', label: 'Class', accessor: 'class_name' },
    { key: 'term', label: 'Term', accessor: 'term' },
    { key: 'balance', label: 'Balance', render: (row) => formatUGX(row.balance) },
  ],
  expenses: [
    { key: 'entry_date', label: 'Date', accessor: 'entry_date' },
    { key: 'description', label: 'Description', accessor: 'description' },
    { key: 'amount', label: 'Amount', render: (row) => formatUGX(row.amount) },
    { key: 'debit_account', label: 'Debit', accessor: 'debit_account' },
    { key: 'credit_account', label: 'Credit', accessor: 'credit_account' },
  ],
};

export function FinanceReports() {
  const { canReadFeature } = usePermissions();
  const canExport = canReadFeature('financial_reports');
  const [reportType, setReportType] = useState('collections');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['finance-reports', reportType, startDate, endDate],
    queryFn: () => financeReportsService.get({
      type: reportType,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    }),
    enabled: canExport,
  });

  const rows = data?.rows || [];
  const totals = data?.totals || {};

  const handleExport = () => {
    financeReportsService.downloadCsv({
      type: reportType,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    });
  };

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/finance" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Finance
        </Link>
      </div>

      <PageHeader
        title="Financial Reports"
        subtitle="Generate and export finance reports"
        actions={canExport && (
          <button type="button" className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1" onClick={handleExport}>
            <FiDownload size={14} /> Export CSV
          </button>
        )}
      />

      {isError && <div className="alert alert-danger">Unable to load financial reports.</div>}

      <div className="apex-card p-3 p-md-4">
        <div className="d-flex flex-wrap gap-2 mb-3">
          <select className="form-select form-select-sm" style={{ width: 200 }} value={reportType} onChange={(e) => setReportType(e.target.value)}>
            {REPORT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
          <input type="date" className="form-control form-control-sm" style={{ width: 160 }} value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          <input type="date" className="form-control form-control-sm" style={{ width: 160 }} value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </div>

        {Object.keys(totals).length > 0 && (
          <div className="small text-muted mb-3">
            Totals: {Object.entries(totals).map(([k, v]) => `${k}: ${formatUGX(v)}`).join(' · ')}
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

export default FinanceReports;