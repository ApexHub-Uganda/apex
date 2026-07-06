import { useTenantContext } from '../context/TenantContext';
import { getModuleKeyForFeature } from '../config/schoolModules';

/**
 * Gate UI mutations by role module write permission (plan + admin matrix).
 * Pass moduleKey directly, or featureKey to resolve module bundle.
 */
export function PermissionGate({
  moduleKey,
  featureKey,
  children,
  fallback = null,
  requireWrite = true,
}) {
  const { canAccessModule, canAccessFeature, loading } = useTenantContext();
  const resolvedKey = moduleKey || (featureKey ? getModuleKeyForFeature(featureKey) : null);

  if (loading) return null;

  let allowed = true;
  if (featureKey) {
    allowed = canAccessFeature(featureKey, requireWrite);
  } else if (resolvedKey) {
    allowed = canAccessModule(resolvedKey, requireWrite);
  }
  if (allowed) return children;
  return fallback;
}

export default PermissionGate;