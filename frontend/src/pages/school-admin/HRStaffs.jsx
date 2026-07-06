import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiEdit2, FiPlus, FiUpload } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import StatusBadge from '../../components/StatusBadge';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import BulkImportWizard from '../../components/BulkImportWizard';
import { staffService } from '../../services/moduleService';
import { staffBulkImport } from '../../services/bulkImportService';
import { getRoleLabel } from '../../config/schoolRoles';
import { usePermissions } from '../../hooks/usePermissions';
import { useAuth } from '../../hooks/useAuth';
import { PersonNameCell } from '../../components/PersonAvatar';
import { notify } from '../../utils/notify';

export function HRStaffs() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isSchoolAdmin } = useAuth();
  const { canWriteModule } = usePermissions();
  const canManage = isSchoolAdmin || canWriteModule('human_resource') || canWriteModule('core_management');
  const [showImport, setShowImport] = useState(false);

  const { data: staffList = [], isLoading, isError } = useQuery({
    queryKey: ['staff', 'hr-staffs'],
    queryFn: () => staffService.list(),
  });

  const columns = [
    { key: 'employee_id', label: 'Employee ID', accessor: 'employee_id', sortable: true, width: '7%' },
    {
      key: 'full_name',
      label: 'Name',
      accessor: 'full_name',
      sortable: true,
      render: (row) => <PersonNameCell row={row} />,
    },
    {
      key: 'portal_role',
      label: 'Role',
      render: (row) => row.role_label || getRoleLabel(row.portal_role),
    },
    { key: 'designation', label: 'Designation', accessor: 'designation' },
    { key: 'department_name', label: 'Department', accessor: 'department_name' },
    { key: 'email', label: 'Work Email', accessor: 'email', width: '16%' },
    {
      key: 'portal',
      label: 'Portal',
      width: '7%',
      truncate: false,
      render: (row) => (
        row.has_user_account
          ? <span className="badge text-bg-success-subtle border text-success">Active</span>
          : <span className="badge text-bg-secondary-subtle border text-muted">No account</span>
      ),
    },
    { key: 'status', label: 'Status', width: '7%', truncate: false, render: (row) => <StatusBadge status={row.status} /> },
    ...(canManage ? [{
      key: 'actions',
      label: '',
      truncate: false,
      render: (row) => (
        <div className="apex-table-row-actions">
          <button
            type="button"
            className="btn btn-sm btn-outline-primary"
            title="Edit staff profile"
            onClick={(e) => { e.stopPropagation(); navigate(`/school-admin/hr/staffs/${row.id}`); }}
          >
            <FiEdit2 size={14} />
          </button>
        </div>
      ),
    }] : []),
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
        subtitle="Bulk import hiring essentials via CSV, or add staff one at a time — HR completes full profiles later"
        actions={canManage && (
          <div className="d-flex flex-wrap gap-2">
            <button type="button" className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1" onClick={() => setShowImport(true)}>
              <FiUpload size={16} /> Import CSV
            </button>
            <Link to="/school-admin/hr/staffs/new" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1">
              <FiPlus size={16} /> Add Staff
            </Link>
          </div>
        )}
      />

      {isError ? (
        <div className="alert alert-danger">Unable to load staff records.</div>
      ) : (
        <DataTable
            columns={columns}
            data={staffList}
            loading={isLoading}
            onRowClick={canManage ? (row) => navigate(`/school-admin/hr/staffs/${row.id}`) : undefined}
            emptyState={(
              <ModuleEmptyState
                title="No staff yet"
                description="Add one staff member at a time, or import many using the minimal CSV template."
                actionLabel={canManage ? 'Add Staff' : undefined}
                onAction={canManage ? () => navigate('/school-admin/hr/staffs/new') : undefined}
              />
            )}
          />
      )}
      <BulkImportWizard
        show={showImport}
        onHide={() => setShowImport(false)}
        title="Import Staff"
        description="Five columns only: name, work email, phone, and date joined."
        profileNote="Imported staff get basic records only. HR should open each profile to set role, department, and portal access."
        importService={staffBulkImport}
        onSuccess={(result) => {
          notify.success(result?.message || 'Staff imported successfully.');
          queryClient.invalidateQueries({ queryKey: ['staff'] });
        }}
      />
    </div>
  );
}

export default HRStaffs;