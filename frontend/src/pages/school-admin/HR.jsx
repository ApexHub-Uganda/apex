import ModulePage from '../../components/ModulePage';
import StatusBadge from '../../components/StatusBadge';
import { hrService } from '../../services/moduleService';

const MOCK_HR = [
  { id: 1, employee: 'Dr. Sarah Mitchell', type: 'Leave Request', details: 'Annual Leave - 5 days', from_date: '2026-07-10', status: 'pending' },
  { id: 2, employee: 'Mr. David Kim', type: 'Leave Request', details: 'Sick Leave - 2 days', from_date: '2026-06-28', status: 'active' },
  { id: 3, employee: 'Ms. Laura Brooks', type: 'Performance Review', details: 'Q2 2026 Review', from_date: '2026-06-30', status: 'pending' },
  { id: 4, employee: 'Mr. John Adams', type: 'Training', details: 'Digital Teaching Workshop', from_date: '2026-07-15', status: 'active' },
];

export function HR() {
  return (
    <ModulePage
      title="Human Resources"
      subtitle="Manage leave, performance, and employee records"
      queryKey={['hr']}
      fetchData={() => hrService.list()}
      mockData={MOCK_HR}
      onCreate={(data) => hrService.create(data)}
      createLabel="New Request"
      columns={[
        { key: 'employee', label: 'Employee', accessor: 'employee', sortable: true },
        { key: 'type', label: 'Type', accessor: 'type' },
        { key: 'details', label: 'Details', accessor: 'details' },
        { key: 'from_date', label: 'Date', accessor: 'from_date' },
        { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
      ]}
      formFields={[
        { name: 'employee', label: 'Employee', required: true },
        { name: 'type', label: 'Type', type: 'select', options: [
          { value: 'Leave Request', label: 'Leave Request' },
          { value: 'Performance Review', label: 'Performance Review' },
          { value: 'Training', label: 'Training' },
        ]},
        { name: 'details', label: 'Details', type: 'textarea', required: true },
        { name: 'from_date', label: 'Date', type: 'date', required: true },
      ]}
    />
  );
}

export default HR;