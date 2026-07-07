import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiCheck } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import {
  feeDiscountsService,
  feePaymentsService,
  financeApprovalService,
  refundsService,
} from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';

export function FinanceApproval() {
  const queryClient = useQueryClient();
  const { canWriteFeature } = usePermissions();
  const canApprove = canWriteFeature('transaction_approval');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['finance-approval-queue'],
    queryFn: () => financeApprovalService.getQueue(),
    staleTime: 15_000,
  });

  const payments = data?.payments || [];
  const discounts = data?.discounts || [];
  const refunds = data?.refunds || [];
  const count = data?.count ?? (payments.length + discounts.length + refunds.length);

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ['finance-approval-queue'] });
    await queryClient.invalidateQueries({ queryKey: ['finance-workspace'] });
  };

  const approvePayment = async (id) => {
    try {
      await feePaymentsService.approve(id);
      notify.success('Payment approved.');
      await invalidate();
    } catch (err) {
      notify.error(extractApiError(err, 'Approval failed.'));
    }
  };

  const approveDiscount = async (id) => {
    try {
      await feeDiscountsService.approve(id);
      notify.success('Discount approved.');
      await invalidate();
    } catch (err) {
      notify.error(extractApiError(err, 'Approval failed.'));
    }
  };

  const approveRefund = async (id) => {
    try {
      await refundsService.approve(id);
      notify.success('Refund processed.');
      await invalidate();
    } catch (err) {
      notify.error(extractApiError(err, 'Approval failed.'));
    }
  };

  const renderTable = (title, rows, columns, onApprove) => (
    <div className="mb-4">
      <h6 className="fw-semibold mb-2">{title}</h6>
      {rows.length === 0 ? (
        <p className="small text-muted">No pending {title.toLowerCase()}.</p>
      ) : (
        <div className="table-responsive">
          <table className="table table-hover mb-0 align-middle">
            <thead className="table-light">
              <tr>
                {columns.map((col) => <th key={col.key}>{col.label}</th>)}
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  {columns.map((col) => <td key={col.key}>{row[col.key]}</td>)}
                  <td>
                    {canApprove && (
                      <button
                        type="button"
                        className="btn btn-sm btn-success d-inline-flex align-items-center gap-1"
                        onClick={() => onApprove(row.id)}
                      >
                        <FiCheck size={14} /> Approve
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/finance" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Finance
        </Link>
      </div>

      <PageHeader title="Transaction Approval" subtitle={`${count} item(s) awaiting bursar review`} />

      {isError && <div className="alert alert-danger">Unable to load approval queue.</div>}

      {isLoading ? (
        <div className="py-5 text-center"><div className="spinner-border text-primary" role="status" /></div>
      ) : count === 0 ? (
        <div className="apex-card p-5">
          <ModuleEmptyState title="No pending transactions" message="Assistant bursar submissions will appear here for approval." />
        </div>
      ) : (
        <div className="apex-card p-3 p-md-4">
          {renderTable('Payments', payments, [
            { key: 'student_name', label: 'Student' },
            { key: 'fee_name', label: 'Fee' },
            { key: 'amount_paid', label: 'Amount' },
            { key: 'payment_date', label: 'Date' },
          ], approvePayment)}
          {renderTable('Discounts', discounts, [
            { key: 'student_name', label: 'Student' },
            { key: 'discount_type', label: 'Type' },
            { key: 'amount', label: 'Amount' },
          ], approveDiscount)}
          {renderTable('Refunds', refunds, [
            { key: 'student_name', label: 'Student' },
            { key: 'amount', label: 'Amount' },
          ], approveRefund)}
        </div>
      )}
    </div>
  );
}

export default FinanceApproval;