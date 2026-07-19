import { useTenantContext } from '../context/TenantContext';
import { CORE_FEATURE_KEYS } from '../config/navigation';
import UpgradeRequired from '../pages/shared/UpgradeRequired';
import AccessDenied from '../pages/shared/AccessDenied';
import { PageLoader } from './ApexLoader';

export function FeatureGate({ featureKey, featureKeys, children }) {
  const { isFeatureEnabled, canAccessFeature, isSchoolAdmin, loading } = useTenantContext();
  const keys = (featureKeys?.length ? featureKeys : (featureKey ? [featureKey] : []));

  if (loading) {
    return <PageLoader label="Loading…" />;
  }

  if (!keys.length || keys.some((k) => CORE_FEATURE_KEYS.includes(k))) {
    return children;
  }

  if (!isSchoolAdmin && !keys.some((k) => canAccessFeature(k, false))) {
    return <AccessDenied message={`Your role does not have permission to access this area. Contact your school admin to update Permission Settings.`} />;
  }

  if (keys.some((k) => isFeatureEnabled(k))) {
    return children;
  }

  return <UpgradeRequired featureKey={keys[0]} />;
}

export default FeatureGate;