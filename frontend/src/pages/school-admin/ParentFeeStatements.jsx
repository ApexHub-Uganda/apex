import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { parentFeeStatementsService } from '../../services/moduleService';

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

  return (
    <div>
      <PageHeader
        title="Fee Statements"
        subtitle="Read-only billing, payments, and balances for your children"
      />

      {isError && <div className="alert alert-danger">Unable to load fee statements.</div>}

      {isLoading ? (
        <div className="py-5 text-center"><div className="spinner-border text-primary" role="status" /></div>
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
            <div className="mb-3">
              <select
                className="form-select form-select-sm"
                style={{ maxWidth: 320 }}
                value={selectedChild || active?.student?.id || ''}
                onChange={(e) => setSelectedChild(e.target.value)}
              >
                {children.map((stmt) => (
                  <option key={stmt.student.id} value={stmt.student.id}>
                    {stmt.student.full_name} ({stmt.student.admission_number})
                  </option>
                ))}
              </select>
            </div>
          )}

          {active && (
            <div className="row g-3">
              <div className="col-12">
                <div className="apex-card p-3 p-md-4">
                  <h5 className="fw-semibold mb-1">{active.student.full_name}</h5>
                  <div className="small text-muted mb-3">
                    {active.student.admission_number}
                    {active.student.class_name ? ` · ${active.student.class_name}` : ''}
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
                  {(active.invoices || []).length === 0 ? (
                    <p className="small text-muted mb-0">No invoices on record.</p>
                  ) : (
                    <div className="table-responsive">
                      <table className="table table-sm mb-0">
                        <thead><tr><th>#</th><th>Issued</th><th>Amount</th><th>Status</th></tr></thead>
                        <tbody>
                          {active.invoices.map((inv) => (
                            <tr key={inv.invoice_number}>
                              <td>{inv.invoice_number}</td>
                              <td>{inv.issue_date}</td>
                              <td>{formatUGX(inv.total_amount)}</td>
                              <td>{inv.status}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>

              <div className="col-lg-6">
                <div className="apex-card p-3">
                  <h6 className="fw-semibold mb-3">Payments</h6>
                  {(active.payments || []).length === 0 ? (
                    <p className="small text-muted mb-0">No payments on record.</p>
                  ) : (
                    <div className="table-responsive">
                      <table className="table table-sm mb-0">
                        <thead><tr><th>Date</th><th>Item</th><th>Amount</th><th>Receipt</th></tr></thead>
                        <tbody>
                          {active.payments.map((p, idx) => (
                            <tr key={`${p.receipt_number}-${idx}`}>
                              <td>{p.payment_date}</td>
                              <td>{p.fee_item}</td>
                              <td>{formatUGX(p.amount_paid)}</td>
                              <td>{p.receipt_number || '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
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