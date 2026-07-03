let maintenanceState = {
  enabled: false,
  isSuperAdmin: false,
};

let confirmHandler = null;

export function setMaintenanceState({ enabled, isSuperAdmin }) {
  maintenanceState = {
    enabled: Boolean(enabled),
    isSuperAdmin: Boolean(isSuperAdmin),
  };
}

export function registerMaintenanceConfirm(handler) {
  confirmHandler = handler;
}

export async function confirmMaintenanceAction(config) {
  const method = (config.method || 'get').toLowerCase();
  if (!maintenanceState.enabled || !maintenanceState.isSuperAdmin) {
    return true;
  }
  if (!['post', 'put', 'patch', 'delete'].includes(method)) {
    return true;
  }
  if (!confirmHandler) {
    return true;
  }
  return confirmHandler(config);
}