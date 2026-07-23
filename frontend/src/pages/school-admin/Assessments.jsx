import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiSend } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { examsService, marksApprovalService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';
import { ApexLoader } from '../../components/ApexLoader';

export function Assessments() {
  const queryClient = useQueryClient();
  const { canWriteFeature } = usePermissions();
  const canPublish = canWriteFeature('assessment_management');
  const [selected, setSelected] = useState(new Set());
  const [busy, setBusy] = useState(false);

  const { data: exams = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['draft-assessments'],
    queryFn: () => examsService.list({ lifecycle_status: 'draft' }),
    staleTime: 15_000,
  });

  const drafts = exams.filter((e) => e.lifecycle_status === 'draft');

  const toggle = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const publishSelected = async () => {
    if (!selected.size) {
      notify.warning('Select at least one assessment.');
      return;
    }
    setBusy(true);
    try {
      const result = await marksApprovalService.bulkAction({
        action: 'publish',
        exam_ids: [...selected],
      });
      if (result?.errors?.length) {
        notify.warning(result.message || 'Some assessments could not be published.');
      } else {
        notify.success(result?.message || 'Assessments published.');
      }
      setSelected(new Set());
      await queryClient.invalidateQueries({ queryKey: ['draft-assessments'] });
      await queryClient.invalidateQueries({ queryKey: ['academic-workspace'] });
      await refetch();
    } catch (err) {
      notify.error(extractApiError(err, 'Publish failed.'));
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
        title="Assessment Management"
        subtitle="Publish draft assessments so teachers can enter marks"
        actions={canPublish && (
          <button
            type="button"
            className="btn btn-primary btn-sm d-inline-flex align-items-center gap-1"
            disabled={busy || !selected.size}
            onClick={publishSelected}
          >
            <FiSend size={14} /> Publish selected
          </button>
        )}
      />

      {isError && <div className="alert alert-danger">Unable to load assessments.</div>}

      {isLoading ? (
        <div className="py-5 text-center"><ApexLoader label="Loading…" /></div>
      ) : drafts.length === 0 ? (
        <div className="apex-card p-5">
          <ModuleEmptyState
            title="No draft assessments"
            message="Schedule exams under Examinations, then publish them here before marks entry."
            actionLabel="Schedule exams"
            actionHref="/school-admin/examinations"
          />
        </div>
      ) : (
        <div className="apex-card p-0 overflow-hidden">
          <div className="apex-sheet-scroll">
            <table className="table table-hover apex-sheet-table align-middle">
              <thead className="table-light">
                <tr>
                  {canPublish && <th style={{ width: 40 }} />}
                  <th>Name</th>
                  <th>Subject</th>
                  <th>Class</th>
                  <th>Date</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {drafts.map((row) => (
                  <tr key={row.id}>
                    {canPublish && (
                      <td>
                        <input
                          type="checkbox"
                          className="form-check-input"
                          checked={selected.has(row.id)}
                          onChange={() => toggle(row.id)}
                        />
                      </td>
                    )}
                    <td className="fw-medium">{row.name}</td>
                    <td>{row.subject_name}</td>
                    <td>{row.school_class_name}</td>
                    <td>{row.exam_date}</td>
                    <td>
                      <span className="badge text-bg-secondary-subtle border">{row.lifecycle_status}</span>
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

export default Assessments;