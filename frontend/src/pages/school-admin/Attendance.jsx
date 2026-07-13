import EntityListPage from '../../components/EntityListPage';
import { getEntityConfig } from '../../config/entityRegistry';
import { useTenant } from '../../hooks/useTenant';
import ClassAttendance from './ClassAttendance';

const TEACHER_ATTENDANCE_ROLES = new Set(['teacher', 'class_teacher']);

export function Attendance() {
  const { roleProfile } = useTenant();
  const role = roleProfile?.role;

  if (TEACHER_ATTENDANCE_ROLES.has(role)) {
    return <ClassAttendance />;
  }

  return (
    <EntityListPage
      title="Attendance"
      featureKey="student_attendance"
      config={getEntityConfig('student_attendance')}
    />
  );
}

export default Attendance;