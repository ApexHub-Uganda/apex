import { FiInfo, FiRefreshCw } from 'react-icons/fi';
import { useTenant } from '../hooks/useTenant';

export function SchoolContextBanner() {
  const { isPartial, refetch, tenant } = useTenant();

  if (!isPartial) return null;

  return (
    <div className="school-context-banner mb-4">
      <FiInfo size={16} className="flex-shrink-0 mt-1" />
      <div className="flex-grow-1">
        <strong className="small">Showing available school info</strong>
        <p className="text-muted small mb-0">
          Full profile sync is limited right now — displaying {tenant?.name || 'your school'} with
          plan-based modules. Missing data sections will show empty states until you create records.
        </p>
      </div>
      <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => refetch()}>
        <FiRefreshCw size={13} />
      </button>
    </div>
  );
}

export default SchoolContextBanner;