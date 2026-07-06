import { useMemo, useCallback } from 'react';
import { useAuth } from './useAuth';
import { useTenantContext } from '../context/TenantContext';

export function usePermissions() {
  const { user, isSchoolAdmin } = useAuth();
  const {
    permissions,
    modulePermissions,
    featurePermissions,
    canAccessModule,
    canAccessFeature,
  } = useTenantContext();

  const permissionList = useMemo(
    () => permissions?.length ? permissions : (user?.permissions || []),
    [permissions, user?.permissions],
  );

  const hasPermission = useCallback((permission) => {
    if (isSchoolAdmin) return true;
    if (!permissionList.length) return false;
    if (permissionList.includes('*')) return true;
    if (permissionList.includes(permission)) return true;

    const [namespace] = permission.split('.');
    if (permissionList.includes(`${namespace}.*`)) return true;
    if (permissionList.includes('school.*') && permission.startsWith('school.')) return true;

    return false;
  }, [permissionList, isSchoolAdmin]);

  const canReadModule = useCallback(
    (moduleKey) => canAccessModule(moduleKey, false),
    [canAccessModule],
  );

  const canWriteModule = useCallback(
    (moduleKey) => canAccessModule(moduleKey, true),
    [canAccessModule],
  );

  const canReadFeature = useCallback(
    (featureKey) => canAccessFeature(featureKey, false),
    [canAccessFeature],
  );

  const canWriteFeaturePerm = useCallback(
    (featureKey) => canAccessFeature(featureKey, true),
    [canAccessFeature],
  );

  const hasAnyPermission = (...perms) => perms.some(hasPermission);
  const hasAllPermissions = (...perms) => perms.every(hasPermission);

  return {
    permissions: permissionList,
    modulePermissions,
    featurePermissions,
    canReadFeature,
    canWriteFeature: canWriteFeaturePerm,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    canReadModule,
    canWriteModule,
    canManage: hasPermission('manage') || isSchoolAdmin,
    canView: hasPermission('view') || isSchoolAdmin,
    canCreate: (moduleOrFeatureKey) => (
      canAccessFeature(moduleOrFeatureKey, true) || canWriteModule(moduleOrFeatureKey)
    ),
    canEdit: (moduleOrFeatureKey) => (
      canAccessFeature(moduleOrFeatureKey, true) || canWriteModule(moduleOrFeatureKey)
    ),
    canDelete: (moduleOrFeatureKey) => (
      canAccessFeature(moduleOrFeatureKey, true) || canWriteModule(moduleOrFeatureKey)
    ),
  };
}

export default usePermissions;