import { useMemo } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { usePermissions } from '../../hooks/usePermissions';
import WorkspaceShell from '../../components/WorkspaceShell';
import StudentForm from '../../components/StudentForm';
import UserDeleteDangerZone from '../../components/UserDeleteDangerZone';
import { studentsService } from '../../services/moduleService';
import { useAuth } from '../../hooks/useAuth';
import { extractApiError, notify } from '../../utils/notify';

export function StudentWorkspace() {
  const { studentId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isSchoolAdmin } = useAuth();
  const { canWriteFeature, canReadDeleteUser, canWriteDeleteUser } = usePermissions();
  const isEdit = Boolean(studentId && studentId !== 'new');

  const presetClassId = searchParams.get('school_class') || '';
  const presetStreamId = searchParams.get('stream') || '';
  const presetClassName = searchParams.get('class_name') || '';
  const presetStreamName = searchParams.get('stream_name') || '';
  const returnTo = searchParams.get('return_to') || '';

  const { data: importContext } = useQuery({
    queryKey: ['student-import-context'],
    queryFn: () => studentsService.getImportContext(),
    enabled: !isEdit,
    staleTime: 60_000,
  });

  const presetClassRow = importContext?.classes?.find(
    (row) => String(row.id) === String(presetClassId),
  );

  const canWriteEnrollment = canWriteFeature('student_management') || canWriteFeature('class_teacher_tools');
  const canEnrollNewStudent = isSchoolAdmin || (
    canWriteEnrollment && (
      !presetClassId
        ? Boolean(importContext?.can_enroll_students)
        : Boolean(presetClassRow?.can_enroll)
    )
  );

  const { data: student, isLoading, isError } = useQuery({
    queryKey: ['students', studentId],
    queryFn: () => studentsService.get(studentId),
    enabled: isEdit,
  });

  const backTo = returnTo || '/school-admin/students';
  const backLabel = returnTo ? 'Back to class' : 'Students';

  const handleDeleteStudent = async () => {
    await studentsService.delete(studentId);
    notify.success('Student record deleted.');
    await queryClient.invalidateQueries({ queryKey: ['students'] });
    await queryClient.invalidateQueries({ queryKey: ['classes-overview'] });
    navigate(backTo);
  };

  const handleSubmit = async (formData) => {
    if (!isEdit && !canEnrollNewStudent) {
      notify.error('You do not have permission to enroll students into this class.');
      return;
    }

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
      await queryClient.invalidateQueries({ queryKey: ['classes-overview'] });
      if (presetClassId) {
        await queryClient.invalidateQueries({ queryKey: ['class-hub', presetClassId] });
      }
      navigate(backTo);
    } catch (err) {
      notify.error(extractApiError(err, isEdit ? 'Unable to update student.' : 'Unable to enroll student.'));
      throw err;
    }
  };

  const createInitialValues = useMemo(() => {
    if (isEdit) return undefined;
    return {
      school_class: presetClassId,
      stream: presetStreamId,
    };
  }, [isEdit, presetClassId, presetStreamId]);

  if (isEdit && isLoading) {
    return (
      <div className="py-5 text-center">
        <div className="spinner-border text-primary" role="status" />
      </div>
    );
  }

  if (isEdit && isError) {
    return (
      <WorkspaceShell backTo={backTo} backLabel={backLabel} title="Student not found">
        <div className="alert alert-danger">Unable to load this student record.</div>
      </WorkspaceShell>
    );
  }

  const initialValues = isEdit && student ? {
    ...student,
    school_class: student.school_class || '',
    stream: student.stream || '',
    parents: student.parent_ids || student.parents || [],
  } : createInitialValues;

  const enrollmentTarget = presetClassName
    ? `${presetClassName}${presetStreamName ? ` · ${presetStreamName}` : ''}`
    : null;

  if (!isEdit && !canEnrollNewStudent) {
    return (
      <WorkspaceShell backTo={backTo} backLabel={backLabel} title="Enrollment restricted">
        <div className="alert alert-warning">
          You do not have permission to enroll students into this class. Assigned class teachers with student write access may enroll from their class page.
        </div>
      </WorkspaceShell>
    );
  }

  return (
    <WorkspaceShell
      backTo={backTo}
      backLabel={backLabel}
      title={isEdit ? `Edit ${student?.full_name || 'Student'}` : 'Add Student'}
      subtitle={isEdit
        ? 'Complete learner profile — UPI, parents, boarding, and other details.'
        : enrollmentTarget
          ? `Enroll a student into ${enrollmentTarget}. Other profile details can be completed later.`
          : 'Enter essentials now. Class teachers can complete the full profile after enrollment.'}
    >
      <StudentForm
        key={studentId || `${presetClassId}-${presetStreamId}` || 'new'}
        mode={isEdit ? 'edit' : 'create'}
        initialValues={initialValues}
        onSubmit={handleSubmit}
        submitLabel={isEdit ? 'Save student profile' : 'Add student'}
        lockClassFields={!isEdit && Boolean(presetClassId)}
        lockedClassLabel={presetClassName}
        lockedStreamLabel={presetStreamName || (presetClassId ? 'Whole class' : '')}
      />

      {isEdit && (
        <UserDeleteDangerZone
          entityLabel="student"
          recordName={student?.full_name}
          description="Permanently remove this learner from the school directory. Attendance, marks, and billing links may be affected."
          onDelete={handleDeleteStudent}
          canRead={canReadDeleteUser('student_management')}
          canWrite={canWriteDeleteUser('student_management')}
        />
      )}
    </WorkspaceShell>
  );
}

export default StudentWorkspace;