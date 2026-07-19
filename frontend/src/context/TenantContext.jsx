import { createContext, useContext, useMemo, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { tenantService } from '../services/tenantService';
import { useAuthContext } from './AuthContext';
import { CORE_FEATURE_KEYS, buildFallbackModuleMenu } from '../config/navigation';
import { getModuleKeyForFeature } from '../config/schoolModules';

const TenantContext = createContext(null);

/** Darken/lighten a #RRGGBB colour for derived theme tokens. */
const shiftHex = (hex, amount) => {
  if (!hex || typeof hex !== 'string' || !/^#([0-9A-Fa-f]{6})$/.test(hex.trim())) {
    return null;
  }
  const raw = hex.trim().slice(1);
  const nums = [0, 2, 4].map((i) => parseInt(raw.slice(i, i + 2), 16));
  const next = nums.map((n) => Math.max(0, Math.min(255, Math.round(n + amount))));
  return `#${next.map((n) => n.toString(16).padStart(2, '0')).join('')}`.toUpperCase();
};

const applyTenantTheme = (theme) => {
  if (!theme) return;
  const root = document.documentElement;
  if (theme.primary) {
    root.style.setProperty('--apex-primary', theme.primary);
    const dark = shiftHex(theme.primary, -24);
    const light = shiftHex(theme.primary, 36);
    if (dark) root.style.setProperty('--apex-primary-dark', dark);
    if (light) root.style.setProperty('--apex-primary-light', light);
  }
  if (theme.secondary) {
    root.style.setProperty('--apex-secondary', theme.secondary);
    const dark = shiftHex(theme.secondary, -22);
    if (dark) root.style.setProperty('--apex-secondary-dark', dark);
  }
  if (theme.accent) {
    root.style.setProperty('--apex-accent', theme.accent);
    const dark = shiftHex(theme.accent, -18);
    if (dark) root.style.setProperty('--apex-accent-dark', dark);
  }
  root.setAttribute('data-tenant-theme', 'custom');
};

const resetTenantTheme = () => {
  const root = document.documentElement;
  [
    '--apex-primary', '--apex-primary-dark', '--apex-primary-light',
    '--apex-secondary', '--apex-secondary-dark',
    '--apex-accent', '--apex-accent-dark',
  ].forEach((prop) => root.style.removeProperty(prop));
  root.removeAttribute('data-tenant-theme');
};

const normalizeTenant = (raw) => {
  if (!raw) return null;
  return {
    ...raw,
    theme: {
      primary: raw.primary_color || '#0F766E',
      secondary: raw.secondary_color || '#FF7F50',
      accent: raw.accent_color || '#F5E6CA',
    },
    feature_flags: raw.feature_flags || {},
    enabled_feature_keys: raw.enabled_feature_keys || [],
    navigation_menu: raw.navigation_menu || [],
    module_menu: raw.module_menu || [],
    module_permissions: raw.module_permissions || {},
    feature_permissions: raw.feature_permissions || {},
    permissions: raw.permissions || [],
    role_profile: raw.role_profile || null,
    dashboard_widgets: raw.dashboard_widgets || [],
    subscription: raw.subscription || null,
    features_revision: raw.features_revision || null,
    is_school_admin: Boolean(raw.is_school_admin),
    user_role: raw.user_role || null,
  };
};

export function TenantProvider({ children }) {
  const { isSchoolPortalUser, isAuthenticated, user, isSchoolAdmin } = useAuthContext();
  const shouldLoadTenant = isAuthenticated && isSchoolPortalUser;

  const tenantId = user?.tenant || user?.tenant_id;
  const planSlug = user?.tenant_plan_slug;
  const userRole = user?.effective_role || user?.role;

  const { data, isPending, isFetching, isError, refetch } = useQuery({
    queryKey: ['tenant', 'context', user?.id, tenantId, planSlug, userRole],
    queryFn: () => tenantService.getSchoolContext(user),
    enabled: shouldLoadTenant && !!user,
    retry: 2,
    staleTime: 0,
    gcTime: 5 * 60 * 1000,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
    refetchInterval: 30 * 1000,
  });

  const tenant = useMemo(() => {
    const normalized = normalizeTenant(data);
    if (normalized) {
      applyTenantTheme(normalized.theme);
      return normalized;
    }
    if (!shouldLoadTenant) {
      resetTenantTheme();
    }
    return null;
  }, [data, shouldLoadTenant]);

  const loading = shouldLoadTenant && !tenant && (isPending || isFetching);
  const isSuspended = Boolean(
    tenant?.is_suspended
    || tenant?.access_blocked
    || tenant?.status === 'suspended',
  );
  const isPartial = Boolean(tenant?._partial || tenant?._source === 'api_unreachable');
  const isReady = !shouldLoadTenant || !!tenant;
  const contextError = tenant?._error || (isError ? 'Failed to load school plan from server.' : null);

  const modulePermissions = useMemo(
    () => tenant?.module_permissions || user?.module_permissions || {},
    [tenant?.module_permissions, user?.module_permissions],
  );

  const featurePermissions = useMemo(
    () => tenant?.feature_permissions || {},
    [tenant?.feature_permissions],
  );

  const moduleMenu = useMemo(() => {
    const fromApi = tenant?.module_menu || [];
    if (fromApi.length > 0) return fromApi;
    const keys = tenant?.enabled_feature_keys || [];
    if (keys.length > CORE_FEATURE_KEYS.length) {
      return buildFallbackModuleMenu(keys);
    }
    return [];
  }, [tenant?.module_menu, tenant?.enabled_feature_keys]);

  useEffect(() => () => resetTenantTheme(), []);

  const canAccessModule = useCallback(
    (moduleKey, requireWrite = false) => {
      if (!moduleKey) return true;
      if (isSchoolAdmin) return !isSuspended;
      const perms = modulePermissions[moduleKey];
      if (!perms) return false;
      return requireWrite ? Boolean(perms.can_write) : Boolean(perms.can_read);
    },
    [modulePermissions, isSchoolAdmin, isSuspended],
  );

  const permissionTokens = useMemo(
    () => tenant?.permissions || [],
    [tenant?.permissions],
  );

  const resolveFeatureKey = useCallback((featureKey) => (
    featureKey === 'streams' ? 'classes' : featureKey
  ), []);

  const canAccessFeature = useCallback(
    (featureKey, requireWrite = false) => {
      if (!featureKey) return true;
      featureKey = resolveFeatureKey(featureKey);
      if (isSuspended) return false;
      if (isSchoolAdmin) return true;
      if (CORE_FEATURE_KEYS.includes(featureKey) && featureKey === 'dashboard_analytics') {
        return true;
      }

      const menuChild = moduleMenu
        .flatMap((module) => module.children || [])
        .find((child) => child.feature_key === featureKey);
      if (menuChild) {
        return requireWrite ? Boolean(menuChild.can_write) : Boolean(menuChild.can_read ?? true);
      }

      const perms = featurePermissions[featureKey];
      if (perms) {
        return requireWrite ? Boolean(perms.can_write) : Boolean(perms.can_read);
      }

      if (Object.keys(featurePermissions).length > 0) {
        return false;
      }

      if (permissionTokens.length) {
        if (requireWrite) {
          return permissionTokens.includes(`${featureKey}.write`);
        }
        return (
          permissionTokens.includes(`${featureKey}.read`)
          || permissionTokens.includes(`${featureKey}.write`)
        );
      }

      const moduleKey = getModuleKeyForFeature(featureKey);
      if (!moduleKey) return false;
      if (requireWrite) {
        return false;
      }
      return canAccessModule(moduleKey, false);
    },
    [
      featurePermissions,
      isSchoolAdmin,
      isSuspended,
      canAccessModule,
      moduleMenu,
      permissionTokens,
      resolveFeatureKey,
    ],
  );

  const isFeatureEnabled = useCallback(
    (featureKey) => {
      if (!featureKey) return true;
      featureKey = resolveFeatureKey(featureKey);
      if (isSuspended) return false;
      if (CORE_FEATURE_KEYS.includes(featureKey)) {
        return isSchoolAdmin || featureKey === 'dashboard_analytics';
      }
      if (!tenant) return false;

      if (!isSchoolAdmin && !canAccessFeature(featureKey, false)) {
        return false;
      }

      const keys = tenant.enabled_feature_keys || [];
      if (keys.includes(featureKey)) return true;
      return tenant.feature_flags?.[featureKey] === true;
    },
    [tenant, isSchoolAdmin, isSuspended, canAccessFeature, resolveFeatureKey],
  );

  const canWriteFeature = useCallback(
    (featureKey) => canAccessFeature(featureKey, true),
    [canAccessFeature],
  );

  return (
    <TenantContext.Provider
      value={{
        tenant,
        loading,
        isSuspended,
        isReady,
        isPartial,
        isError: isError || Boolean(contextError),
        contextError,
        refetch,
        isFeatureEnabled,
        canWriteFeature,
        canAccessModule,
        featureFlags: tenant?.feature_flags || {},
        enabledFeatureKeys: tenant?.enabled_feature_keys || [],
        navigationMenu: tenant?.navigation_menu?.length ? tenant.navigation_menu : moduleMenu,
        moduleMenu,
        modulePermissions,
        featurePermissions,
        canAccessFeature,
        permissions: tenant?.permissions || user?.permissions || [],
        roleProfile: tenant?.role_profile || null,
        dashboardWidgets: tenant?.dashboard_widgets || [],
        subscription: tenant?.subscription || null,
        isSchoolAdmin: tenant?.is_school_admin ?? isSchoolAdmin,
      }}
    >
      {children}
    </TenantContext.Provider>
  );
}

export function useTenantContext() {
  const ctx = useContext(TenantContext);
  if (!ctx) throw new Error('useTenantContext must be used within TenantProvider');
  return ctx;
}

export default TenantContext;