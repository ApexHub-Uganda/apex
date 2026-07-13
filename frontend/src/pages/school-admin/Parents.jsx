import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiLink, FiPlus, FiUpload, FiUsers, FiX } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import BulkImportWizard from '../../components/BulkImportWizard';
import StatusBadge from '../../components/StatusBadge';
import { parentsService, studentsService } from '../../services/moduleService';
import { parentBulkImport } from '../../services/bulkImportService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';
import TableCategoryFilters from '../../components/TableCategoryFilters';
import { useTableCategoryFilters } from '../../hooks/useTableCategoryFilters';
import { PARENT_DIRECTORY_FILTERS } from '../../config/directoryTableFilters';
import { buildParentDirectoryColumns } from '../../config/directoryTableColumns.jsx';
import { COL_WIDTH, nameColumn } from '../../utils/tableDisplay';
import { PersonNameCell } from '../../components/PersonAvatar';

const TABS = [
  { key: 'directory', label: 'Parent Directory' },
  { key: 'matching', label: 'Learner Matching' },
];

export function Parents() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { canWriteModule } = usePermissions();
  const canManage = canWriteModule('parent_management') || canWriteModule('core_management');
  const [showImport, setShowImport] = useState(false);
  const [activeTab, setActiveTab] = useState('directory');
  const [selectedParentId, setSelectedParentId] = useState('');
  const [studentSearch, setStudentSearch] = useState('');
  const [linking, setLinking] = useState(false);

  const { data: parents = [], isLoading, isError } = useQuery({
    queryKey: ['parents'],
    queryFn: () => parentsService.list(),
  });

  const {
    values: filterValues,
    setFilter,
    clearFilters,
    filteredRows: filteredParents,
    activeCount: activeFilterCount,
  } = useTableCategoryFilters(parents, PARENT_DIRECTORY_FILTERS);

  const { data: matchingSummary, isLoading: summaryLoading } = useQuery({
    queryKey: ['parent-matching-summary'],
    queryFn: () => parentsService.getMatchingSummary(),
  });

  const { data: selectedParent, isLoading: parentLoading } = useQuery({
    queryKey: ['parents', selectedParentId],
    queryFn: () => parentsService.get(selectedParentId),
    enabled: Boolean(selectedParentId),
  });

  const { data: students = [] } = useQuery({
    queryKey: ['students'],
    queryFn: () => studentsService.list(),
    enabled: activeTab === 'matching',
  });

  const linkedChildIds = useMemo(
    () => new Set((selectedParent?.children || []).map((c) => c.id)),
    [selectedParent],
  );

  const linkableStudents = useMemo(() => {
    const q = studentSearch.trim().toLowerCase();
    return students.filter((s) => {
      if (linkedChildIds.has(s.id)) return false;
      if (!q) return true;
      const hay = `${s.full_name || ''} ${s.admission_number || ''} ${s.class_name || ''}`.toLowerCase();
      return hay.includes(q);
    });
  }, [students, studentSearch, linkedChildIds]);

  const invalidateParentData = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['parents'] }),
      queryClient.invalidateQueries({ queryKey: ['parent-matching-summary'] }),
      queryClient.invalidateQueries({ queryKey: ['parents', selectedParentId] }),
      queryClient.invalidateQueries({ queryKey: ['students'] }),
    ]);
  };

  const handleLinkStudent = async (studentId) => {
    if (!selectedParentId) return;
    setLinking(true);
    try {
      await parentsService.linkStudent(selectedParentId, studentId);
      notify.success('Learner linked to parent.');
      await invalidateParentData();
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to link learner.'));
    } finally {
      setLinking(false);
    }
  };

  const handleUnlinkStudent = async (studentId) => {
    if (!selectedParentId) return;
    setLinking(true);
    try {
      await parentsService.unlinkStudent(selectedParentId, studentId);
      notify.success('Learner unlinked from parent.');
      await invalidateParentData();
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to unlink learner.'));
    } finally {
      setLinking(false);
    }
  };

  const columns = useMemo(
    () => buildParentDirectoryColumns({ canManage, navigate }),
    [canManage, navigate],
  );

  const childColumns = [
    { key: 'admission_number', label: 'Adm. No.', accessor: 'admission_number', width: COL_WIDTH.admission },
    nameColumn({
      key: 'full_name',
      label: 'Learner',
      accessor: 'full_name',
      sortable: true,
      render: (row) => <PersonNameCell row={row} compact />,
    }),
    { key: 'class_name', label: 'Class', accessor: 'class_name', width: COL_WIDTH.class },
    {
      key: 'status',
      label: 'Status',
      width: COL_WIDTH.status,
      truncate: false,
      render: (row) => (row.status ? <StatusBadge status={row.status} /> : '—'),
    },
    ...(canManage ? [{
      key: 'actions',
      label: '',
      truncate: false,
      render: (row) => (
        <div className="apex-table-row-actions">
          <button
            type="button"
            className="btn btn-sm btn-outline-danger"
            disabled={linking}
            onClick={() => handleUnlinkStudent(row.id)}
          >
            <FiX size={14} /> Unlink
          </button>
        </div>
      ),
    }] : []),
  ];

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/core" className="small text-decoration-none text-muted">
          ← Core Management
        </Link>
      </div>

      <PageHeader
        title="Parents & Guardians"
        subtitle="Manage parent contacts and match learners to their guardians — all links are saved to your school database"
        actions={canManage && (
          <div className="d-flex flex-wrap gap-2">
            <button type="button" className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1" onClick={() => setShowImport(true)}>
              <FiUpload size={16} /> Import Excel
            </button>
            <Link to="/school-admin/parents/new" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1">
              <FiPlus size={16} /> Add Parent
            </Link>
          </div>
        )}
      />

      <div className="row g-3 mb-4">
        {[
          { label: 'Parents', value: matchingSummary?.parent_count, icon: FiUsers },
          { label: 'Learners', value: matchingSummary?.student_count },
          { label: 'Linked Pairs', value: matchingSummary?.linked_pairs },
          { label: 'Unmatched Learners', value: matchingSummary?.unmatched_students?.length },
        ].map((stat) => (
          <div key={stat.label} className="col-6 col-lg-3">
            <div className="apex-card p-3 h-100">
              <div className="text-muted small">{stat.label}</div>
              <div className="fs-4 fw-bold">
                {summaryLoading ? '…' : (stat.value ?? '—')}
              </div>
            </div>
          </div>
        ))}
      </div>

      <ul className="nav nav-tabs mb-3">
        {TABS.map((tab) => (
          <li key={tab.key} className="nav-item">
            <button
              type="button"
              className={`nav-link ${activeTab === tab.key ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
            </button>
          </li>
        ))}
      </ul>

      {activeTab === 'directory' && (
        isError ? (
          <div className="alert alert-danger">Unable to load parent records.</div>
        ) : (
          <DataTable
            columns={columns}
            data={filteredParents}
            loading={isLoading}
            searchPlaceholder="Search parents…"
            filters={(
              <TableCategoryFilters
                data={parents}
                filterDefs={PARENT_DIRECTORY_FILTERS}
                values={filterValues}
                onChange={setFilter}
                onClear={clearFilters}
                activeCount={activeFilterCount}
              />
            )}
            onRowClick={canManage ? (row) => navigate(`/school-admin/parents/${row.id}`) : undefined}
            emptyState={(
              <ModuleEmptyState
                title="No parents yet"
                message="Add one parent at a time, or import many using the minimal Excel template."
                actionLabel={canManage ? 'Add Parent' : undefined}
                onAction={canManage ? () => navigate('/school-admin/parents/new') : undefined}
              />
            )}
          />
        )
      )}

      {activeTab === 'matching' && (
        <div className="row g-3">
          <div className="col-lg-5">
            <div className="apex-card p-3 p-md-4 h-100">
              <h6 className="fw-bold mb-3">Select Parent / Guardian</h6>
              <select
                className="form-select mb-3"
                value={selectedParentId}
                onChange={(e) => setSelectedParentId(e.target.value)}
              >
                <option value="">Choose a parent…</option>
                {parents.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.full_name || `${p.first_name} ${p.last_name}`.trim()}
                    {p.children_count ? ` (${p.children_count} linked)` : ' (no learners)'}
                  </option>
                ))}
              </select>

              {selectedParentId && (
                <div className="small text-muted mb-3">
                  <div><strong>Phone:</strong> {selectedParent?.phone || '—'}</div>
                  <div><strong>Email:</strong> {selectedParent?.email || '—'}</div>
                  <div><strong>Relationship:</strong> {selectedParent?.relationship_to_student?.replace('_', ' ') || '—'}</div>
                  {canManage && (
                    <button
                      type="button"
                      className="btn btn-link btn-sm px-0 mt-2"
                      onClick={() => navigate(`/school-admin/parents/${selectedParentId}`)}
                    >
                      Open full profile →
                    </button>
                  )}
                </div>
              )}

              <h6 className="fw-bold mb-2">Link a Learner</h6>
              <input
                type="search"
                className="form-control mb-2"
                placeholder="Search by name, admission no., or class…"
                value={studentSearch}
                onChange={(e) => setStudentSearch(e.target.value)}
                disabled={!selectedParentId || !canManage}
              />
              <div className="list-group list-group-flush" style={{ maxHeight: 280, overflowY: 'auto' }}>
                {!selectedParentId ? (
                  <div className="text-muted small py-3">Select a parent to start matching learners.</div>
                ) : linkableStudents.length === 0 ? (
                  <div className="text-muted small py-3">No available learners to link.</div>
                ) : (
                  linkableStudents.slice(0, 20).map((s) => (
                    <div key={s.id} className="list-group-item d-flex align-items-center justify-content-between px-0">
                      <div>
                        <div className="fw-medium">{s.full_name}</div>
                        <div className="small text-muted">
                          {s.admission_number}{s.class_name ? ` · ${s.class_name}` : ''}
                        </div>
                      </div>
                      {canManage && (
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-primary"
                          disabled={linking}
                          onClick={() => handleLinkStudent(s.id)}
                        >
                          <FiLink size={14} /> Link
                        </button>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="col-lg-7">
            <div className="apex-card p-3 p-md-4 h-100">
              <h6 className="fw-bold mb-3">Linked Learners</h6>
              {!selectedParentId ? (
                <ModuleEmptyState
                  title="No parent selected"
                  message="Choose a parent or guardian on the left to view and manage their linked learners."
                />
              ) : (
                <DataTable
                  columns={childColumns}
                  data={selectedParent?.children || []}
                  loading={parentLoading}
                  emptyState={(
                    <ModuleEmptyState
                      title="No learners linked"
                      message="Search and link learners using the panel on the left, or open the student profile to assign parents."
                    />
                  )}
                />
              )}
            </div>
          </div>

          {matchingSummary?.unmatched_students?.length > 0 && (
            <div className="col-12">
              <div className="apex-card p-3 p-md-4">
                <h6 className="fw-bold mb-2">Learners Without a Parent Link</h6>
                <p className="text-muted small mb-3">
                  {matchingSummary.unmatched_students.length} active learners still need at least one parent or guardian assigned.
                </p>
                <div className="d-flex flex-wrap gap-2">
                  {matchingSummary.unmatched_students.slice(0, 12).map((s) => (
                    <span key={s.id} className="badge text-bg-light border text-dark">
                      {s.full_name} ({s.admission_number})
                    </span>
                  ))}
                  {matchingSummary.unmatched_students.length > 12 && (
                    <span className="badge text-bg-secondary">
                      +{matchingSummary.unmatched_students.length - 12} more
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <BulkImportWizard
        show={showImport}
        onHide={() => setShowImport(false)}
        title="Import Parents"
        description="Parent imports use a separate template from students and staff."
        templateHint={(
          <>
            Four columns: <strong>First Name</strong>, <strong>Last Name</strong>, <strong>Email</strong>, and <strong>Phone</strong>.
            Parents with portal access can complete address and contact preferences in My Profile.
          </>
        )}
        profileNote="Mobile money numbers, addresses, and fee-payer settings can be added in each parent's full profile later."
        importService={parentBulkImport}
        onSuccess={async (result) => {
          notify.success(result?.message || 'Parents imported successfully.');
          await invalidateParentData();
        }}
      />
    </div>
  );
}

export default Parents;