import AcademicRoleWorkspace from './AcademicRoleWorkspace';

export function TeacherWorkspace() {
  return (
    <AcademicRoleWorkspace
      title="Teacher Workspace"
      subtitle="Your classes, marks entry, lesson attendance, and teaching tasks."
      featureKey="teacher_workspace"
    />
  );
}

export default TeacherWorkspace;