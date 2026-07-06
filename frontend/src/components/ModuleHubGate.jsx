import { useTenantContext } from '../context/TenantContext';
import { SCHOOL_MODULES } from '../config/schoolModules';
import AccessDenied from '../pages/shared/AccessDenied';
import UpgradeRequired from '../pages/shared/UpgradeRequired';

export function ModuleHubGate({ moduleKey, children }) {
  const {
    moduleMenu,
    isSchoolAdmin,
    canAccessFeature,
    isFeatureEnabled,
    loading,
  } = useTenantContext();

  if (loading) {
    return (
      <div className="d-flex justify-content-center py-5">
        <div className="spinner-border text-primary" role="status" />
      </div>
    );
  }

  const module = moduleMenu.find((entry) => entry.key === moduleKey)
    || SCHOOL_MODULES.find((entry) => entry.key === moduleKey);

  if (!module) {
    return <UpgradeRequired featureKey={moduleKey} />;
  }

  if (isSchoolAdmin) {
    return children;
  }

  const accessibleChildren = (module.children || []).filter(
    (child) => canAccessFeature(child.feature_key, false) && isFeatureEnabled(child.feature_key),
  );

  if (!accessibleChildren.length) {
    return (
      <AccessDenied message="Your role does not have permission to access this area. Contact your school admin to update Permission Settings." />
    );
  }

  return children;
}

export default ModuleHubGate;