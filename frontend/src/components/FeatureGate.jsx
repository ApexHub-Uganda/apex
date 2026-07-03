import { useTenantContext } from '../context/TenantContext';
import { CORE_FEATURE_KEYS } from '../config/navigation';
import { getModuleKeyForFeature } from '../config/schoolModules';
import UpgradeRequired from '../pages/shared/UpgradeRequired';
import AccessDenied from '../pages/shared/AccessDenied';

export function FeatureGate({ featureKey, children }) {
  const { isFeatureEnabled, canAccessModule, isSchoolAdmin, loading } = useTenantContext();

  if (loading) {
    return (
      <div className="d-flex justify-content-center py-5">
        <div className="spinner-border text-primary" role="status" />
      </div>
    );
  }

  if (!featureKey || CORE_FEATURE_KEYS.includes(featureKey)) {
    return children;
  }

  const moduleKey = getModuleKeyForFeature(featureKey);
  if (!isSchoolAdmin && moduleKey && !canAccessModule(moduleKey, false)) {
    return <AccessDenied moduleKey={moduleKey} />;
  }

  if (isFeatureEnabled(featureKey)) {
    return children;
  }

  return <UpgradeRequired featureKey={featureKey} />;
}

export default FeatureGate;