import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiCheck, FiX } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import DataTable from '../../components/DataTable';
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

  const rejectPayment = async (id) => {
    try {
      await feePaymentsService.reject?.(id, { reason: 'Rejected from approval queue' });
      notify.success('Payment rejected.');
      await invalidate();
    } catch (err) {
      notify.error(extractApiError(err, 'Reject failed.'));
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

  const paymentColumns = useMemo(() => [
    { key: 'student_name', label: 'Student', accessor: 'student_name', sortable: true },
    { key: 'fee_name', label: 'Fee', accessor: 'fee_name' },
    { key: 'amount_paid', label: 'Amount', accessor: 'amount_paid', sortable: true },
    { key: 'payment_date', label: 'Date', accessor: 'payment_date' },
    {
      key: 'actions',
      label: '',
      render: (row) => canApprove && (
        <div className="d-flex gap-1">
          <button
            type="button"
            className="btn btn-sm btn-success d-inline-flex align-items-center gap-1"
            onClick={() => approvePayment(row.id)}
          >
            <FiCheck size={14} /> Approve
          </button>
          <button
            type="button"
            className="btn btn-sm btn-outline-danger d-inline-flex align-items-center gap-1"
            onClick={() => rejectPayment(row.id)}
          >
            <FiX size={14} /> Reject
          </button>
        </div>
      ),
    },
  ], [canApprove]);

  const discountColumns = useMemo(() => [
    { key: 'student_name', label: 'Student', accessor: 'student_name', sortable: true },
    { key: 'discount_type', label: 'Type', accessor: 'discount_type' },
    { key: 'amount', label: 'Amount', accessor: 'amount' },
    {
      key: 'actions',
      label: '',
      render: (row) => canApprove && (
        <button
          type="button"
          className="btn btn-sm btn-success d-inline-flex align-items-center gap-1"
          onClick={() => approveDiscount(row.id)}
        >
          <FiCheck size={14} /> Approve
        </button>
      ),
    },
  ], [canApprove]);

  const refundColumns = useMemo(() => [
    { key: 'student_name', label: 'Student', accessor: 'student_name', sortable: true },
    { key: 'amount', label: 'Amount', accessor: 'amount' },
    {
      key: 'actions',
      label: '',
      render: (row) => canApprove && (
        <button
          type="button"
          className="btn btn-sm btn-success d-inline-flex align-items-center gap-1"
          onClick={() => approveRefund(row.id)}
        >
          <FiCheck size={14} /> Approve
        </button>
      ),
    },
  ], [canApprove]);

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
        <div className="d-flex flex-column gap-4">
          <div className="apex-card p-3 p-md-4">
            <h6 className="fw-semibold mb-3">Payments ({payments.length})</h6>
            <DataTable
              columns={paymentColumns}
              data={payments}
              searchable
              searchPlaceholder="Search payment by student, fee, amount, date…"
              searchKeys={['student_name', 'fee_name', 'amount_paid', 'payment_date', 'receipt_number']}
              emptyState={<p className="small text-muted mb-0">No pending payments.</p>}
            />
          </div>
          <div className="apex-card p-3 p-md-4">
            <h6 className="fw-semibold mb-3">Discounts ({discounts.length})</h6>
            <DataTable
              columns={discountColumns}
              data={discounts}
              searchable
              searchPlaceholder="Search discount by student, type, amount…"
              searchKeys={['student_name', 'discount_type', 'amount', 'reason']}
              emptyState={<p className="small text-muted mb-0">No pending discounts.</p>}
            />
          </div>
          <div className="apex-card p-3 p-md-4">
            <h6 className="fw-semibold mb-3">Refunds ({refunds.length})</h6>
            <DataTable
              columns={refundColumns}
              data={refunds}
              searchable
              searchPlaceholder="Search refund by student or amount…"
              searchKeys={['student_name', 'amount', 'reason']}
              emptyState={<p className="small text-muted mb-0">No pending refunds.</p>}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default FinanceApproval;
