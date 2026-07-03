import { FiCheck, FiLayers } from 'react-icons/fi';

export function PlanFeatureBreakdown({ plan, showInheritedList = false, compact = false }) {
  if (!plan) return null;

  const hasInheritance = Boolean(plan.inherits_from_label && plan.inherited_feature_count > 0);
  const exclusiveCategories = plan.exclusive_feature_categories?.length
    ? plan.exclusive_feature_categories
    : (plan.feature_categories || []);

  if (!hasInheritance) {
    if (compact) {
      return (
        <p className="text-muted small mb-0">
          {plan.feature_count ?? 0} features included on this plan.
        </p>
      );
    }
    return (
      <div className="plan-feature-breakdown">
        <div className="row g-3">
          {exclusiveCategories.map((category) => (
            <div className="col-md-6" key={category.name}>
              <div className="apex-card p-3 h-100 plan-upgrade-feature-group">
                <h6 className="fw-bold mb-2">{category.name}</h6>
                <ul className="plan-upgrade-feature-list mb-0">
                  {(category.features || []).map((feature) => (
                    <li key={feature.feature_key}>
                      <FiCheck size={13} />
                      <span className="fw-medium">{feature.name}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="plan-feature-breakdown">
      <div className="plan-inheritance-banner mb-3">
        <FiLayers size={16} />
        <div>
          <strong>{plan.inherited_summary || `Everything in ${plan.inherits_from_label}, plus more`}</strong>
          <span className="d-block text-muted small">
            {plan.inherited_feature_count} inherited · {plan.exclusive_feature_count} additional on {plan.name}
          </span>
        </div>
      </div>

      {showInheritedList && plan.inherited_features?.length > 0 && (
        <div className="mb-3">
          <h6 className="fw-bold small text-muted text-uppercase mb-2">
            Included from {plan.inherits_from_label}
          </h6>
          <ul className="plan-upgrade-feature-list plan-inherited-feature-list mb-0">
            {plan.inherited_features.map((feature) => (
              <li key={feature.feature_key}>
                <FiCheck size={13} />
                <span>{feature.name}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!compact && exclusiveCategories.length > 0 && (
        <>
          <h6 className="fw-bold small text-muted text-uppercase mb-2">
            Additional on {plan.name}
          </h6>
          <div className="row g-3">
            {exclusiveCategories.map((category) => (
              <div className="col-md-6" key={category.name}>
                <div className="apex-card p-3 h-100 plan-upgrade-feature-group">
                  <h6 className="fw-bold mb-2">{category.name}</h6>
                  <ul className="plan-upgrade-feature-list mb-0">
                    {(category.features || []).map((feature) => (
                      <li key={feature.feature_key}>
                        <FiCheck size={13} />
                        <div>
                          <span className="fw-medium">{feature.name}</span>
                          {feature.description && (
                            <span className="d-block text-muted" style={{ fontSize: '0.75rem' }}>
                              {feature.description}
                            </span>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default PlanFeatureBreakdown;