import AcademicRoleWorkspace from './AcademicRoleWorkspace';

export function ClassTeacherWorkspace() {
  return (
    <AcademicRoleWorkspace
      title="Class Teacher Tools"
      subtitle="Class welfare — notices, discipline, and report cards for your assigned class."
      featureKey="class_teacher_tools"
      backTo="/school-admin/academics/teacher"
      backLabel="Teacher Workspace"
    />
  );
}

export default ClassTeacherWorkspace;