import ModulePage from '../../components/ModulePage';
import StatusBadge from '../../components/StatusBadge';
import { transportService } from '../../services/moduleService';

const MOCK_TRANSPORT = [
  { id: 1, route: 'Route A - North', vehicle: 'BUS-001', driver: 'John Smith', capacity: 45, students: 38, status: 'active' },
  { id: 2, route: 'Route B - South', vehicle: 'BUS-002', driver: 'Mike Johnson', capacity: 40, students: 35, status: 'active' },
  { id: 3, route: 'Route C - East', vehicle: 'VAN-001', driver: 'Tom Brown', capacity: 15, students: 12, status: 'active' },
  { id: 4, route: 'Route D - West', vehicle: 'BUS-003', driver: 'Chris Davis', capacity: 45, students: 0, status: 'inactive' },
];

export function Transport() {
  return (
    <ModulePage
      title="Transport"
      subtitle="Manage bus routes, vehicles, and student transport"
      queryKey={['transport']}
      fetchData={() => transportService.list()}
      mockData={MOCK_TRANSPORT}
      onCreate={(data) => transportService.create(data)}
      createLabel="Add Route"
      columns={[
        { key: 'route', label: 'Route', accessor: 'route', sortable: true },
        { key: 'vehicle', label: 'Vehicle', accessor: 'vehicle' },
        { key: 'driver', label: 'Driver', accessor: 'driver' },
        { key: 'capacity', label: 'Capacity', accessor: 'capacity' },
        { key: 'students', label: 'Students', accessor: 'students' },
        { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
      ]}
      formFields={[
        { name: 'route', label: 'Route Name', required: true },
        { name: 'vehicle', label: 'Vehicle ID', required: true },
        { name: 'driver', label: 'Driver Name', required: true },
        { name: 'capacity', label: 'Capacity', type: 'number', required: true },
      ]}
    />
  );
}

export default Transport;