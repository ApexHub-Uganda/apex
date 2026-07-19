import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiPlus } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import SearchableSelect from '../../components/SearchableSelect';
import StatusBadge from '../../components/StatusBadge';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { Modal } from '../../components/Modal';
import {
  feePaymentsService, feeStructuresService, studentsService, financeDocumentsService,
} from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';

const formatUGX = (amount) => {
  const n = Number(amount);
  if (Number.isNaN(n)) return '—';
  return `UGX ${n.toLocaleString('en-UG', { minimumFractionDigits: 0 })}`;
};

const PAYMENT_METHODS = [
  { value: 'mpesa', label: 'M-Pesa' },
  { value: 'cash', label: 'Cash' },
  { value: 'bank', label: 'Bank Transfer' },
  { value: 'cheque', label: 'Cheque' },
  { value: 'card', label: 'Card' },
];

const EMPTY_FORM = {
  student: '', fee_structure: '', amount_paid: '', payment_date: '',
  payment_method: 'mpesa', reference: '', receipt_number: '',
  mpesa_transaction_id: '', mpesa_phone: '', notes: '',
};

export function Finance() {
  const queryClient = useQueryClient();
  const { canReadFeature, canWriteFeature } = usePermissions();
  const canView = canReadFeature('payment_recording') || canReadFeature('student_billing');
  const canManage = canWriteFeature('payment_recording');
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const { data: payments = [], isLoading, isError } = useQuery({
    queryKey: ['fee-payments'],
    queryFn: () => feePaymentsService.list(),
    enabled: canView,
  });

  const { data: structures = [] } = useQuery({
    queryKey: ['fee-structures'],
    queryFn: () => feeStructuresService.list(),
  });

  const { data: students = [] } = useQuery({
    queryKey: ['students', 'finance-select'],
    queryFn: () => studentsService.list({ status: 'active', page_size: 500 }),
  });

  const studentOptions = useMemo(() => (
    (students || []).map((s) => ({
      value: s.id,
      label: `${s.full_name || `${s.first_name || ''} ${s.last_name || ''}`.trim() || s.admission_number} — ${s.admission_number || ''}`.trim(),
      meta: [s.school_class_name || s.class_name, s.stream_name].filter(Boolean).join(' · ') || undefined,
      keywords: [s.admission_number, s.first_name, s.last_name, s.email, s.phone, s.upi_number].filter(Boolean).join(' '),
    }))
  ), [students]);

  const structureOptions = useMemo(() => (
    (structures || []).map((f) => ({
      value: f.id,
      label: `${f.name} — ${formatUGX(f.amount)}`,
      meta: [f.class_name, f.term_name, f.fee_category].filter(Boolean).join(' · ') || undefined,
      keywords: [f.name, f.fee_category, f.class_name, f.term_name, f.vote_head_code].filter(Boolean).join(' '),
    }))
  ), [structures]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await feePaymentsService.create({
        ...form,
        amount_paid: form.amount_paid,
      });
      notify.success('Payment recorded.');
      await queryClient.invalidateQueries({ queryKey: ['fee-payments'] });
      setShowModal(false);
      setForm(EMPTY_FORM);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to record payment.'));
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { key: 'student_name', label: 'Student', accessor: 'student_name', sortable: true },
    { key: 'student_admission', label: 'Admission No', accessor: 'student_admission' },
    { key: 'class_name', label: 'Class', accessor: 'class_name' },
    { key: 'fee_name', label: 'Fee Item', accessor: 'fee_name' },
    {
      key: 'amount_paid',
      label: 'Amount',
      render: (row) => <span className="fw-medium">{formatUGX(row.amount_paid)}</span>,
    },
    { key: 'payment_date', label: 'Date', accessor: 'payment_date' },
    {
      key: 'payment_method',
      label: 'Method',
      render: (row) => PAYMENT_METHODS.find((m) => m.value === row.payment_method)?.label || row.payment_method,
    },
    { key: 'receipt_number', label: 'Receipt', accessor: 'receipt_number' },
    { key: 'mpesa_transaction_id', label: 'M-Pesa ID', accessor: 'mpesa_transaction_id' },
    { key: 'approval_status', label: 'Approval', render: (row) => <StatusBadge status={row.approval_status || row.status} /> },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
    {
      key: 'actions',
      label: '',
      render: (row) => row.receipt_number ? (
        <button
          type="button"
          className="btn btn-link btn-sm p-0"
          onClick={async () => {
            try {
              await financeDocumentsService.paymentReceiptPdf(row.id);
              notify.success('Receipt downloaded.');
            } catch (err) {
              notify.error(extractApiError(err, 'Could not download receipt.'));
            }
          }}
        >
          PDF
        </button>
      ) : '—',
    },
  ];

  if (!canView) {
    return (
      <div className="apex-card p-5">
        <ModuleEmptyState title="Payments unavailable" message="Payment recording has not been enabled for your role in Permission Settings." />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Fee Payments"
        subtitle="Record school fees in UGX — mobile money, cash, bank, and receipt tracking"
        actions={canManage && (
          <button type="button" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1" onClick={() => setShowModal(true)}>
            <FiPlus size={16} /> Record Payment
          </button>
        )}
      />

      {isError ? (
        <div className="alert alert-danger">Unable to load payment records.</div>
      ) : (
        <div className="apex-card p-3 p-md-4">
          <DataTable
            columns={columns}
            data={payments}
            loading={isLoading}
            searchable
            searchPlaceholder="Search student, admission, receipt, M-Pesa ID, fee…"
            searchKeys={[
              'student_name', 'student_admission', 'class_name', 'fee_name',
              'receipt_number', 'mpesa_transaction_id', 'mpesa_phone', 'reference',
              'payment_method', 'status', 'approval_status', 'amount_paid',
            ]}
            emptyState={(
              <ModuleEmptyState
                title="No payments recorded"
                message="Record fee payments with M-Pesa transaction IDs and receipt numbers."
                actionLabel={canManage ? 'Record Payment' : undefined}
                onAction={canManage ? () => setShowModal(true) : undefined}
              />
            )}
          />
        </div>
      )}

      <Modal
        show={showModal}
        onHide={() => setShowModal(false)}
        title="Record Fee Payment"
        size="lg"
        footer={(
          <button type="button" className="btn btn-primary ms-auto" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Record payment'}
          </button>
        )}
      >
        <div className="row g-3">
          <div className="col-md-6">
            <label className="form-label small fw-medium">Student *</label>
            <SearchableSelect
              options={studentOptions}
              value={form.student}
              onChange={(val) => setForm({ ...form, student: val })}
              placeholder="Search student by name or admission no…"
              emptyLabel="No students match your search"
              required
            />
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Fee Structure *</label>
            <SearchableSelect
              options={structureOptions}
              value={form.fee_structure}
              onChange={(val) => setForm({ ...form, fee_structure: val })}
              placeholder="Search fee item, class, or term…"
              emptyLabel="No fee structures match"
              required
            />
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Amount (UGX) *</label>
            <input type="number" className="form-control" value={form.amount_paid} onChange={(e) => setForm({ ...form, amount_paid: e.target.value })} />
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Payment Date *</label>
            <input type="date" className="form-control" value={form.payment_date} onChange={(e) => setForm({ ...form, payment_date: e.target.value })} />
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Payment Method</label>
            <select className="form-select" value={form.payment_method} onChange={(e) => setForm({ ...form, payment_method: e.target.value })}>
              {PAYMENT_METHODS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">Receipt Number</label>
            <input className="form-control" value={form.receipt_number} onChange={(e) => setForm({ ...form, receipt_number: e.target.value })} />
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">M-Pesa Transaction ID</label>
            <input className="form-control" value={form.mpesa_transaction_id} onChange={(e) => setForm({ ...form, mpesa_transaction_id: e.target.value })} placeholder="e.g. QHK7X8Y9Z0" />
          </div>
          <div className="col-md-4">
            <label className="form-label small fw-medium">M-Pesa Phone</label>
            <input className="form-control" value={form.mpesa_phone} onChange={(e) => setForm({ ...form, mpesa_phone: e.target.value })} placeholder="2547XXXXXXXX" />
          </div>
          <div className="col-md-6">
            <label className="form-label small fw-medium">Reference</label>
            <input className="form-control" value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} />
          </div>
          <div className="col-12">
            <label className="form-label small fw-medium">Notes</label>
            <textarea className="form-control" rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default Finance;
