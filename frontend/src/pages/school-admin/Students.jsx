import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiPlus, FiUpload } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import StudentBulkImportWizard from '../../components/StudentBulkImportWizard';
import IncompleteProfileBanner from '../../components/IncompleteProfileBanner';
import { studentsService } from '../../services/moduleService';
import { studentBulkImport } from '../../services/bulkImportService';
import { useAuth } from '../../hooks/useAuth';
import { usePermissions } from '../../hooks/usePermissions';
import { notify } from '../../utils/notify';
import TableCategoryFilters from '../../components/TableCategoryFilters';
import { useTableCategoryFilters } from '../../hooks/useTableCategoryFilters';
import { STUDENT_DIRECTORY_FILTERS } from '../../config/directoryTableFilters';
import { buildStudentDirectoryColumns } from '../../config/directoryTableColumns.jsx';

export function Students() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isSchoolAdmin } = useAuth();
  const { canWriteModule, canWriteFeature } = usePermissions();
  const canManage = canWriteModule('student_management') || canWriteModule('core_management');
  const { data: importContext } = useQuery({
    queryKey: ['student-import-context'],
    queryFn: () => studentsService.getImportContext(),
    staleTime: 60_000,
  });
  const canWriteEnrollment = canWriteFeature('student_management') || canWriteFeature('class_teacher_tools');
  const canEnroll = isSchoolAdmin || Boolean(importContext?.can_enroll_students && canWriteEnrollment);
  const [showImport, setShowImport] = useState(false);

  const { data: listPayload, isLoading, isError } = useQuery({
    queryKey: ['students'],
    queryFn: () => studentsService.listWithMeta(),
  });

  const students = listPayload?.records || [];
  const {
    values: filterValues,
    setFilter,
    clearFilters,
    filteredRows: filteredStudents,
    activeCount: activeFilterCount,
  } = useTableCategoryFilters(students, STUDENT_DIRECTORY_FILTERS);
  const incompleteCount = useMemo(() => {
    if (listPayload?.meta?.incomplete_profile_count != null) {
      return listPayload.meta.incomplete_profile_count;
    }
    return students.filter((row) => row.is_profile_incomplete).length;
  }, [listPayload, students]);

  const columns = useMemo(
    () => buildStudentDirectoryColumns({ canManage, navigate }),
    [canManage, navigate],
  );

  return (
    <div>
      <PageHeader
        title="Students"
        subtitle="Bulk import by class or stream with name and sex (M/F) — complete full profiles later"
        actions={canEnroll && (
          <div className="d-flex flex-wrap gap-2">
            <button type="button" className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1" onClick={() => setShowImport(true)}>
              <FiUpload size={16} /> Import Excel
            </button>
            <Link to="/school-admin/students/new" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1">
              <FiPlus size={16} /> Add Student
            </Link>
          </div>
        )}
      />

      <IncompleteProfileBanner count={incompleteCount} />

      {isError ? (
        <div className="alert alert-danger">Unable to load student records.</div>
      ) : (
        <DataTable
          columns={columns}
          data={filteredStudents}
          loading={isLoading}
          searchPlaceholder="Search students…"
          filters={(
            <TableCategoryFilters
              data={students}
              filterDefs={STUDENT_DIRECTORY_FILTERS}
              values={filterValues}
              onChange={setFilter}
              onClear={clearFilters}
              activeCount={activeFilterCount}
            />
          )}
          onRowClick={canManage ? (row) => navigate(`/school-admin/students/${row.id}`) : undefined}
          emptyState={(
            <ModuleEmptyState
              title="No students yet"
              description="Import students by class or stream using the minimal Excel template, or add one at a time."
              actionLabel={canEnroll ? 'Add Student' : undefined}
              onAction={canEnroll ? () => navigate('/school-admin/students/new') : undefined}
            />
          )}
        />
      )}

      <StudentBulkImportWizard
        show={showImport}
        onHide={() => setShowImport(false)}
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