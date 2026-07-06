import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiSave } from 'react-icons/fi';
import WorkspaceShell from '../../components/WorkspaceShell';
import StaffOnboardForm from '../../components/StaffOnboardForm';
import { staffService } from '../../services/moduleService';
import { extractApiError, notify } from '../../utils/notify';

export function StaffWorkspace() {
  const { staffId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isEdit = Boolean(staffId && staffId !== 'new');

  const { data: staff, isLoading, isError } = useQuery({
    queryKey: ['staff', staffId],
    queryFn: () => staffService.get(staffId),
    enabled: isEdit,
  });

  const handleSubmit = async (formData) => {
    try {
      const payload = { ...formData };
      if (!payload.department) delete payload.department;
      if (!payload.supervisor) delete payload.supervisor;
      if (!payload.password) delete payload.password;
      if (!payload.teacher?.qualification && !payload.teacher?.specialization && !payload.teacher?.years_experience) {
        delete payload.teacher;
      }

      if (isEdit) {
        await staffService.update(staffId, payload);
        notify.success('Staff profile updated successfully.');
      } else {
        const response = await staffService.create(payload);
        const temp = response?.temporary_password;
        if (temp) {
          notify.success('Staff added. Temporary portal password was generated — share it securely.');
        } else {
          notify.success('Staff member added successfully.');
        }
      }

      await queryClient.invalidateQueries({ queryKey: ['staff'] });
      navigate('/school-admin/hr/staffs');
    } catch (err) {
      notify.error(extractApiError(err, isEdit ? 'Unable to update staff profile.' : 'Unable to add staff member.'));
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
      <WorkspaceShell backTo="/school-admin/hr/staffs" backLabel="Staffs" title="Staff not found">
        <div className="alert alert-danger">Unable to load this staff record.</div>
      </WorkspaceShell>
    );
  }

  const initialValues = isEdit && staff ? {
    ...staff,
    department: staff.department || '',
    supervisor: staff.supervisor || '',
    teacher: staff.teacher_profile || {},
  } : undefined;

  return (
    <WorkspaceShell
      backTo="/school-admin/hr/staffs"
      backLabel="Staffs"
      title={isEdit ? `Edit ${staff?.full_name || 'Staff Member'}` : 'Add Staff Member'}
      subtitle={isEdit
        ? 'Update employment records, role assignment, and portal access.'
        : 'Capture complete staff details with automated role and category assignment.'}
    >
      <div className="apex-card p-3 p-md-4">
        <StaffOnboardForm
          key={staffId || 'new'}
          mode={isEdit ? 'edit' : 'create'}
          adminMode
          initialValues={initialValues}
          onSubmit={handleSubmit}
          submitLabel={isEdit ? 'Save staff profile' : 'Add staff member'}
        />
      </div>
    </WorkspaceShell>
  );
}

export default StaffWorkspace;