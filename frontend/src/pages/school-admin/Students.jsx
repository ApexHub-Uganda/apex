import ModulePage from '../../components/ModulePage';
import StatusBadge from '../../components/StatusBadge';
import { studentsService } from '../../services/moduleService';
import { MOCK_STUDENTS } from '../../utils/mockData';

export function Students() {
  return (
    <ModulePage
      title="Students"
      subtitle="Manage student records and enrollments"
      queryKey={['students']}
      fetchData={() => studentsService.list()}
      mockData={MOCK_STUDENTS}
      onCreate={(data) => studentsService.create(data)}
      onUpdate={(id, data) => studentsService.update(id, data)}
      onDelete={(id) => studentsService.delete(id)}
      createLabel="Enroll Student"
      columns={[
        { key: 'admission_no', label: 'Admission No', accessor: 'admission_no', sortable: true },
        { key: 'name', label: 'Name', accessor: 'name', sortable: true },
        { key: 'class', label: 'Class', accessor: 'class' },
        { key: 'gender', label: 'Gender', accessor: 'gender' },
        { key: 'guardian', label: 'Guardian', accessor: 'guardian' },
        { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
      ]}
      formFields={[
        { name: 'name', label: 'Full Name', required: true },
        { name: 'admission_no', label: 'Admission Number', required: true },
        { name: 'class', label: 'Class', type: 'select', required: true, options: [
          { value: 'Grade 8-A', label: 'Grade 8-A' },
          { value: 'Grade 9-B', label: 'Grade 9-B' },
          { value: 'Grade 10-A', label: 'Grade 10-A' },
          { value: 'Grade 11-A', label: 'Grade 11-A' },
        ]},
        { name: 'gender', label: 'Gender', type: 'select', options: [
          { value: 'Male', label: 'Male' },
          { value: 'Female', label: 'Female' },
        ]},
        { name: 'guardian', label: 'Guardian Name', required: true },
      ]}
    />
  );
}

export default Students;