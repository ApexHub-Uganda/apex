import { Link, useParams } from 'react-router-dom';
import { FiArrowRight } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import { useTenant } from '../../hooks/useTenant';
import { resolveFeatureIcon } from '../../utils/featureIcons';
import { SCHOOL_MODULES } from '../../config/schoolModules';

export function ModuleHub({ moduleKey: propKey }) {
  const { moduleKey: paramKey } = useParams();
  const moduleKey = propKey || paramKey;
  const { moduleMenu, isFeatureEnabled } = useTenant();

  const module = moduleMenu.find((m) => m.key === moduleKey)
    || SCHOOL_MODULES.find((m) => m.key === moduleKey);

  if (!module) {
    return (
      <div className="apex-card p-5 text-center">
        <h5 className="fw-bold">Module not available</h5>
        <p className="text-muted mb-0">This module is not included in your school&apos;s plan.</p>
      </div>
    );
  }

  const children = (module.children || []).filter(
    (child) => isFeatureEnabled(child.feature_key),
  );

  const Icon = resolveFeatureIcon(module.icon);

  return (
    <div>
      <PageHeader
        title={module.label}
        subtitle={`${children.length} feature${children.length === 1 ? '' : 's'} enabled on your plan`}
      />

      <div className="row g-3">
        {children.length === 0 ? (
          <div className="col-12">
            <div className="apex-card p-5 text-center text-muted">
              No child features enabled yet. Contact your platform admin to update your plan.
            </div>
          </div>
        ) : (
          children.map((child) => {
            const ChildIcon = resolveFeatureIcon(child.icon);
            return (
              <div key={child.feature_key} className="col-sm-6 col-lg-4">
                <Link to={child.path} className="school-module-hub-card text-decoration-none h-100 d-block">
                  <div className="d-flex align-items-start justify-content-between mb-3">
                    <span className="school-module-icon">
                      <ChildIcon size={18} />
                    </span>
                    <FiArrowRight className="text-muted" size={16} />
                  </div>
                  <h6 className="fw-bold mb-1 text-body">{child.label}</h6>
                  <p className="text-muted small mb-0">Open module actions and records</p>
                </Link>
              </div>
            );
          })
        )}
      </div>

      <div className="apex-card p-4 mt-4 d-flex align-items-center gap-3">
        <span className="school-module-icon">
          <Icon size={20} />
        </span>
        <div>
          <div className="fw-semibold">{module.label}</div>
          <div className="text-muted small">
            Use the cards above to manage records, create entries, and run workflows for this module.
          </div>
        </div>
      </div>
    </div>
  );
}

export default ModuleHub;