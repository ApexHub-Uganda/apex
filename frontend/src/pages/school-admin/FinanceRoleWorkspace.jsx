import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiArrowRight, FiDollarSign } from 'react-icons/fi';
import WorkspaceShell, { WorkspaceSection } from '../../components/WorkspaceShell';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { financeWorkspaceService } from '../../services/moduleService';
import { usePermissions } from '../../hooks/usePermissions';

function StatTile({ label, value, accent = 'primary' }) {
  return (
    <div className={`apex-card p-3 border-start border-3 border-${accent}`}>
      <div className="text-muted small">{label}</div>
      <div className="fs-4 fw-bold">{value ?? 0}</div>
    </div>
  );
}

export function FinanceRoleWorkspace({
  title,
  subtitle,
  backTo = '/school-admin/finance',
  backLabel = 'Finance',
  featureKey,
}) {
  const { canReadFeature } = usePermissions();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['finance-workspace', featureKey],
    queryFn: () => financeWorkspaceService.get(),
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
        <div className="alert alert-danger">Unable to load finance workspace.</div>
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
        {counts.outstanding_debtors != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Debtors" value={counts.outstanding_debtors} accent="warning" />
          </div>
        )}
        {counts.pending_approval != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Pending approval" value={counts.pending_approval} accent="info" />
          </div>
        )}
        {counts.open_invoices != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Open invoices" value={counts.open_invoices} />
          </div>
        )}
        {counts.total_collected != null && (
          <div className="col-6 col-md-3">
            <StatTile label="Total collected" value={counts.total_collected} accent="success" />
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

      {queues.pending_payments?.length > 0 && canReadFeature('transaction_approval') && (
        <WorkspaceSection title="Payments awaiting approval" icon={FiDollarSign}>
          <Link to="/school-admin/finance/approval" className="btn btn-link btn-sm px-0">
            Open approval queue <FiArrowRight size={14} />
          </Link>
        </WorkspaceSection>
      )}

      {!quickLinks.length && (
        <div className="apex-card p-4">
          <ModuleEmptyState
            title="Finance workspace ready"
            message="Use the sidebar to access your permitted finance tools."
            icon={FiDollarSign}
          />
        </div>
      )}
    </WorkspaceShell>
  );
}

export default FinanceRoleWorkspace;