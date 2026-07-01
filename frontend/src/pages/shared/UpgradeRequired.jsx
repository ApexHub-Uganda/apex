import { FiLock, FiTrendingUp } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';

export function UpgradeRequired({ featureKey }) {
  const label = featureKey?.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) || 'This feature';

  return (
    <div>
      <PageHeader title="Feature Not Available" subtitle="Upgrade your subscription to unlock this capability" />
      <div className="apex-card p-5 text-center" style={{ maxWidth: 560, margin: '0 auto' }}>
        <div
          className="d-inline-flex align-items-center justify-content-center mb-4"
          style={{
            width: 72, height: 72, borderRadius: 16,
            background: 'rgba(245, 158, 11, 0.12)', color: '#D97706', fontSize: '1.75rem',
          }}
        >
          <FiLock />
        </div>
        <h4 className="fw-bold mb-2">{label}</h4>
        <p className="text-muted mb-4">
          This module is not on your current plan. Upgrade to unlock it, or use the modules
          already included in your subscription from the sidebar.
        </p>
        <button type="button" className="btn btn-primary d-inline-flex align-items-center gap-2" disabled>
          <FiTrendingUp /> Request Plan Upgrade
        </button>
      </div>
    </div>
  );
}

export default UpgradeRequired;