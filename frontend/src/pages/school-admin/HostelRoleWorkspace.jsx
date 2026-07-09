import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowRight, FiHome, FiUsers } from 'react-icons/fi';
import WorkspaceShell, { WorkspaceSection } from '../../components/WorkspaceShell';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { hostelWorkspaceService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';

function StatTile({ label, value, accent = 'primary' }) {
  return (
    <div className={`apex-card p-3 border-start border-3 border-${accent}`}>
      <div className="text-muted small">{label}</div>
      <div className="fs-4 fw-bold">{value ?? 0}</div>
    </div>
  );
}

export function HostelRoleWorkspace({
  title,
  subtitle,
  backTo = '/school-admin/hostel',
  backLabel = 'Hostels',
  featureKey,
}) {
  const { canReadFeature } = usePermissions();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['hostel-workspace', featureKey],
    queryFn: () => hostelWorkspaceService.get(),
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
        <div className="alert alert-danger">Unable to load hostel workspace.</div>
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
        {counts.total_hostels != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Hostels" value={counts.total_hostels} />
          </div>
        )}
        {counts.total_rooms != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Rooms" value={counts.total_rooms} accent="info" />
          </div>
        )}
        {counts.active_allocations != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Active allocations" value={counts.active_allocations} accent="success" />
          </div>
        )}
        {counts.vacant_beds != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Vacant beds" value={counts.vacant_beds} accent="warning" />
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

      {queues.pending_allocations?.length > 0 && canReadFeature('room_allocation') && (
        <WorkspaceSection title="Allocations needing attention" icon={FiUsers}>
          <Link to="/school-admin/hostel/allocations" className="btn btn-link btn-sm px-0">
            Open allocations <FiArrowRight size={14} />
          </Link>
        </WorkspaceSection>
      )}

      {!quickLinks.length && !queues.pending_allocations?.length && (
        <div className="apex-card p-4">
          <ModuleEmptyState
            title="Hostel workspace ready"
            message="Use the sidebar to access your permitted hostel tools."
            icon={FiHome}
          />
        </div>
      )}
    </WorkspaceShell>
  );
}

export default HostelRoleWorkspace;