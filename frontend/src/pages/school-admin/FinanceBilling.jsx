import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiDollarSign } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import DataTable from '../../components/DataTable';
import SearchableSelect from '../../components/SearchableSelect';
import {
  classesService,
  termsService,
  financeBillingService,
  invoicesService,
} from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';

const formatUGX = (amount) => {
  const n = Number(amount);
  if (Number.isNaN(n)) return amount ?? '—';
  return `UGX ${n.toLocaleString('en-UG', { minimumFractionDigits: 0 })}`;
};

export function FinanceBilling() {
  const queryClient = useQueryClient();
  const { canWriteFeature, canReadFeature } = usePermissions();
  const canBill = canWriteFeature('student_billing');
  const canView = canReadFeature('student_billing') || canReadFeature('invoice_generation');

  const [schoolClass, setSchoolClass] = useState('');
  const [term, setTerm] = useState('');
  const [busy, setBusy] = useState(false);
  const [lastResult, setLastResult] = useState(null);

  const { data: classes = [] } = useQuery({
    queryKey: ['classes', 'billing'],
    queryFn: () => classesService.list({ page_size: 200 }),
    enabled: canView,
  });
  const { data: terms = [] } = useQuery({
    queryKey: ['terms', 'billing'],
    queryFn: () => termsService.list({ page_size: 50 }),
    enabled: canView,
  });
  const { data: invoices = [], isLoading } = useQuery({
    queryKey: ['invoices', 'billing-list'],
    queryFn: () => invoicesService.list({ page_size: 100 }),
    enabled: canView,
  });

  const classOptions = useMemo(() => (
    (classes || []).map((c) => ({
      value: c.id,
      label: `${c.name}${c.code ? ` (${c.code})` : ''}`,
      meta: c.academic_year_name || c.level || undefined,
      keywords: [c.name, c.code, c.academic_year_name].filter(Boolean).join(' '),
    }))
  ), [classes]);

  const termOptions = useMemo(() => (
    (terms || []).map((t) => ({
      value: t.id,
      label: t.name,
      meta: t.academic_year_name || (t.is_current ? 'Current term' : undefined),
      keywords: [t.name, t.academic_year_name, t.term_number].filter(Boolean).join(' '),
    }))
  ), [terms]);

  const invoiceColumns = useMemo(() => [
    { key: 'invoice_number', label: 'Invoice #', accessor: 'invoice_number', sortable: true },
    { key: 'student_name', label: 'Student', accessor: 'student_name', sortable: true },
    {
      key: 'total_amount',
      label: 'Total',
      render: (row) => formatUGX(row.total_amount),
      searchValue: (row) => row.total_amount,
    },
    { key: 'status', label: 'Status', accessor: 'status' },
  ], []);

  const handleBill = async () => {
    if (!schoolClass || !term) {
      notify.error('Select class and term.');
      return;
    }
    setBusy(true);
    try {
      const data = await financeBillingService.billClass({
        school_class: schoolClass,
        term,
        only_mandatory: true,
      });
      setLastResult(data);
      notify.success(
        `Billing done: ${data.created_count} invoices created, ${data.skipped_count} already billed.`,
      );
      await queryClient.invalidateQueries({ queryKey: ['invoices'] });
      await queryClient.invalidateQueries({ queryKey: ['student-fee-balances'] });
    } catch (err) {
      notify.error(extractApiError(err, 'Billing failed.'));
    } finally {
      setBusy(false);
    }
  };

  if (!canView) {
    return (
      <div className="apex-card p-5">
        <ModuleEmptyState
          title="Billing unavailable"
          message="Student billing has not been enabled for your role."
        />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/finance/payments" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Payments
        </Link>
      </div>

      <PageHeader
        title="Student billing"
        subtitle="Charge a whole class for a term from fee structures — creates invoices and balances"
      />

      <div className="row g-4">
        <div className="col-lg-5">
          <div className="apex-card p-4">
            <h6 className="fw-semibold mb-3 d-flex align-items-center gap-2">
              <FiDollarSign /> Bill class for term
            </h6>
            <div className="mb-3">
              <label className="form-label small fw-medium">Class</label>
              <SearchableSelect
                options={classOptions}
                value={schoolClass}
                onChange={setSchoolClass}
                placeholder="Search class by name or code…"
                disabled={!canBill}
              />
            </div>
            <div className="mb-3">
              <label className="form-label small fw-medium">Term</label>
              <SearchableSelect
                options={termOptions}
                value={term}
                onChange={setTerm}
                placeholder="Search term…"
                disabled={!canBill}
              />
            </div>
            <p className="small text-muted">
              Uses mandatory fee structures for the selected class and term. Students already billed
              for that term are skipped.
            </p>
            {canBill && (
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleBill}
                disabled={busy || !schoolClass || !term}
              >
                {busy ? 'Billing…' : 'Generate invoices'}
              </button>
            )}
            {lastResult && (
              <div className="alert alert-info mt-3 small mb-0">
                Created: {lastResult.created_count} · Skipped: {lastResult.skipped_count}
                {lastResult.error_count ? ` · Errors: ${lastResult.error_count}` : ''}
              </div>
            )}
          </div>
        </div>

        <div className="col-lg-7">
          <div className="apex-card p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h6 className="fw-semibold mb-0">Recent invoices</h6>
              <Link to="/school-admin/finance/invoices" className="btn btn-sm btn-outline-primary">
                All invoices
              </Link>
            </div>
            <DataTable
              columns={invoiceColumns}
              data={invoices || []}
              loading={isLoading}
              pageSize={10}
              searchable
              searchPlaceholder="Search invoice #, student, status…"
              searchKeys={['invoice_number', 'student_name', 'student', 'status', 'total_amount']}
              emptyState={(
                <ModuleEmptyState
                  title="No invoices yet"
                  message="Bill a class to generate student invoices from fee structures."
                />
              )}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default FinanceBilling;
