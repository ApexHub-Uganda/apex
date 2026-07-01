import ModulePage from '../../components/ModulePage';
import StatusBadge from '../../components/StatusBadge';
import { payrollService } from '../../services/moduleService';

const MOCK_PAYROLL = [
  { id: 1, employee: 'Dr. Sarah Mitchell', role: 'Principal', basic: 8000, allowances: 1500, deductions: 800, net: 8700, status: 'paid' },
  { id: 2, employee: 'Mr. David Kim', role: 'Teacher', basic: 4500, allowances: 500, deductions: 450, net: 4550, status: 'paid' },
  { id: 3, employee: 'Ms. Laura Brooks', role: 'Librarian', basic: 3800, allowances: 300, deductions: 380, net: 3720, status: 'pending' },
  { id: 4, employee: 'Mr. John Adams', role: 'Teacher', basic: 4500, allowances: 500, deductions: 450, net: 4550, status: 'pending' },
];

export function Payroll() {
  return (
    <ModulePage
      title="Payroll"
      subtitle="Manage staff salaries and payment processing"
      queryKey={['payroll']}
      fetchData={() => payrollService.list()}
      mockData={MOCK_PAYROLL}
      createLabel="Process Payroll"
      columns={[
        { key: 'employee', label: 'Employee', accessor: 'employee', sortable: true },
        { key: 'role', label: 'Role', accessor: 'role' },
        { key: 'basic', label: 'Basic', render: (row) => `$${row.basic.toLocaleString()}` },
        { key: 'allowances', label: 'Allowances', render: (row) => `$${row.allowances.toLocaleString()}` },
        { key: 'deductions', label: 'Deductions', render: (row) => `$${row.deductions.toLocaleString()}` },
        { key: 'net', label: 'Net Pay', render: (row) => <span className="fw-bold">${row.net.toLocaleString()}</span> },
        { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
      ]}
      formFields={[
        { name: 'employee', label: 'Employee', required: true },
        { name: 'basic', label: 'Basic Salary', type: 'number', required: true },
        { name: 'allowances', label: 'Allowances', type: 'number' },
        { name: 'deductions', label: 'Deductions', type: 'number' },
      ]}
    />
  );
}

export default Payroll;