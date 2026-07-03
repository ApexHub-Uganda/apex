import { FiAlertTriangle } from 'react-icons/fi';
import { useMaintenance } from '../hooks/useMaintenance';

export function MaintenanceBanner() {
  const { maintenanceMode, isSuperAdmin } = useMaintenance();

  if (!maintenanceMode || !isSuperAdmin) return null;

  return (
    <div className="maintenance-mode-banner" role="alert">
      <FiAlertTriangle size={18} aria-hidden />
      <div className="maintenance-mode-banner-text">
        <strong>Maintenance mode enabled</strong>
        <span>Be careful of actions — all other users are blocked from the platform.</span>
      </div>
    </div>
  );
}

export default MaintenanceBanner;