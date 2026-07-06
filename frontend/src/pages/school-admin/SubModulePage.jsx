import { Navigate, useParams } from 'react-router-dom';
import EntityListPage from '../../components/EntityListPage';
import ModuleEmptyState from '../../components/ModuleEmptyState';
import { getEntityConfig } from '../../config/entityRegistry';
import { useTenant } from '../../hooks/useTenant';

export function SubModulePage({ title, subtitle, featureKey, createLabel = 'Add Record' }) {
  const params = useParams();
  const { isFeatureEnabled } = useTenant();
  const resolvedTitle = title || params.module?.replace(/-/g, ' ') || 'Module';
  const key = featureKey || params.featureKey;

  if (key && !isFeatureEnabled(key)) {
    return (
      <div className="apex-card p-5 text-center">
        <h5 className="fw-bold">Feature not on your plan</h5>
        <p className="text-muted mb-0">Upgrade your subscription to access {resolvedTitle}.</p>
      </div>
    );
  }

  const config = key ? getEntityConfig(key) : null;

  if (!config) {
    return (
      <div className="apex-card p-4 p-md-5">
        <ModuleEmptyState
          title={resolvedTitle}
          message={
            subtitle
            || `${resolvedTitle} is not yet wired to the live API. Use related modules from the sidebar, or contact support.`
          }
        />
      </div>
    );
  }

  if (config.redirectTo) {
    return <Navigate to={config.redirectTo} replace />;
  }

  return (
    <EntityListPage
      title={resolvedTitle}
      featureKey={key}
      config={{
        ...config,
        createLabel: createLabel || config.createLabel,
        subtitle: subtitle || config.subtitle,
      }}
    />
  );
}

export default SubModulePage;