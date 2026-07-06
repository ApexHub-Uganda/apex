import { useTenantContext } from '../context/TenantContext';
import { CORE_FEATURE_KEYS } from '../config/navigation';
import UpgradeRequired from '../pages/shared/UpgradeRequired';
import AccessDenied from '../pages/shared/AccessDenied';

export function FeatureGate({ featureKey, children }) {
  const { isFeatureEnabled, canAccessFeature, isSchoolAdmin, loading } = useTenantContext();

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

  if (!isSchoolAdmin && !canAccessFeature(featureKey, false)) {
    return <AccessDenied message={`Your role does not have permission to access this area. Contact your school admin to update Permission Settings.`} />;
  }

  if (isFeatureEnabled(featureKey)) {
    return children;
  }

  return <UpgradeRequired featureKey={featureKey} />;
}

export default FeatureGate;