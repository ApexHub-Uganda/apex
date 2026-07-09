import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowRight, FiBookOpen, FiRotateCcw } from 'react-icons/fi';
import WorkspaceShell, { WorkspaceSection } from '../../components/WorkspaceShell';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { libraryWorkspaceService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';

function StatTile({ label, value, accent = 'primary' }) {
  return (
    <div className={`apex-card p-3 border-start border-3 border-${accent}`}>
      <div className="text-muted small">{label}</div>
      <div className="fs-4 fw-bold">{value ?? 0}</div>
    </div>
  );
}

export function LibraryRoleWorkspace({
  title,
  subtitle,
  backTo = '/school-admin/library',
  backLabel = 'Library',
  featureKey,
}) {
  const { canReadFeature } = usePermissions();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['library-workspace', featureKey],
    queryFn: () => libraryWorkspaceService.get(),
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
        <div className="alert alert-danger">Unable to load library workspace.</div>
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
        {counts.total_books != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Books in catalog" value={counts.total_books} />
          </div>
        )}
        {counts.active_borrows != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Active borrows" value={counts.active_borrows} accent="info" />
          </div>
        )}
        {counts.overdue_borrows != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Overdue" value={counts.overdue_borrows} accent="warning" />
          </div>
        )}
        {counts.pending_reservations != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Reservations" value={counts.pending_reservations} accent="success" />
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

      {queues.overdue_borrows?.length > 0 && canReadFeature('returns') && (
        <WorkspaceSection title="Overdue returns" icon={FiRotateCcw} className="mb-4">
          <Link to="/school-admin/library/returns" className="btn btn-link btn-sm px-0">
            Process returns <FiArrowRight size={14} />
          </Link>
        </WorkspaceSection>
      )}

      {queues.pending_reservations?.length > 0 && canReadFeature('reservations') && (
        <WorkspaceSection title="Pending reservations" icon={FiBookOpen}>
          <Link to="/school-admin/library/reservations" className="btn btn-link btn-sm px-0">
            View reservations <FiArrowRight size={14} />
          </Link>
        </WorkspaceSection>
      )}

      {!quickLinks.length && !queues.overdue_borrows?.length && !queues.pending_reservations?.length && (
        <div className="apex-card p-4">
          <ModuleEmptyState
            title="Library workspace ready"
            message="Use the sidebar to access your permitted library tools."
            icon={FiBookOpen}
          />
        </div>
      )}
    </WorkspaceShell>
  );
}

export default LibraryRoleWorkspace;