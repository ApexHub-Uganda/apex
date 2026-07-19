import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import DataTable from '../../components/DataTable';
import SearchableSelect from '../../components/SearchableSelect';
import { parentFeeStatementsService, financeDocumentsService } from '../../services/moduleService';
import { notify } from '../../utils/notify';
import { ApexLoader } from '../../components/ApexLoader';

const formatUGX = (amount) => {
  const n = Number(amount);
  if (Number.isNaN(n)) return '—';
  return `UGX ${n.toLocaleString('en-UG', { minimumFractionDigits: 0 })}`;
};

export function ParentFeeStatements() {
  const [selectedChild, setSelectedChild] = useState('');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['parent-fee-statements', selectedChild],
    queryFn: () => parentFeeStatementsService.get(selectedChild ? { student_id: selectedChild } : {}),
  });

  const children = data?.children || [];
  const active = children.find((c) => c.student?.id === selectedChild) || children[0];

  const childOptions = useMemo(() => (
    children.map((stmt) => ({
      value: stmt.student.id,
      label: `${stmt.student.full_name} (${stmt.student.admission_number})`,
      meta: stmt.student.class_name || undefined,
      keywords: [stmt.student.full_name, stmt.student.admission_number, stmt.student.class_name].filter(Boolean).join(' '),
    }))
  ), [children]);

  const invoiceColumns = useMemo(() => [
    { key: 'invoice_number', label: '#', accessor: 'invoice_number', sortable: true },
    { key: 'issue_date', label: 'Issued', accessor: 'issue_date' },
    {
      key: 'total_amount',
      label: 'Amount',
      render: (row) => formatUGX(row.total_amount),
      searchValue: (row) => row.total_amount,
    },
    { key: 'status', label: 'Status', accessor: 'status' },
  ], []);

  const paymentColumns = useMemo(() => [
    { key: 'payment_date', label: 'Date', accessor: 'payment_date', sortable: true },
    { key: 'fee_item', label: 'Item', accessor: 'fee_item' },
    {
      key: 'amount_paid',
      label: 'Amount',
      render: (row) => formatUGX(row.amount_paid),
      searchValue: (row) => row.amount_paid,
    },
    { key: 'receipt_number', label: 'Receipt', accessor: 'receipt_number' },
  ], []);

  return (
    <div>
      <PageHeader
        title="Fee Statements"
        subtitle="Read-only billing, payments, and balances for your children"
      />

      {isError && <div className="alert alert-danger">Unable to load fee statements.</div>}

      {isLoading ? (
        <div className="py-5 text-center"><ApexLoader label="Loading…" /></div>
      ) : children.length === 0 ? (
        <div className="apex-card p-5">
          <ModuleEmptyState
            title="No linked children"
            message="Fee statements appear when your account is linked to enrolled students."
          />
        </div>
      ) : (
        <>
          {children.length > 1 && (
            <div className="mb-3" style={{ maxWidth: 420 }}>
              <SearchableSelect
                options={childOptions}
                value={selectedChild || active?.student?.id || ''}
                onChange={setSelectedChild}
                placeholder="Search child by name or admission no…"
              />
            </div>
          )}

          {active && (
            <div className="row g-3">
              <div className="col-12">
                <div className="apex-card p-3 p-md-4">
                  <div className="d-flex flex-wrap justify-content-between align-items-start gap-2">
                    <div>
                      <h5 className="fw-semibold mb-1">{active.student.full_name}</h5>
                      <div className="small text-muted mb-3">
                        {active.student.admission_number}
                        {active.student.class_name ? ` · ${active.student.class_name}` : ''}
                      </div>
                    </div>
                    <button
                      type="button"
                      className="btn btn-outline-primary btn-sm"
                      onClick={async () => {
                        try {
                          await financeDocumentsService.statementPdf(active.student.id);
                          notify.success('Statement PDF downloaded.');
                        } catch {
                          notify.error('Unable to download statement PDF.');
                        }
                      }}
                    >
                      Download PDF
                    </button>
                  </div>
                  <div className="row g-3">
                    <div className="col-md-4"><div className="small text-muted">Total Billed</div><div className="fw-semibold">{formatUGX(active.summary.total_billed)}</div></div>
                    <div className="col-md-4"><div className="small text-muted">Total Paid</div><div className="fw-semibold">{formatUGX(active.summary.total_paid)}</div></div>
                    <div className="col-md-4"><div className="small text-muted">Balance</div><div className="fw-semibold text-primary">{formatUGX(active.summary.balance)}</div></div>
                  </div>
                </div>
              </div>

              <div className="col-lg-6">
                <div className="apex-card p-3">
                  <h6 className="fw-semibold mb-3">Invoices</h6>
                  <DataTable
                    columns={invoiceColumns}
                    data={active.invoices || []}
                    pageSize={8}
                    searchable
                    searchPlaceholder="Search invoices…"
                    searchKeys={['invoice_number', 'issue_date', 'total_amount', 'status']}
                    emptyState={<p className="small text-muted mb-0">No invoices on record.</p>}
                  />
                </div>
              </div>

              <div className="col-lg-6">
                <div className="apex-card p-3">
                  <h6 className="fw-semibold mb-3">Payments</h6>
                  <DataTable
                    columns={paymentColumns}
                    data={active.payments || []}
                    pageSize={8}
                    searchable
                    searchPlaceholder="Search payments by receipt, item…"
                    searchKeys={['payment_date', 'fee_item', 'amount_paid', 'receipt_number']}
                    emptyState={<p className="small text-muted mb-0">No payments on record.</p>}
                  />
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default ParentFeeStatements;
