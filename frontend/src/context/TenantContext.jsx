import { createContext, useContext, useMemo, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { tenantService } from '../services/tenantService';
import { useAuthContext } from './AuthContext';
import { CORE_FEATURE_KEYS, buildFallbackModuleMenu } from '../config/navigation';

const TenantContext = createContext(null);

const applyTenantTheme = (theme) => {
  if (!theme) return;
  const root = document.documentElement;
  if (theme.primary) root.style.setProperty('--apex-primary', theme.primary);
  if (theme.secondary) root.style.setProperty('--apex-secondary', theme.secondary);
  if (theme.accent) root.style.setProperty('--apex-accent', theme.accent);
  root.setAttribute('data-tenant-theme', 'custom');
};

const resetTenantTheme = () => {
  const root = document.documentElement;
  root.style.removeProperty('--apex-primary');
  root.style.removeProperty('--apex-secondary');
  root.style.removeProperty('--apex-accent');
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
    dashboard_widgets: raw.dashboard_widgets || [],
    subscription: raw.subscription || null,
    features_revision: raw.features_revision || null,
  };
};

export function TenantProvider({ children }) {
  const { isSchoolAdmin, isAuthenticated, user } = useAuthContext();
  const shouldLoadTenant = isAuthenticated && isSchoolAdmin;

  const tenantId = user?.tenant || user?.tenant_id;
  const planSlug = user?.tenant_plan_slug;

  const { data, isPending, isFetching, isError, refetch } = useQuery({
    queryKey: ['tenant', 'context', user?.id, tenantId, planSlug],
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

  const isFeatureEnabled = useCallback(
    (featureKey) => {
      if (!isSchoolAdmin) return true;
      if (isSuspended) return false;
      if (!featureKey) return true;
      if (CORE_FEATURE_KEYS.includes(featureKey)) return true;
      if (!tenant) return true;
      const keys = tenant.enabled_feature_keys || [];
      if (keys.includes(featureKey)) return true;
      return tenant.feature_flags?.[featureKey] === true;
    },
    [tenant, isSchoolAdmin, isSuspended],
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
        featureFlags: tenant?.feature_flags || {},
        enabledFeatureKeys: tenant?.enabled_feature_keys || [],
        navigationMenu: tenant?.navigation_menu?.length ? tenant.navigation_menu : moduleMenu,
        moduleMenu,
        dashboardWidgets: tenant?.dashboard_widgets || [],
        subscription: tenant?.subscription || null,
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