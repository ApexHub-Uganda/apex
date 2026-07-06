import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import WorkspaceShell from '../../components/WorkspaceShell';
import StudentForm from '../../components/StudentForm';
import { studentsService } from '../../services/moduleService';
import { extractApiError, notify } from '../../utils/notify';

export function StudentWorkspace() {
  const { studentId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isEdit = Boolean(studentId && studentId !== 'new');

  const { data: student, isLoading, isError } = useQuery({
    queryKey: ['students', studentId],
    queryFn: () => studentsService.get(studentId),
    enabled: isEdit,
  });

  const handleSubmit = async (formData) => {
    try {
      const payload = { ...formData };
      if (Array.isArray(payload.parents)) {
        payload.parents = payload.parents.filter(Boolean);
      }

      if (isEdit) {
        await studentsService.update(studentId, payload);
        notify.success('Student record updated.');
      } else {
        await studentsService.create(payload);
        notify.success('Student enrolled successfully.');
      }

      await queryClient.invalidateQueries({ queryKey: ['students'] });
      navigate('/school-admin/students');
    } catch (err) {
      notify.error(extractApiError(err, isEdit ? 'Unable to update student.' : 'Unable to enroll student.'));
      throw err;
    }
  };

  if (isEdit && isLoading) {
    return (
      <div className="py-5 text-center">
        <div className="spinner-border text-primary" role="status" />
      </div>
    );
  }

  if (isEdit && isError) {
    return (
      <WorkspaceShell backTo="/school-admin/students" backLabel="Students" title="Student not found">
        <div className="alert alert-danger">Unable to load this student record.</div>
      </WorkspaceShell>
    );
  }

  const initialValues = isEdit && student ? {
    ...student,
    school_class: student.school_class || '',
    stream: student.stream || '',
    parents: student.parent_ids || student.parents || [],
  } : undefined;

  return (
    <WorkspaceShell
      backTo="/school-admin/students"
      backLabel="Students"
      title={isEdit ? `Edit ${student?.full_name || 'Student'}` : 'Add Student'}
      subtitle={isEdit
        ? 'Complete learner profile — UPI, parents, boarding, and other details.'
        : 'Enter essentials now. Class teachers can complete the full profile after enrollment.'}
    >
      <StudentForm
        key={studentId || 'new'}
        mode={isEdit ? 'edit' : 'create'}
        initialValues={initialValues}
        onSubmit={handleSubmit}
        submitLabel={isEdit ? 'Save student profile' : 'Add student'}
      />
    </WorkspaceShell>
  );
}

export default StudentWorkspace;