import { useTenantContext } from '../context/TenantContext';
import { CORE_FEATURE_KEYS } from '../config/navigation';
import UpgradeRequired from '../pages/shared/UpgradeRequired';

export function FeatureGate({ featureKey, children }) {
  const { isFeatureEnabled, loading } = useTenantContext();

  if (loading) {
    return (
      <div className="d-flex justify-content-center py-5">
        <div className="spinner-border text-primary" role="status" />
      </div>
    );
  }

  if (!featureKey || CORE_FEATURE_KEYS.includes(featureKey) || isFeatureEnabled(featureKey)) {
    return children;
  }

  return <UpgradeRequired featureKey={featureKey} />;
}

export default FeatureGate;