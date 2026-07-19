import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiSave } from 'react-icons/fi';
import WorkspaceShell from '../../components/WorkspaceShell';
import StaffOnboardForm from '../../components/StaffOnboardForm';
import UserDeleteDangerZone from '../../components/UserDeleteDangerZone';
import { usePermissions } from '../../hooks/usePermissions';
import { staffService } from '../../services/moduleService';
import { extractApiError, notify } from '../../utils/notify';

const STAFF_WRITE_FIELDS = [
  'employee_id', 'first_name', 'middle_name', 'last_name', 'email', 'personal_email',
  'phone', 'alternate_phone', 'gender', 'date_of_birth', 'national_id', 'nationality',
  'staff_category', 'portal_role', 'designation', 'department', 'supervisor',
  'date_joined', 'date_left', 'employment_type', 'status', 'address',
  'emergency_contact', 'emergency_phone', 'emergency_relationship',
  'qualification_summary', 'notes', 'has_portal_access', 'teacher',
];

const normalizeRelationId = (value) => {
  if (value == null || value === '') return undefined;
  if (typeof value === 'object') return value.id || undefined;
  return value;
};

const buildStaffPayload = (formData, { isEdit }) => {
  const payload = {};
  STAFF_WRITE_FIELDS.forEach((field) => {
    if (!(field in formData)) return;
    const value = formData[field];
    if (value === '' || value == null) {
      if (field === 'department' || field === 'supervisor') return;
      if (!isEdit || field === 'date_of_birth' || field === 'date_left') return;
    }
    payload[field] = value;
  });

  const department = normalizeRelationId(formData.department);
  const supervisor = normalizeRelationId(formData.supervisor);
  if (department) payload.department = department;
  if (supervisor) payload.supervisor = supervisor;

  if (!payload.password) delete payload.password;
  if (
    payload.teacher
    && !payload.teacher?.qualification
    && !payload.teacher?.specialization
    && payload.teacher?.years_experience == null
    && !payload.teacher?.is_class_teacher
  ) {
    delete payload.teacher;
  }

  return payload;
};

export function StaffWorkspace() {
  const { staffId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { canReadDeleteUser, canWriteDeleteUser } = usePermissions();
  const isEdit = Boolean(staffId && staffId !== 'new');

  const { data: staff, isLoading, isError } = useQuery({
    queryKey: ['staff', staffId],
    queryFn: () => staffService.get(staffId),
    enabled: isEdit,
  });

  const handleDeleteStaff = async () => {
    await staffService.delete(staffId);
    notify.success('Staff record deleted.');
    await queryClient.invalidateQueries({ queryKey: ['staff'] });
    navigate('/school-admin/hr/staffs');
  };

  const handleSubmit = async (formData) => {
    try {
      const payload = buildStaffPayload(formData, { isEdit });

      if (isEdit) {
        await staffService.update(staffId, payload);
        notify.success('Staff profile updated successfully.');
      } else {
        const response = await staffService.create(payload);
        const message = response?.message || '';
        if (payload.has_portal_access !== false && message.toLowerCase().includes('emailed')) {
          notify.success('Staff added. Portal login credentials were emailed to their work address.');
        } else {
          notify.success(message || 'Staff member added successfully.');
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
    employee_id: staff.employee_id,
    first_name: staff.first_name,
    middle_name: staff.middle_name || '',
    last_name: staff.last_name,
    email: staff.email,
    personal_email: staff.personal_email || '',
    phone: staff.phone,
    alternate_phone: staff.alternate_phone || '',
    gender: staff.gender || '',
    date_of_birth: staff.date_of_birth || '',
    national_id: staff.national_id || '',
    nationality: staff.nationality || 'Kenyan',
    staff_category: staff.staff_category,
    portal_role: staff.portal_role,
    designation: staff.designation,
    department: normalizeRelationId(staff.department) || '',
    supervisor: normalizeRelationId(staff.supervisor) || '',
    date_joined: staff.date_joined,
    date_left: staff.date_left || '',
    employment_type: staff.employment_type,
    status: staff.status,
    address: staff.address || '',
    emergency_contact: staff.emergency_contact || '',
    emergency_phone: staff.emergency_phone || '',
    emergency_relationship: staff.emergency_relationship || '',
    qualification_summary: staff.qualification_summary || '',
    notes: staff.notes || '',
    has_portal_access: staff.has_portal_access,
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

      {isEdit && (
        <UserDeleteDangerZone
          entityLabel="staff member"
          recordName={staff?.full_name}
          description="Permanently remove this staff member from the school directory. Portal access and teaching assignments will be revoked."
          onDelete={handleDeleteStaff}
          canRead={canReadDeleteUser('staff_management')}
          canWrite={canWriteDeleteUser('staff_management')}
        />
      )}
    </WorkspaceShell>
  );
}

export default StaffWorkspace;