import EntityListPage from '../../components/EntityListPage';
import { getEntityConfig } from '../../config/entityRegistry';

export function Attendance() {
  return (
    <EntityListPage
      title="Attendance"
      featureKey="student_attendance"
      config={getEntityConfig('student_attendance')}
    />
  );
}

export default Attendance;