import ModulePage from '../../components/ModulePage';
import StatusBadge from '../../components/StatusBadge';
import { financeService } from '../../services/moduleService';

const MOCK_FINANCE = [
  { id: 1, student: 'Aisha Patel', class: 'Grade 10-A', fee_type: 'Tuition', amount: 2500, due_date: '2026-07-01', status: 'paid' },
  { id: 2, student: 'James Wilson', class: 'Grade 9-B', fee_type: 'Tuition', amount: 2500, due_date: '2026-07-01', status: 'pending' },
  { id: 3, student: 'Emma Chen', class: 'Grade 11-A', fee_type: 'Transport', amount: 500, due_date: '2026-06-15', status: 'overdue' },
  { id: 4, student: 'Omar Hassan', class: 'Grade 8-C', fee_type: 'Tuition', amount: 2200, due_date: '2026-07-01', status: 'paid' },
];

export function Finance() {
  return (
    <ModulePage
      title="Finance"
      subtitle="Manage fees, payments, and financial records"
      queryKey={['finance']}
      fetchData={() => financeService.list()}
      mockData={MOCK_FINANCE}
      onCreate={(data) => financeService.create(data)}
      createLabel="Record Payment"
      columns={[
        { key: 'student', label: 'Student', accessor: 'student', sortable: true },
        { key: 'class', label: 'Class', accessor: 'class' },
        { key: 'fee_type', label: 'Fee Type', accessor: 'fee_type' },
        { key: 'amount', label: 'Amount', render: (row) => `$${row.amount.toLocaleString()}` },
        { key: 'due_date', label: 'Due Date', accessor: 'due_date' },
        { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
      ]}
      formFields={[
        { name: 'student', label: 'Student', required: true },
        { name: 'fee_type', label: 'Fee Type', type: 'select', options: [
          { value: 'Tuition', label: 'Tuition' },
          { value: 'Transport', label: 'Transport' },
          { value: 'Hostel', label: 'Hostel' },
          { value: 'Library', label: 'Library' },
        ]},
        { name: 'amount', label: 'Amount', type: 'number', required: true },
        { name: 'due_date', label: 'Due Date', type: 'date', required: true },
      ]}
    />
  );
}

export default Finance;