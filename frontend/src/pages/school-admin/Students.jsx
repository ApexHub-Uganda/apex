import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiEdit2, FiPlus, FiUpload } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import StatusBadge from '../../components/StatusBadge';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import BulkImportWizard from '../../components/BulkImportWizard';
import { studentsService } from '../../services/moduleService';
import { studentBulkImport } from '../../services/bulkImportService';
import { usePermissions } from '../../hooks/usePermissions';
import { PersonNameCell } from '../../components/PersonAvatar';
import { notify } from '../../utils/notify';

export function Students() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { canWriteModule } = usePermissions();
  const canManage = canWriteModule('student_management') || canWriteModule('core_management');
  const [showImport, setShowImport] = useState(false);

  const { data: students = [], isLoading, isError } = useQuery({
    queryKey: ['students'],
    queryFn: () => studentsService.list(),
  });

  const columns = [
    { key: 'admission_number', label: 'Admission No', accessor: 'admission_number', sortable: true },
    {
      key: 'full_name',
      label: 'Name',
      accessor: 'full_name',
      sortable: true,
      render: (row) => <PersonNameCell row={row} />,
    },
    { key: 'class_name', label: 'Class', accessor: 'class_name' },
    { key: 'stream_name', label: 'Stream', accessor: 'stream_name' },
    { key: 'upi_number', label: 'UPI', accessor: 'upi_number' },
    { key: 'county', label: 'County', accessor: 'county' },
    {
      key: 'boarding_status',
      label: 'Boarding',
      render: (row) => {
        const labels = { day: 'Day', boarding: 'Boarding', weekly: 'Weekly' };
        return labels[row.boarding_status] || row.boarding_status || '—';
      },
    },
    { key: 'parent_names', label: 'Parents', accessor: 'parent_names' },
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
            title="Edit student"
            onClick={(e) => { e.stopPropagation(); navigate(`/school-admin/students/${row.id}`); }}
          >
            <FiEdit2 size={14} />
          </button>
        </div>
      ),
    }] : []),
  ];

  return (
    <div>
      <PageHeader
        title="Students"
        subtitle="Bulk import essentials via CSV, or add students one at a time — class teachers complete full profiles later"
        actions={canManage && (
          <div className="d-flex flex-wrap gap-2">
            <button type="button" className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1" onClick={() => setShowImport(true)}>
              <FiUpload size={16} /> Import CSV
            </button>
            <Link to="/school-admin/students/new" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1">
              <FiPlus size={16} /> Add Student
            </Link>
          </div>
        )}
      />

      {isError ? (
        <div className="alert alert-danger">Unable to load student records.</div>
      ) : (
        <DataTable
            columns={columns}
            data={students}
            loading={isLoading}
            onRowClick={canManage ? (row) => navigate(`/school-admin/students/${row.id}`) : undefined}
            emptyState={(
              <ModuleEmptyState
                title="No students yet"
                description="Add a student one at a time, or import many via the minimal CSV template."
                actionLabel={canManage ? 'Add Student' : undefined}
                onAction={canManage ? () => navigate('/school-admin/students/new') : undefined}
              />
            )}
          />
      )}

      <BulkImportWizard
        show={showImport}
        onHide={() => setShowImport(false)}
        title="Import Students"
        description="Six columns only: admission number, name, date of birth, gender, and class code."
        profileNote="Imported students get basic enrollment only. Class teachers should open each profile to add UPI, parents, boarding, and other details."
        importService={studentBulkImport}
        onSuccess={(result) => {
          notify.success(result?.message || 'Students imported successfully.');
          queryClient.invalidateQueries({ queryKey: ['students'] });
        }}
      />
    </div>
  );
}

export default Students;