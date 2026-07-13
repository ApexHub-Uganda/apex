import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiPlus, FiUpload } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';

import ModuleEmptyState from '../../components/ModuleEmptyState';
import BulkImportWizard from '../../components/BulkImportWizard';
import { staffService } from '../../services/moduleService';
import { staffBulkImport } from '../../services/bulkImportService';
import { usePermissions } from '../../hooks/usePermissions';
import { useAuth } from '../../hooks/useAuth';
import { notify } from '../../utils/notify';
import TableCategoryFilters from '../../components/TableCategoryFilters';
import { useTableCategoryFilters } from '../../hooks/useTableCategoryFilters';
import { STAFF_DIRECTORY_FILTERS } from '../../config/directoryTableFilters';
import { buildStaffDirectoryColumns } from '../../config/directoryTableColumns.jsx';

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

  const {
    values: filterValues,
    setFilter,
    clearFilters,
    filteredRows: filteredStaff,
    activeCount: activeFilterCount,
  } = useTableCategoryFilters(staffList, STAFF_DIRECTORY_FILTERS);

  const columns = useMemo(
    () => buildStaffDirectoryColumns({ canManage, navigate }),
    [canManage, navigate],
  );

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/hr" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Human Resources
        </Link>
      </div>

      <PageHeader
        title="Staffs"
        subtitle="Bulk import hiring essentials via Excel, or add staff one at a time — HR completes full profiles later"
        actions={canManage && (
          <div className="d-flex flex-wrap gap-2">
            <button type="button" className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1" onClick={() => setShowImport(true)}>
              <FiUpload size={16} /> Import Excel
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
            data={filteredStaff}
            loading={isLoading}
            searchPlaceholder="Search staff…"
            filters={(
              <TableCategoryFilters
                data={staffList}
                filterDefs={STAFF_DIRECTORY_FILTERS}
                values={filterValues}
                onChange={setFilter}
                onClear={clearFilters}
                activeCount={activeFilterCount}
              />
            )}
            onRowClick={canManage ? (row) => navigate(`/school-admin/hr/staffs/${row.id}`) : undefined}
            emptyState={(
              <ModuleEmptyState
                title="No staff yet"
                description="Add one staff member at a time, or import many using the minimal Excel template."
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
        description="Staff and teacher imports use the same minimal template."
        templateHint={(
          <>
            Four columns: <strong>First Name</strong>, <strong>Last Name</strong>, <strong>Email</strong>, and <strong>Phone</strong>.
            HR completes role, department, and portal access later; staff fill personal details in My Profile.
          </>
        )}
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