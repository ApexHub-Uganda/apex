import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiLink, FiX } from 'react-icons/fi';
import WorkspaceShell from '../../components/WorkspaceShell';
import ParentForm from '../../components/ParentForm';
import UserDeleteDangerZone from '../../components/UserDeleteDangerZone';
import { usePermissions } from '../../hooks/usePermissions';
import DataTable from '../../components/DataTable';
import StatusBadge from '../../components/StatusBadge';
import { parentsService, studentsService } from '../../services/moduleService';
import { extractApiError, notify } from '../../utils/notify';

export function ParentWorkspace() {
  const { parentId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isEdit = Boolean(parentId && parentId !== 'new');
  const { canReadDeleteUser, canWriteDeleteUser } = usePermissions();
  const [studentSearch, setStudentSearch] = useState('');
  const [linking, setLinking] = useState(false);

  const { data: parent, isLoading, isError } = useQuery({
    queryKey: ['parents', parentId],
    queryFn: () => parentsService.get(parentId),
    enabled: isEdit,
  });

  const { data: students = [] } = useQuery({
    queryKey: ['students'],
    queryFn: () => studentsService.list(),
    enabled: isEdit,
  });

  const invalidateParentData = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['parents'] }),
      queryClient.invalidateQueries({ queryKey: ['parents', parentId] }),
      queryClient.invalidateQueries({ queryKey: ['parent-matching-summary'] }),
      queryClient.invalidateQueries({ queryKey: ['students'] }),
    ]);
  };

  const handleDeleteParent = async () => {
    await parentsService.delete(parentId);
    notify.success('Parent record deleted.');
    await invalidateParentData();
    navigate('/school-admin/parents');
  };

  const handleSubmit = async (formData) => {
    try {
      if (isEdit) {
        await parentsService.update(parentId, formData);
        notify.success('Parent record updated.');
      } else {
        await parentsService.create(formData);
        notify.success('Parent added successfully.');
      }
      await invalidateParentData();
      navigate('/school-admin/parents');
    } catch (err) {
      notify.error(extractApiError(err, isEdit ? 'Unable to update parent.' : 'Unable to add parent.'));
      throw err;
    }
  };

  const handleLinkStudent = async (studentId) => {
    setLinking(true);
    try {
      await parentsService.linkStudent(parentId, studentId);
      notify.success('Learner linked.');
      await invalidateParentData();
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to link learner.'));
    } finally {
      setLinking(false);
    }
  };

  const handleUnlinkStudent = async (studentId) => {
    setLinking(true);
    try {
      await parentsService.unlinkStudent(parentId, studentId);
      notify.success('Learner unlinked.');
      await invalidateParentData();
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to unlink learner.'));
    } finally {
      setLinking(false);
    }
  };

  const linkedIds = new Set((parent?.children || []).map((c) => c.id));
  const q = studentSearch.trim().toLowerCase();
  const linkableStudents = students.filter((s) => {
    if (linkedIds.has(s.id)) return false;
    if (!q) return true;
    const hay = `${s.full_name || ''} ${s.admission_number || ''}`.toLowerCase();
    return hay.includes(q);
  });

  if (isEdit && isLoading) {
    return <div className="py-5 text-center"><div className="spinner-border text-primary" role="status" /></div>;
  }

  if (isEdit && isError) {
    return (
      <WorkspaceShell backTo="/school-admin/parents" backLabel="Parents" title="Parent not found">
        <div className="alert alert-danger">Unable to load this parent record.</div>
      </WorkspaceShell>
    );
  }

  return (
    <WorkspaceShell
      backTo="/school-admin/parents"
      backLabel="Parents"
      title={isEdit ? `Edit ${parent?.full_name || 'Parent'}` : 'Add Parent / Guardian'}
      subtitle={isEdit
        ? 'Update contact details and manage learner links for this guardian'
        : 'Contact details, mobile money number, and fee payer designation'}
    >
      <ParentForm
        key={parentId || 'new'}
        mode={isEdit ? 'edit' : 'create'}
        initialValues={isEdit ? parent : undefined}
        onSubmit={handleSubmit}
        submitLabel={isEdit ? 'Save parent profile' : 'Add parent'}
      />

      {isEdit && (
        <div className="apex-card p-3 p-md-4 mt-4">
          <h6 className="fw-bold mb-3">Learner Matching</h6>
          <div className="row g-4">
            <div className="col-lg-6">
              <label className="form-label small fw-medium">Search learners to link</label>
              <input
                type="search"
                className="form-control mb-2"
                placeholder="Name or admission number…"
                value={studentSearch}
                onChange={(e) => setStudentSearch(e.target.value)}
              />
              <div className="list-group" style={{ maxHeight: 240, overflowY: 'auto' }}>
                {linkableStudents.slice(0, 15).map((s) => (
                  <div key={s.id} className="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                      <div className="fw-medium">{s.full_name}</div>
                      <div className="small text-muted">{s.admission_number}</div>
                    </div>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-primary"
                      disabled={linking}
                      onClick={() => handleLinkStudent(s.id)}
                    >
                      <FiLink size={14} /> Link
                    </button>
                  </div>
                ))}
                {linkableStudents.length === 0 && (
                  <div className="list-group-item text-muted small">No learners available to link.</div>
                )}
              </div>
            </div>
            <div className="col-lg-6">
              <DataTable
                columns={[
                  { key: 'admission_number', label: 'Admission No.', accessor: 'admission_number' },
                  { key: 'full_name', label: 'Learner', accessor: 'full_name' },
                  { key: 'class_name', label: 'Class', accessor: 'class_name' },
                  {
                    key: 'status',
                    label: 'Status',
                    render: (row) => (row.status ? <StatusBadge status={row.status} /> : '—'),
                  },
                  {
                    key: 'actions',
                    label: '',
                    render: (row) => (
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-danger"
                        disabled={linking}
                        onClick={() => handleUnlinkStudent(row.id)}
                      >
                        <FiX size={14} />
                      </button>
                    ),
                  },
                ]}
                data={parent?.children || []}
                emptyState={<p className="text-muted small mb-0">No learners linked to this parent yet.</p>}
              />
            </div>
          </div>
        </div>
      )}

      {isEdit && (
        <UserDeleteDangerZone
          entityLabel="parent"
          recordName={parent?.full_name}
          description="Permanently remove this parent or guardian from the school directory. Learner links will be removed."
          onDelete={handleDeleteParent}
          canRead={canReadDeleteUser('parent_management')}
          canWrite={canWriteDeleteUser('parent_management')}
        />
      )}
    </WorkspaceShell>
  );
}

export default ParentWorkspace;