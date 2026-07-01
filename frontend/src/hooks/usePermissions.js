import { useMemo } from 'react';
import { useAuth } from './useAuth';

export function usePermissions() {
  const { user } = useAuth();

  const permissions = useMemo(() => user?.permissions || [], [user]);

  const hasPermission = (permission) => {
    if (!permissions.length) return false;
    if (permissions.includes('*')) return true;
    if (permissions.includes(permission)) return true;

    const [namespace] = permission.split('.');
    if (permissions.includes(`${namespace}.*`)) return true;
    if (permissions.includes('school.*') && permission.startsWith('school.')) return true;

    return false;
  };

  const hasAnyPermission = (...perms) => perms.some(hasPermission);
  const hasAllPermissions = (...perms) => perms.every(hasPermission);

  return {
    permissions,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    canManage: hasPermission('manage'),
    canView: hasPermission('view'),
    canCreate: hasPermission('create'),
    canEdit: hasPermission('edit'),
    canDelete: hasPermission('delete'),
  };
}

export default usePermissions;