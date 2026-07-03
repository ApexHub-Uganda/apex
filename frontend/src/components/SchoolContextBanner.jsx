import { FiAlertTriangle, FiInfo, FiRefreshCw } from 'react-icons/fi';
import { useTenant } from '../hooks/useTenant';
import { notify } from '../utils/notify';

export function SchoolContextBanner() {
  const {
    isPartial, isError, contextError, refetch, tenant, moduleMenu, loading, subscription,
  } = useTenant();

  const handleSync = async () => {
    try {
      const result = await refetch();
      const modules = result.data?.module_menu?.length || moduleMenu?.length || 0;
      if (modules > 0) {
        notify.success(`Loaded ${modules} modules from your ${subscription?.plan_name || 'plan'}.`);
      } else {
        notify.warning('Still no modules returned. Check that the backend is running on port 8000.');
      }
    } catch {
      notify.error('Unable to sync school modules. Is the API server running?');
    }
  };

  const modulesMissing = !loading && (moduleMenu?.length ?? 0) === 0;
  const apiUnreachable = tenant?._source === 'api_unreachable';
  const showBanner = isPartial || isError || modulesMissing || apiUnreachable;

  if (!showBanner) return null;

  return (
    <div className={`school-context-banner mb-4 ${(isError || modulesMissing || apiUnreachable) ? 'border border-warning' : ''}`}>
      <FiAlertTriangle size={16} className="flex-shrink-0 mt-1 text-warning" />
      <div className="flex-grow-1">
        <strong className="small">
          {apiUnreachable ? 'Cannot reach database API' : modulesMissing ? 'Plan modules not loaded' : 'School plan sync needed'}
        </strong>
        <p className="text-muted small mb-0">
          {apiUnreachable
            ? `The school dashboard could not load modules from the server (${contextError || 'connection failed'}). Start the backend: cd E:/apex/backend && python manage.py runserver`
            : modulesMissing
              ? `${tenant?.name || 'Your school'} has no modules in the sidebar. Click Sync to pull Premium Plus features from the database.`
              : `Plan: ${subscription?.plan_name || '—'}. Sync to refresh modules after a super-admin plan change.`}
        </p>
      </div>
      <button type="button" className="btn btn-sm btn-warning" onClick={handleSync} disabled={loading}>
        <FiRefreshCw size={13} className="me-1" />
        Sync from DB
      </button>
    </div>
  );
}

export default SchoolContextBanner;