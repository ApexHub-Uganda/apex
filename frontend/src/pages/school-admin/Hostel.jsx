import ModulePage from '../../components/ModulePage';
import StatusBadge from '../../components/StatusBadge';
import { hostelService } from '../../services/moduleService';

const MOCK_HOSTEL = [
  { id: 1, block: 'Block A', room: 'A-101', type: 'Boys', capacity: 4, occupied: 3, warden: 'Mr. Robert Lee' },
  { id: 2, block: 'Block A', room: 'A-102', type: 'Boys', capacity: 4, occupied: 4, warden: 'Mr. Robert Lee' },
  { id: 3, block: 'Block B', room: 'B-201', type: 'Girls', capacity: 4, occupied: 2, warden: 'Ms. Anna White' },
  { id: 4, block: 'Block B', room: 'B-202', type: 'Girls', capacity: 4, occupied: 4, warden: 'Ms. Anna White' },
];

export function Hostel() {
  return (
    <ModulePage
      title="Hostel"
      subtitle="Manage hostel blocks, rooms, and allocations"
      queryKey={['hostel']}
      fetchData={() => hostelService.list()}
      mockData={MOCK_HOSTEL}
      onCreate={(data) => hostelService.create(data)}
      createLabel="Add Room"
      columns={[
        { key: 'block', label: 'Block', accessor: 'block', sortable: true },
        { key: 'room', label: 'Room', accessor: 'room' },
        { key: 'type', label: 'Type', accessor: 'type' },
        { key: 'capacity', label: 'Capacity', accessor: 'capacity' },
        { key: 'occupied', label: 'Occupied', render: (row) => `${row.occupied}/${row.capacity}` },
        { key: 'warden', label: 'Warden', accessor: 'warden' },
        { key: 'status', label: 'Status', render: (row) => (
          <StatusBadge status={row.occupied >= row.capacity ? 'inactive' : 'active'} />
        )},
      ]}
      formFields={[
        { name: 'block', label: 'Block', required: true },
        { name: 'room', label: 'Room Number', required: true },
        { name: 'type', label: 'Type', type: 'select', options: [
          { value: 'Boys', label: 'Boys' },
          { value: 'Girls', label: 'Girls' },
        ]},
        { name: 'capacity', label: 'Capacity', type: 'number', required: true },
        { name: 'warden', label: 'Warden', required: true },
      ]}
    />
  );
}

export default Hostel;