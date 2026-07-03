import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { FiArrowLeft, FiPlus, FiUserCheck } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import Modal from '../../components/Modal';
import StatusBadge from '../../components/StatusBadge';
import StaffOnboardForm from '../../components/StaffOnboardForm';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { staffService } from '../../services/moduleService';
import { extractApiError, notify } from '../../utils/notify';
import { getRoleLabel } from '../../config/schoolRoles';

export function HRStaffs() {
  const queryClient = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [tempPassword, setTempPassword] = useState(null);

  const { data: staffList = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['staff', 'hr-staffs'],
    queryFn: () => staffService.list(),
  });

  const handleCreate = async (formData) => {
    setSaving(true);
    try {
      const payload = { ...formData };
      if (!payload.department) delete payload.department;
      if (!payload.password) delete payload.password;
      if (!payload.teacher?.qualification && !payload.teacher?.specialization) {
        delete payload.teacher;
      }

      const response = await staffService.create(payload);
      const temp = response?.temporary_password || response?.data?.temporary_password;
      setShowModal(false);
      setTempPassword(temp || null);
      await queryClient.invalidateQueries({ queryKey: ['staff'] });
      refetch();
      notify.success(
        temp
          ? 'Staff added. Share the temporary portal password securely with the employee.'
          : 'Staff member added successfully.',
      );
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to add staff member.'));
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { key: 'employee_id', label: 'Employee ID', accessor: 'employee_id', sortable: true },
    {
      key: 'full_name',
      label: 'Name',
      accessor: 'full_name',
      sortable: true,
      render: (row) => row.full_name || `${row.first_name || ''} ${row.last_name || ''}`.trim(),
    },
    {
      key: 'portal_role',
      label: 'Role',
      render: (row) => row.role_label || getRoleLabel(row.portal_role),
    },
    { key: 'designation', label: 'Designation', accessor: 'designation' },
    { key: 'department_name', label: 'Department', accessor: 'department_name' },
    { key: 'email', label: 'Work Email', accessor: 'email' },
    {
      key: 'portal',
      label: 'Portal',
      render: (row) => (
        row.has_user_account
          ? <span className="badge text-bg-success-subtle border text-success">Active</span>
          : <span className="badge text-bg-secondary-subtle border text-muted">No account</span>
      ),
    },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
  ];

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/hr" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Human Resources
        </Link>
      </div>

      <PageHeader
        title="Staffs"
        subtitle="Add and manage school employees — profiles, roles, and portal accounts"
        actions={(
          <button type="button" className="btn btn-primary btn-sm d-flex align-items-center gap-1" onClick={() => setShowModal(true)}>
            <FiPlus size={16} /> Add Staff
          </button>
        )}
      />

      {tempPassword && (
        <div className="alert alert-warning d-flex align-items-start gap-2 mb-4">
          <FiUserCheck className="mt-1 flex-shrink-0" />
          <div>
            <strong>Temporary portal password:</strong>{' '}
            <code className="user-select-all">{tempPassword}</code>
            <div className="small mt-1">Share securely and ask the staff member to change it on first login.</div>
            <button type="button" className="btn btn-link btn-sm p-0 mt-1" onClick={() => setTempPassword(null)}>Dismiss</button>
          </div>
        </div>
      )}

      {isError ? (
        <div className="alert alert-danger">Unable to load staff records.</div>
      ) : (
        <div className="apex-card p-3 p-md-4">
          <DataTable
            columns={columns}
            data={staffList}
            loading={isLoading}
            emptyState={(
              <ModuleEmptyState
                title="No staff yet"
                description="Add your first staff member to set up roles, emails, and portal access."
                actionLabel="Add Staff"
                onAction={() => setShowModal(true)}
              />
            )}
          />
        </div>
      )}

      <Modal
        show={showModal}
        onHide={() => setShowModal(false)}
        title="Add Staff Member"
        size="xl"
      >
        <StaffOnboardForm onSubmit={handleCreate} saving={saving} />
      </Modal>
    </div>
  );
}

export default HRStaffs;