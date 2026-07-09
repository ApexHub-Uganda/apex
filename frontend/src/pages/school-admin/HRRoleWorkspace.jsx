import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowRight, FiCalendar, FiUsers } from 'react-icons/fi';
import WorkspaceShell, { WorkspaceSection } from '../../components/WorkspaceShell';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { hrWorkspaceService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';

function StatTile({ label, value, accent = 'primary' }) {
  return (
    <div className={`apex-card p-3 border-start border-3 border-${accent}`}>
      <div className="text-muted small">{label}</div>
      <div className="fs-4 fw-bold">{value ?? 0}</div>
    </div>
  );
}

export function HRRoleWorkspace({
  title,
  subtitle,
  backTo = '/school-admin/hr',
  backLabel = 'Human Resources',
  featureKey,
}) {
  const { canReadFeature } = usePermissions();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['hr-workspace', featureKey],
    queryFn: () => hrWorkspaceService.get(),
    staleTime: 30_000,
  });

  const counts = data?.counts || {};
  const queues = data?.queues || {};
  const quickLinks = (data?.quick_links || []).filter((link) => canReadFeature(link.feature_key));

  if (isLoading) {
    return (
      <div className="py-5 text-center">
        <div className="spinner-border text-primary" role="status" />
      </div>
    );
  }

  if (isError) {
    return (
      <WorkspaceShell backTo={backTo} backLabel={backLabel} title={title} subtitle={subtitle}>
        <div className="alert alert-danger">Unable to load HR workspace.</div>
      </WorkspaceShell>
    );
  }

  return (
    <WorkspaceShell
      backTo={backTo}
      backLabel={backLabel}
      title={title}
      subtitle={subtitle}
      actions={(
        <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => refetch()}>
          Refresh
        </button>
      )}
    >
      <div className="row g-3 mb-4">
        {counts.staff_count != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Staff" value={counts.staff_count} />
          </div>
        )}
        {counts.pending_leave != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Pending leave" value={counts.pending_leave} accent="warning" />
          </div>
        )}
        {counts.pending_reviews != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Pending reviews" value={counts.pending_reviews} accent="info" />
          </div>
        )}
        {counts.departments != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Departments" value={counts.departments} accent="success" />
          </div>
        )}
      </div>

      {quickLinks.length > 0 && (
        <WorkspaceSection title="Quick actions" icon={FiArrowRight} className="mb-4">
          <div className="d-flex flex-wrap gap-2">
            {quickLinks.map((link) => (
              <Link key={link.path} to={link.path} className="btn btn-outline-primary btn-sm">
                {link.label}
              </Link>
            ))}
          </div>
        </WorkspaceSection>
      )}

      {queues.pending_leave_requests?.length > 0 && canReadFeature('leave_requests') && (
        <WorkspaceSection title="Leave requests awaiting approval" icon={FiCalendar}>
          <Link to="/school-admin/hr/leave" className="btn btn-link btn-sm px-0">
            Open leave queue <FiArrowRight size={14} />
          </Link>
        </WorkspaceSection>
      )}

      {!quickLinks.length && !queues.pending_leave_requests?.length && (
        <div className="apex-card p-4">
          <ModuleEmptyState
            title="HR workspace ready"
            message="Use the sidebar to access your permitted HR tools."
            icon={FiUsers}
          />
        </div>
      )}
    </WorkspaceShell>
  );
}

export default HRRoleWorkspace;