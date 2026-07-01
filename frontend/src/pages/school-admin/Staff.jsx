import ModulePage from '../../components/ModulePage';
import StatusBadge from '../../components/StatusBadge';
import { staffService } from '../../services/moduleService';
import { MOCK_STAFF } from '../../utils/mockData';

export function Staff() {
  return (
    <ModulePage
      title="Staff"
      subtitle="Manage teachers and administrative staff"
      queryKey={['staff']}
      fetchData={() => staffService.list()}
      mockData={MOCK_STAFF}
      onCreate={(data) => staffService.create(data)}
      onUpdate={(id, data) => staffService.update(id, data)}
      onDelete={(id) => staffService.delete(id)}
      createLabel="Add Staff"
      columns={[
        { key: 'employee_id', label: 'Employee ID', accessor: 'employee_id', sortable: true },
        { key: 'name', label: 'Name', accessor: 'name', sortable: true },
        { key: 'role', label: 'Role', accessor: 'role' },
        { key: 'department', label: 'Department', accessor: 'department' },
        { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
      ]}
      formFields={[
        { name: 'name', label: 'Full Name', required: true },
        { name: 'employee_id', label: 'Employee ID', required: true },
        { name: 'role', label: 'Role', required: true },
        { name: 'department', label: 'Department', type: 'select', options: [
          { value: 'Administration', label: 'Administration' },
          { value: 'Academics', label: 'Academics' },
          { value: 'Library', label: 'Library' },
          { value: 'Finance', label: 'Finance' },
        ]},
      ]}
    />
  );
}

export default Staff;