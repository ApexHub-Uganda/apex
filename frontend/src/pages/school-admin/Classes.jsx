import ModulePage from '../../components/ModulePage';
import { classesService } from '../../services/moduleService';

const MOCK_CLASSES = [
  { id: 1, name: 'Grade 10-A', teacher: 'Mr. David Kim', students: 32, room: 'Room 201', schedule: 'Mon-Fri 8AM' },
  { id: 2, name: 'Grade 9-B', teacher: 'Ms. Laura Brooks', students: 28, room: 'Room 105', schedule: 'Mon-Fri 8AM' },
  { id: 3, name: 'Grade 11-A', teacher: 'Dr. Sarah Mitchell', students: 30, room: 'Room 301', schedule: 'Mon-Fri 9AM' },
  { id: 4, name: 'Grade 8-C', teacher: 'Mr. John Adams', students: 35, room: 'Room 102', schedule: 'Mon-Fri 8AM' },
];

export function Classes() {
  return (
    <ModulePage
      title="Classes"
      subtitle="Manage class sections and schedules"
      queryKey={['classes']}
      fetchData={() => classesService.list()}
      mockData={MOCK_CLASSES}
      onCreate={(data) => classesService.create(data)}
      onUpdate={(id, data) => classesService.update(id, data)}
      onDelete={(id) => classesService.delete(id)}
      createLabel="Add Class"
      columns={[
        { key: 'name', label: 'Class', accessor: 'name', sortable: true },
        { key: 'teacher', label: 'Class Teacher', accessor: 'teacher' },
        { key: 'students', label: 'Students', accessor: 'students', sortable: true },
        { key: 'room', label: 'Room', accessor: 'room' },
        { key: 'schedule', label: 'Schedule', accessor: 'schedule' },
      ]}
      formFields={[
        { name: 'name', label: 'Class Name', required: true },
        { name: 'teacher', label: 'Class Teacher', required: true },
        { name: 'room', label: 'Room Number', required: true },
        { name: 'schedule', label: 'Schedule' },
      ]}
    />
  );
}

export default Classes;