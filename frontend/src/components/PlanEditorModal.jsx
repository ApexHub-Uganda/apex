import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FiChevronDown, FiChevronRight } from 'react-icons/fi';
import Modal from './Modal';
import { featuresService } from '../services/moduleService';

const USER_LIMIT_FIELDS = [
  { name: 'max_students', label: 'Max Students' },
  { name: 'max_staff', label: 'Max Staff' },
  { name: 'max_parents', label: 'Max Parents' },
  { name: 'max_branches', label: 'Max Branches' },
];

const LIMIT_FIELDS = [
  { name: 'max_storage_mb', label: 'Storage Limit (MB)', type: 'number' },
  { name: 'max_sms_monthly', label: 'SMS / Month', type: 'number' },
  { name: 'max_emails_monthly', label: 'Emails / Month', type: 'number' },
  { name: 'trial_days', label: 'Trial Duration (days)', type: 'number' },
  { name: 'grace_period_days', label: 'Grace Period (days)', type: 'number' },
];

const emptyForm = () => ({
  name: '',
  slug: '',
  description: '',
  price_monthly: '',
  price_yearly: '',
  is_active: true,
  is_public: true,
  sort_order: 0,
  max_students: 100,
  max_staff: 20,
  max_parents: 500,
  max_branches: 1,
  max_storage_mb: 1024,
  max_sms_monthly: 0,
  max_emails_monthly: 500,
  trial_days: 14,
  grace_period_days: 7,
});

export function PlanEditorModal({
  show,
  onHide,
  plan,
  onSave,
  saving = false,
}) {
  const [form, setForm] = useState(emptyForm());
  const [selectedFeatures, setSelectedFeatures] = useState(new Set());
  const [expanded, setExpanded] = useState({});

  const { data: catalog = [], isLoading: catalogLoading } = useQuery({
    queryKey: ['feature-catalog'],
    queryFn: () => featuresService.getCatalog(),
    enabled: show,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (!show) return;
    if (plan) {
      setForm({
        ...emptyForm(),
        name: plan.name ?? '',
        slug: plan.slug ?? '',
        description: plan.description ?? '',
        price_monthly: plan.price_monthly ?? '',
        price_yearly: plan.price_yearly ?? '',
        is_active: plan.is_active ?? true,
        is_public: plan.is_public ?? true,
        sort_order: plan.sort_order ?? 0,
        max_students: plan.max_students ?? 100,
        max_staff: plan.max_staff ?? 20,
        max_parents: plan.max_parents ?? 500,
        max_branches: plan.max_branches ?? 1,
        max_storage_mb: plan.max_storage_mb ?? 1024,
        max_sms_monthly: plan.max_sms_monthly ?? 0,
        max_emails_monthly: plan.max_emails_monthly ?? 500,
        trial_days: plan.trial_days ?? 14,
        grace_period_days: plan.grace_period_days ?? 7,
      });
      const keys = new Set(
        plan.enabled_features_detail?.map((f) => f.feature_key)
        || Object.entries(plan.feature_flags || {})
          .filter(([key, enabled]) => enabled && key.includes('_'))
          .map(([key]) => key),
      );
      setSelectedFeatures(keys);
      const open = {};
      catalog.forEach((cat) => { open[cat.slug] = true; });
      setExpanded(open);
    } else {
      setForm(emptyForm());
      setSelectedFeatures(new Set());
      const open = {};
      catalog.forEach((cat) => { open[cat.slug] = true; });
      setExpanded(open);
    }
  }, [show, plan, catalog]);

  const selectedCount = selectedFeatures.size;
  const totalFeatures = useMemo(
    () => catalog.reduce((sum, cat) => sum + (cat.features?.length || 0), 0),
    [catalog],
  );

  const updateField = (name, value) => {
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const toggleFeature = (featureKey) => {
    setSelectedFeatures((prev) => {
      const next = new Set(prev);
      if (next.has(featureKey)) next.delete(featureKey);
      else next.add(featureKey);
      return next;
    });
  };

  const toggleCategory = (category, selectAll) => {
    setSelectedFeatures((prev) => {
      const next = new Set(prev);
      category.features.forEach((f) => {
        const key = f.feature_key || f.slug;
        if (selectAll) next.add(key);
        else next.delete(key);
      });
      return next;
    });
  };

  const categoryState = (category) => {
    const slugs = category.features.map((f) => f.feature_key || f.slug);
    const selected = slugs.filter((s) => selectedFeatures.has(s)).length;
    if (selected === 0) return 'none';
    if (selected === slugs.length) return 'all';
    return 'partial';
  };

  const handleSubmit = async () => {
    const payload = {
      ...form,
      price_monthly: Number(form.price_monthly) || 0,
      price_yearly: Number(form.price_yearly) || Number(form.price_monthly) * 10 || 0,
      max_students: 0,
      max_staff: 0,
      max_parents: 0,
      max_branches: 0,
      enabled_feature_keys: Array.from(selectedFeatures),
    };
    await onSave(payload);
  };

  return (
    <Modal
      show={show}
      onHide={onHide}
      title={plan ? `Edit Plan — ${plan.name}` : 'Create Plan'}
      size="lg"
      footer={(
        <>
          <span className="text-muted small me-auto">
            {selectedCount} of {totalFeatures} features selected
          </span>
          <button className="btn btn-secondary" onClick={onHide} disabled={saving}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={saving || !form.name}>
            {saving ? 'Saving…' : plan ? 'Update Plan' : 'Create Plan'}
          </button>
        </>
      )}
    >
      <div className="row g-3 mb-4">
        <div className="col-md-6">
          <label className="form-label fw-medium">Plan Name *</label>
          <input className="form-control" value={form.name} onChange={(e) => updateField('name', e.target.value)} />
        </div>
        <div className="col-md-6">
          <label className="form-label fw-medium">Slug {!plan && '*'}</label>
          <input
            className="form-control"
            value={form.slug}
            disabled={!!plan}
            onChange={(e) => updateField('slug', e.target.value)}
            placeholder="e.g. premium_plus"
          />
        </div>
        <div className="col-12">
          <label className="form-label fw-medium">Description</label>
          <textarea
            className="form-control"
            rows={2}
            value={form.description}
            onChange={(e) => updateField('description', e.target.value)}
          />
        </div>
        <div className="col-md-4">
          <label className="form-label fw-medium">Monthly Price ($)</label>
          <input type="number" className="form-control" value={form.price_monthly} onChange={(e) => updateField('price_monthly', e.target.value)} />
        </div>
        <div className="col-md-4">
          <label className="form-label fw-medium">Yearly Price ($)</label>
          <input type="number" className="form-control" value={form.price_yearly} onChange={(e) => updateField('price_yearly', e.target.value)} />
        </div>
        <div className="col-md-4">
          <label className="form-label fw-medium">Sort Order</label>
          <input type="number" className="form-control" value={form.sort_order} onChange={(e) => updateField('sort_order', e.target.value)} />
        </div>
        <div className="col-md-6">
          <div className="form-check">
            <input className="form-check-input" type="checkbox" checked={form.is_active} onChange={(e) => updateField('is_active', e.target.checked)} id="plan-active" />
            <label className="form-check-label" htmlFor="plan-active">Active</label>
          </div>
        </div>
        <div className="col-md-6">
          <div className="form-check">
            <input className="form-check-input" type="checkbox" checked={form.is_public} onChange={(e) => updateField('is_public', e.target.checked)} id="plan-public" />
            <label className="form-check-label" htmlFor="plan-public">Public (visible on signup)</label>
          </div>
        </div>
      </div>

      <h6 className="fw-bold mb-3">Plan Limits</h6>
      <div className="alert alert-light border small mb-3">
        <strong>User capacity:</strong> Unlimited for all plans — students, staff, parents, and branches are not restricted by subscription tier.
      </div>
      <div className="row g-3 mb-3">
        {USER_LIMIT_FIELDS.map((field) => (
          <div className="col-md-3" key={field.name}>
            <label className="form-label small fw-medium text-muted">{field.label}</label>
            <div className="form-control form-control-sm bg-light text-muted">Unlimited</div>
          </div>
        ))}
      </div>
      <div className="row g-3 mb-4">
        {LIMIT_FIELDS.map((field) => (
          <div className="col-md-4" key={field.name}>
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

      <h6 className="fw-bold mb-3">Features & Benefits</h6>
      {catalogLoading ? (
        <p className="text-muted">Loading feature catalog…</p>
      ) : (
        <div className="d-flex flex-column gap-2" style={{ maxHeight: 360, overflowY: 'auto' }}>
          {catalog.map((category) => {
            const state = categoryState(category);
            const isOpen = expanded[category.slug];
            return (
              <div key={category.slug} className="border rounded-3">
                <div
                  className="d-flex align-items-center justify-content-between px-3 py-2"
                  style={{ background: 'var(--apex-bg)', cursor: 'pointer' }}
                  onClick={() => setExpanded((prev) => ({ ...prev, [category.slug]: !prev[category.slug] }))}
                >
                  <div className="d-flex align-items-center gap-2">
                    {isOpen ? <FiChevronDown size={16} /> : <FiChevronRight size={16} />}
                    <span className="fw-semibold small">{category.name}</span>
                    <span className="badge bg-secondary-subtle text-secondary">
                      {category.features.filter((f) => selectedFeatures.has(f.feature_key || f.slug)).length}/{category.features.length}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-primary"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleCategory(category, state !== 'all');
                    }}
                  >
                    {state === 'all' ? 'Deselect all' : 'Select all'}
                  </button>
                </div>
                {isOpen && (
                  <div className="px-3 py-2 row g-2">
                    {category.features.map((feature) => {
                      const fkey = feature.feature_key || feature.slug;
                      const fname = feature.feature_name || feature.name;
                      return (
                        <div className="col-md-6" key={fkey}>
                          <div className="form-check">
                            <input
                              className="form-check-input"
                              type="checkbox"
                              id={`feat-${fkey}`}
                              checked={selectedFeatures.has(fkey)}
                              onChange={() => toggleFeature(fkey)}
                            />
                            <label className="form-check-label small" htmlFor={`feat-${fkey}`}>
                              <span className="fw-medium">{fname}</span>
                              {feature.description && (
                                <span className="d-block text-muted" style={{ fontSize: '0.72rem' }}>{feature.description}</span>
                              )}
                            </label>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Modal>
  );
}

export default PlanEditorModal;