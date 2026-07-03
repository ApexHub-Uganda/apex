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
  const { canAccessModule, loading } = useTenantContext();
  const resolvedKey = moduleKey || (featureKey ? getModuleKeyForFeature(featureKey) : null);

  if (loading) return null;
  if (!resolvedKey) return children;

  const allowed = canAccessModule(resolvedKey, requireWrite);
  if (allowed) return children;
  return fallback;
}

export default PermissionGate;