import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiCheck, FiX } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { hrApprovalService, leavesService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';
import { extractApiError, notify } from '../../utils/notify';
import { ApexLoader } from '../../components/ApexLoader';

export function HRApproval() {
  const queryClient = useQueryClient();
  const { canWriteFeature } = usePermissions();
  const canApprove = canWriteFeature('leave_requests');
  const [selected, setSelected] = useState([]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['hr-approval-queue'],
    queryFn: () => hrApprovalService.getQueue(),
    staleTime: 15_000,
  });

  const leaves = data?.leaves || [];
  const count = data?.count ?? leaves.length;

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ['hr-approval-queue'] });
    await queryClient.invalidateQueries({ queryKey: ['hr-workspace'] });
    setSelected([]);
  };

  const toggle = (id) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const approveOne = async (id) => {
    try {
      await leavesService.approve(id);
      notify.success('Leave approved.');
      await invalidate();
    } catch (err) {
      notify.error(extractApiError(err, 'Approval failed.'));
    }
  };

  const rejectOne = async (id) => {
    try {
      await leavesService.reject(id, { reason: 'Rejected by HR manager' });
      notify.success('Leave rejected.');
      await invalidate();
    } catch (err) {
      notify.error(extractApiError(err, 'Rejection failed.'));
    }
  };

  const bulkAction = async (action) => {
    if (!selected.length) return;
    try {
      await hrApprovalService.bulkAction({ action, leave_ids: selected });
      notify.success(`Leave requests ${action}d.`);
      await invalidate();
    } catch (err) {
      notify.error(extractApiError(err, 'Bulk action failed.'));
    }
  };

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/hr" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> Human Resources
        </Link>
      </div>

      <PageHeader
        title="Leave Approval"
        subtitle={`${count} leave request(s) awaiting review`}
        actions={canApprove && selected.length > 0 && (
          <div className="d-flex gap-2">
            <button type="button" className="btn btn-success btn-sm" onClick={() => bulkAction('approve')}>
              Approve selected ({selected.length})
            </button>
            <button type="button" className="btn btn-outline-danger btn-sm" onClick={() => bulkAction('reject')}>
              Reject selected
            </button>
          </div>
        )}
      />

      {isError && <div className="alert alert-danger">Unable to load leave approval queue.</div>}

      {isLoading ? (
        <div className="py-5 text-center"><ApexLoader label="Loading…" /></div>
      ) : count === 0 ? (
        <div className="apex-card p-5">
          <ModuleEmptyState title="No pending leave requests" message="Staff leave submissions will appear here for approval." />
        </div>
      ) : (
        <div className="apex-card p-3 p-md-4">
          <div className="table-responsive">
            <table className="table table-hover mb-0 align-middle">
              <thead className="table-light">
                <tr>
                  {canApprove && <th style={{ width: 40 }} />}
                  <th>Staff</th>
                  <th>Type</th>
                  <th>From</th>
                  <th>To</th>
                  <th>Days</th>
                  <th>Reason</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {leaves.map((row) => (
                  <tr key={row.id}>
                    {canApprove && (
                      <td>
                        <input
                          type="checkbox"
                          className="form-check-input"
                          checked={selected.includes(row.id)}
                          onChange={() => toggle(row.id)}
                        />
                      </td>
                    )}
                    <td>{row.staff}</td>
                    <td>{row.leave_type}</td>
                    <td>{row.start_date}</td>
                    <td>{row.end_date}</td>
                    <td>{row.days}</td>
                    <td className="small text-muted">{row.reason}</td>
                    <td>
                      {canApprove && (
                        <div className="d-flex gap-1">
                          <button type="button" className="btn btn-sm btn-success" onClick={() => approveOne(row.id)}>
                            <FiCheck size={14} />
                          </button>
                          <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => rejectOne(row.id)}>
                            <FiX size={14} />
                          </button>
                        </div>
                      )}
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

export default HRApproval;