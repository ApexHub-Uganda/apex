import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FiArrowLeft, FiChevronDown, FiChevronRight, FiLayers, FiLock, FiSave, FiShield,
} from 'react-icons/fi';
import { usePlanEditor, LIMIT_FIELDS } from '../hooks/usePlanEditor';
import PlanVerifiedBadge from './PlanVerifiedBadge';

export function PlanEditorWorkspace({
  plan,
  onSave,
  onCancel,
  saving = false,
}) {
  const editor = usePlanEditor(plan, { enabled: true });
  const {
    form,
    catalog,
    catalogLoading,
    selectedFeatures,
    expanded,
    setExpanded,
    inheritedFeatureKeys,
    parentTierLabel,
    activeSlug,
    totalFeatures,
    exclusiveCount,
    updateField,
    toggleFeature,
    toggleCategory,
    categoryState,
    getCategoryMeta,
    expandAllModules,
    collapseAllModules,
    buildPayload,
    isNew,
  } = editor;

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onSave(buildPayload());
  };

  const inheritedCount = inheritedFeatureKeys.size;

  return (
    <form className="plan-editor-workspace" onSubmit={handleSubmit}>
      <div className="plan-editor-topbar apex-card">
        <div className="plan-editor-topbar-main">
          <Link to="/super-admin/plans" className="plan-editor-back" onClick={(e) => { e.preventDefault(); onCancel(); }}>
            <FiArrowLeft size={16} />
            Plans & Subscriptions
          </Link>
          <div className="plan-editor-title-wrap">
            <h1 className="plan-editor-title">
              {isNew ? 'Create subscription plan' : `Edit ${form.name || 'plan'}`}
            </h1>
            <p className="plan-editor-subtitle">
              Configure pricing, limits, and module features in a dedicated workspace.
            </p>
          </div>
        </div>
        <div className="plan-editor-topbar-actions">
          <button type="button" className="btn btn-outline-secondary" onClick={onCancel} disabled={saving}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary d-inline-flex align-items-center gap-2" disabled={saving || !form.name}>
            <FiSave size={15} />
            {saving ? 'Saving…' : isNew ? 'Create plan' : 'Save changes'}
          </button>
        </div>
      </div>

      <div className="plan-editor-stats row g-3">
        <div className="col-md-3">
          <div className="plan-editor-stat apex-card">
            <span className="plan-editor-stat-label">Total selected</span>
            <strong>{selectedFeatures.size}</strong>
            <span className="text-muted small">of {totalFeatures} platform features</span>
          </div>
        </div>
        <div className="col-md-3">
          <div className="plan-editor-stat apex-card">
            <span className="plan-editor-stat-label">Inherited</span>
            <strong>{inheritedCount}</strong>
            <span className="text-muted small">
              {parentTierLabel ? `Required from ${parentTierLabel}` : 'Base tier plan'}
            </span>
          </div>
        </div>
        <div className="col-md-3">
          <div className="plan-editor-stat apex-card">
            <span className="plan-editor-stat-label">Additional</span>
            <strong>{exclusiveCount}</strong>
            <span className="text-muted small">Exclusive to this plan tier</span>
          </div>
        </div>
        <div className="col-md-3">
          <div className="plan-editor-stat apex-card">
            <span className="plan-editor-stat-label">Modules</span>
            <strong>{catalog.length}</strong>
            <span className="text-muted small">Collapsed by default — expand to edit</span>
          </div>
        </div>
      </div>

      <div className="row g-4 plan-editor-layout">
        <div className="col-xl-4">
          <div className="plan-editor-sidebar">
            <motion.div className="apex-card p-4 mb-4" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <div className="d-flex align-items-center gap-2 mb-3">
                <FiLayers className="text-primary" />
                <h5 className="fw-bold mb-0">Plan details</h5>
                {!isNew && <PlanVerifiedBadge planSlug={activeSlug} size="sm" />}
              </div>
              <div className="mb-3">
                <label className="form-label fw-medium">Plan name *</label>
                <input className="form-control" value={form.name} onChange={(e) => updateField('name', e.target.value)} required />
              </div>
              <div className="mb-3">
                <label className="form-label fw-medium">Slug {!isNew ? '' : '*'}</label>
                <input
                  className="form-control"
                  value={form.slug}
                  disabled={!isNew}
                  onChange={(e) => updateField('slug', e.target.value)}
                  placeholder="e.g. premium_plus"
                />
              </div>
              <div className="mb-3">
                <label className="form-label fw-medium">Description</label>
                <textarea
                  className="form-control"
                  rows={3}
                  value={form.description}
                  onChange={(e) => updateField('description', e.target.value)}
                />
              </div>
              <div className="row g-3">
                <div className="col-6">
                  <label className="form-label fw-medium">Monthly ($)</label>
                  <input type="number" className="form-control" value={form.price_monthly} onChange={(e) => updateField('price_monthly', e.target.value)} />
                </div>
                <div className="col-6">
                  <label className="form-label fw-medium">Yearly ($)</label>
                  <input type="number" className="form-control" value={form.price_yearly} onChange={(e) => updateField('price_yearly', e.target.value)} />
                </div>
              </div>
              <div className="d-flex gap-4 mt-3">
                <div className="form-check">
                  <input className="form-check-input" type="checkbox" checked={form.is_active} onChange={(e) => updateField('is_active', e.target.checked)} id="plan-active" />
                  <label className="form-check-label" htmlFor="plan-active">Active</label>
                </div>
                <div className="form-check">
                  <input className="form-check-input" type="checkbox" checked={form.is_public} onChange={(e) => updateField('is_public', e.target.checked)} id="plan-public" />
                  <label className="form-check-label" htmlFor="plan-public">Public</label>
                </div>
              </div>
            </motion.div>

            <motion.div className="apex-card p-4" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
              <div className="d-flex align-items-center gap-2 mb-3">
                <FiShield className="text-primary" />
                <h5 className="fw-bold mb-0">Limits & lifecycle</h5>
              </div>
              <p className="text-muted small mb-3">
                User capacity is unlimited across all tiers. Configure operational limits below.
              </p>
              <div className="row g-3">
                {LIMIT_FIELDS.map((field) => (
                  <div className="col-md-6" key={field.name}>
                    <label className="form-label small fw-medium">{field.label}</label>
                    <input
                      type={field.type}
                      className="form-control form-control-sm"
                      value={form[field.name]}
                      onChange={(e) => updateField(field.name, e.target.value)}
                    />
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>

        <div className="col-xl-8">
          <motion.div className="apex-card plan-editor-modules" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }}>
            <div className="plan-editor-modules-header">
              <div>
                <h5 className="fw-bold mb-1">Module feature catalog</h5>
                <p className="text-muted small mb-0">
                  Assign platform modules and features. Inherited items from lower tiers are locked and greyed out.
                </p>
              </div>
              <div className="plan-editor-modules-tools">
                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={expandAllModules}>
                  Expand all
                </button>
                <button type="button" className="btn btn-sm btn-outline-secondary" onClick={collapseAllModules}>
                  Collapse all
                </button>
              </div>
            </div>

            {parentTierLabel && inheritedCount > 0 && (
              <div className="plan-inheritance-banner mb-4">
                <FiLock size={16} />
                <div>
                  <strong>All {parentTierLabel} features are included automatically</strong>
                  <span className="d-block text-muted small">
                    Greyed modules and features are mandatory from the lower plan. Select additional items to differentiate this tier.
                  </span>
                </div>
              </div>
            )}

            {catalogLoading ? (
              <p className="text-muted px-1">Loading feature catalog…</p>
            ) : (
              <div className="plan-editor-module-list">
                {catalog.map((category) => {
                  const state = categoryState(category);
                  const meta = getCategoryMeta(category);
                  const isOpen = expanded[category.slug];
                  const moduleClass = [
                    'plan-module-panel',
                    meta.allInherited ? 'is-fully-inherited' : '',
                    meta.inheritedCount > 0 ? 'has-inherited' : '',
                    meta.selectedCount === 0 ? 'is-empty' : '',
                  ].filter(Boolean).join(' ');

                  return (
                    <div key={category.slug} className={moduleClass}>
                      <div
                        className="plan-module-panel-header"
                        onClick={() => setExpanded((prev) => ({ ...prev, [category.slug]: !prev[category.slug] }))}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            setExpanded((prev) => ({ ...prev, [category.slug]: !prev[category.slug] }));
                          }
                        }}
                      >
                        <div className="plan-module-panel-title">
                          {isOpen ? <FiChevronDown size={16} /> : <FiChevronRight size={16} />}
                          <span className="fw-semibold">{category.name}</span>
                          <span className="plan-module-count">
                            {meta.selectedCount}/{meta.totalCount}
                          </span>
                          {meta.allInherited && (
                            <span className="plan-module-badge is-inherited">All inherited</span>
                          )}
                          {!meta.allInherited && meta.inheritedCount > 0 && (
                            <span className="plan-module-badge is-mixed">
                              {meta.inheritedCount} inherited
                              {meta.additionalSelected > 0 ? ` · ${meta.additionalSelected} additional` : ''}
                            </span>
                          )}
                        </div>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-primary"
                          disabled={meta.allInherited}
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleCategory(category, state !== 'all');
                          }}
                        >
                          {meta.allInherited ? 'Included' : state === 'all' ? 'Deselect optional' : 'Select optional'}
                        </button>
                      </div>

                      {isOpen && (
                        <div className="plan-module-panel-body">
                          {category.features.map((feature) => {
                            const fkey = feature.feature_key || feature.slug;
                            const fname = feature.feature_name || feature.name;
                            const isInherited = inheritedFeatureKeys.has(fkey);
                            return (
                              <label
                                key={fkey}
                                className={`plan-feature-row ${isInherited ? 'is-inherited' : ''}`}
                                htmlFor={`feat-${fkey}`}
                              >
                                <input
                                  className="form-check-input"
                                  type="checkbox"
                                  id={`feat-${fkey}`}
                                  checked={selectedFeatures.has(fkey)}
                                  disabled={isInherited}
                                  onChange={() => toggleFeature(fkey)}
                                />
                                <div className="plan-feature-row-content">
                                  <div className="d-flex align-items-center gap-2 flex-wrap">
                                    <span className="fw-medium">{fname}</span>
                                    {isInherited && (
                                      <span className="plan-feature-tag">From {parentTierLabel}</span>
                                    )}
                                  </div>
                                  {feature.description && (
                                    <span className="plan-feature-description">{feature.description}</span>
                                  )}
                                </div>
                              </label>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </form>
  );
}

export default PlanEditorWorkspace;