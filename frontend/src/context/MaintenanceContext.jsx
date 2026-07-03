import { createContext, useCallback, useContext, useEffect, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../hooks/useAuth';
import { platformService } from '../services/moduleService';
import { alert } from '../utils/notify';
import {
  registerMaintenanceConfirm,
  setMaintenanceState,
} from '../utils/maintenanceConfirm';

const MaintenanceContext = createContext(null);

const MUTATING_METHODS = new Set(['post', 'put', 'patch', 'delete']);

const describeMaintenanceAction = (config) => {
  const method = (config.method || 'get').toUpperCase();
  const url = config.url || '';
  if (url.includes('/platform/settings/general/')) {
    return 'update platform settings while schools are locked out';
  }
  if (url.includes('/tenants/') && method !== 'GET') {
    return 'change school records while users cannot access the platform';
  }
  if (url.includes('/subscriptions/')) {
    return 'modify subscriptions while checkout and self-service are unavailable';
  }
  if (url.includes('/broadcast')) {
    return 'send broadcasts while most users cannot sign in';
  }
  return 'perform this action while the platform is in maintenance mode';
};

export function MaintenanceProvider({ children }) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const isSuperAdmin = user?.role === 'super_admin';

  const { data: health } = useQuery({
    queryKey: ['platform-health'],
    queryFn: () => platformService.getHealth(),
    refetchInterval: 60000,
    staleTime: 15000,
  });

  const maintenanceMode = Boolean(health?.maintenance_mode);

  const confirmMaintenanceAction = useCallback(async (config) => {
    const method = (config.method || 'get').toLowerCase();
    if (!MUTATING_METHODS.has(method)) return true;

    const payload = typeof config.data === 'string'
      ? (() => { try { return JSON.parse(config.data); } catch { return {}; } })()
      : (config.data || {});

    if (config.url?.includes('/platform/settings/general/') && payload.maintenance_mode === false) {
      return true;
    }

    const action = describeMaintenanceAction(config);
    const result = await alert.confirm({
      title: 'Maintenance mode is active',
      text: `You are about to ${action}. Non–super-admin users are blocked until maintenance is turned off. Continue?`,
      confirmText: 'Yes, continue',
      cancelText: 'Cancel',
      icon: 'warning',
      danger: true,
    });
    return result.isConfirmed;
  }, []);

  useEffect(() => {
    setMaintenanceState({ enabled: maintenanceMode, isSuperAdmin });
  }, [maintenanceMode, isSuperAdmin]);

  useEffect(() => {
    if (!isSuperAdmin) return undefined;
    registerMaintenanceConfirm(confirmMaintenanceAction);
    return () => registerMaintenanceConfirm(null);
  }, [isSuperAdmin, confirmMaintenanceAction]);

  useEffect(() => {
    const handleMaintenanceBlocked = () => {
      queryClient.invalidateQueries({ queryKey: ['platform-health'] });
    };
    window.addEventListener('apex:maintenance-blocked', handleMaintenanceBlocked);
    return () => window.removeEventListener('apex:maintenance-blocked', handleMaintenanceBlocked);
  }, [queryClient]);

  const value = useMemo(() => ({
    maintenanceMode,
    isSuperAdmin,
    refreshMaintenanceStatus: () => queryClient.invalidateQueries({ queryKey: ['platform-health'] }),
  }), [maintenanceMode, isSuperAdmin, queryClient]);

  return (
    <MaintenanceContext.Provider value={value}>
      {children}
    </MaintenanceContext.Provider>
  );
}

export function useMaintenance() {
  const context = useContext(MaintenanceContext);
  if (!context) {
    throw new Error('useMaintenance must be used within MaintenanceProvider');
  }
  return context;
}

export default MaintenanceContext;