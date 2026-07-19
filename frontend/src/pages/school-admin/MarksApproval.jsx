import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiCheck, FiLock } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { marksApprovalService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';
import { ApexLoader } from '../../components/ApexLoader';

export function MarksApproval() {
  const queryClient = useQueryClient();
  const { canWriteFeature } = usePermissions();
  const canApprove = canWriteFeature('marks_approval');
  const [selected, setSelected] = useState(new Set());
  const [busy, setBusy] = useState(false);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['marks-approval-queue'],
    queryFn: () => marksApprovalService.getQueue(),
    staleTime: 15_000,
  });

  const results = data?.results || [];
  const count = data?.count ?? results.length;

  const toggle = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === results.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(results.map((r) => r.id)));
    }
  };

  const runBulk = async (action) => {
    if (!selected.size) {
      notify.warning('Select at least one exam.');
      return;
    }
    setBusy(true);
    try {
      const result = await marksApprovalService.bulkAction({
        action,
        exam_ids: [...selected],
      });
      if (result?.errors?.length) {
        notify.warning(result.message || 'Some items could not be processed.');
      } else {
        notify.success(result?.message || 'Done.');
      }
      setSelected(new Set());
      await queryClient.invalidateQueries({ queryKey: ['marks-approval-queue'] });
      await queryClient.invalidateQueries({ queryKey: ['academic-workspace'] });
      await refetch();
    } catch (err) {
      notify.error(extractApiError(err, 'Action failed.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/examinations" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Examinations
        </Link>
      </div>

      <PageHeader
        title="Marks Approval"
        subtitle={`${count} exam(s) awaiting review`}
        actions={canApprove && (
          <div className="d-flex gap-2">
            <button
              type="button"
              className="btn btn-success btn-sm d-inline-flex align-items-center gap-1"
              disabled={busy || !selected.size}
              onClick={() => runBulk('approve')}
            >
              <FiCheck size={14} /> Approve selected
            </button>
            <button
              type="button"
              className="btn btn-dark btn-sm d-inline-flex align-items-center gap-1"
              disabled={busy || !selected.size}
              onClick={() => runBulk('lock')}
            >
              <FiLock size={14} /> Lock selected
            </button>
          </div>
        )}
      />

      {isError && (
        <div className="alert alert-danger">Unable to load approval queue.</div>
      )}

      {isLoading ? (
        <div className="py-5 text-center"><ApexLoader label="Loading…" /></div>
      ) : results.length === 0 ? (
        <div className="apex-card p-5">
          <ModuleEmptyState
            title="No marks pending approval"
            message="Submitted mark sheets from teachers will appear here for HoD or DoS review."
          />
        </div>
      ) : (
        <div className="apex-card p-0 overflow-hidden">
          <div className="table-responsive">
            <table className="table table-hover mb-0 align-middle">
              <thead className="table-light">
                <tr>
                  {canApprove && (
                    <th style={{ width: 40 }}>
                      <input
                        type="checkbox"
                        className="form-check-input"
                        checked={selected.size === results.length && results.length > 0}
                        onChange={toggleAll}
                        aria-label="Select all"
                      />
                    </th>
                  )}
                  <th>Exam</th>
                  <th>Subject</th>
                  <th>Class</th>
                  <th>Term</th>
                  <th>Grades</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {results.map((row) => (
                  <tr key={row.id}>
                    {canApprove && (
                      <td>
                        <input
                          type="checkbox"
                          className="form-check-input"
                          checked={selected.has(row.id)}
                          onChange={() => toggle(row.id)}
                          aria-label={`Select ${row.name}`}
                        />
                      </td>
                    )}
                    <td className="fw-medium">{row.name}</td>
                    <td>{row.subject_name}</td>
                    <td>{row.school_class_name}</td>
                    <td>{row.term_name}</td>
                    <td>{row.grade_count ?? '—'}</td>
                    <td>
                      <span className="badge text-bg-warning-subtle border text-warning">
                        {row.marks_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default MarksApproval;