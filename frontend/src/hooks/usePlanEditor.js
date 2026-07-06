import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { featuresService, plansService } from '../services/moduleService';

export const TIER_ORDER = ['free_trial', 'basic', 'premium', 'premium_plus'];
export const TIER_LABELS = {
  free_trial: 'Free Trial',
  basic: 'Basic',
  premium: 'Premium',
  premium_plus: 'Premium Plus',
};

export const LIMIT_FIELDS = [
  { name: 'max_storage_mb', label: 'Storage Limit (MB)', type: 'number' },
  { name: 'max_sms_monthly', label: 'SMS / Month', type: 'number' },
  { name: 'max_emails_monthly', label: 'Emails / Month', type: 'number' },
  { name: 'trial_days', label: 'Trial Duration (days)', type: 'number' },
  { name: 'grace_period_days', label: 'Grace Period (days)', type: 'number' },
];

export const emptyPlanForm = () => ({
  name: '',
  slug: '',
  description: '',
  price_monthly: '',
  price_yearly: '',
  is_active: true,
  is_public: true,
  sort_order: 0,
  max_branches: 1,
  max_storage_mb: 1024,
  max_sms_monthly: 0,
  max_emails_monthly: 500,
  trial_days: 14,
  grace_period_days: 7,
});

export function usePlanEditor(plan, { enabled = true } = {}) {
  const [form, setForm] = useState(emptyPlanForm());
  const [selectedFeatures, setSelectedFeatures] = useState(new Set());
  const [expanded, setExpanded] = useState({});

  const { data: catalog = [], isLoading: catalogLoading } = useQuery({
    queryKey: ['feature-catalog'],
    queryFn: () => featuresService.getCatalog(),
    enabled,
    staleTime: 5 * 60 * 1000,
  });

  const { data: allPlans = [] } = useQuery({
    queryKey: ['plans-manage'],
    queryFn: () => plansService.list(),
    enabled,
    staleTime: 60 * 1000,
  });

  useEffect(() => {
    if (!enabled) return;
    if (plan) {
      setForm({
        ...emptyPlanForm(),
        name: plan.name ?? '',
        slug: plan.slug ?? '',
        description: plan.description ?? '',
        price_monthly: plan.price_monthly ?? '',
        price_yearly: plan.price_yearly ?? '',
        is_active: plan.is_active ?? true,
        is_public: plan.is_public ?? true,
        sort_order: plan.sort_order ?? 0,
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
          .filter(([key, enabledFlag]) => enabledFlag && key.includes('_'))
          .map(([key]) => key),
      );
      setSelectedFeatures(keys);
    } else {
      setForm(emptyPlanForm());
      setSelectedFeatures(new Set());
    }
    const collapsed = {};
    catalog.forEach((cat) => { collapsed[cat.slug] = false; });
    setExpanded(collapsed);
  }, [enabled, plan, catalog]);

  const activeSlug = (plan?.slug || form.slug || '').trim().toLowerCase();

  const inheritedFeatureKeys = useMemo(() => {
    const idx = TIER_ORDER.indexOf(activeSlug);
    if (idx <= 0) return new Set();
    const keys = new Set(plan?.inherited_feature_keys || []);
    for (let i = 0; i < idx; i += 1) {
      const tierPlan = allPlans.find((p) => p.slug === TIER_ORDER[i]);
      if (!tierPlan) continue;
      (tierPlan.inherited_feature_keys || []).forEach((key) => keys.add(key));
      (tierPlan.exclusive_feature_keys || []).forEach((key) => keys.add(key));
      (tierPlan.enabled_features_detail || []).forEach((feature) => keys.add(feature.feature_key));
    }
    return keys;
  }, [activeSlug, allPlans, plan?.inherited_feature_keys]);

  const parentTierLabel = useMemo(() => {
    const idx = TIER_ORDER.indexOf(activeSlug);
    if (idx <= 0) return null;
    return TIER_LABELS[TIER_ORDER[idx - 1]];
  }, [activeSlug]);

  useEffect(() => {
    if (!inheritedFeatureKeys.size) return;
    setSelectedFeatures((prev) => new Set([...prev, ...inheritedFeatureKeys]));
  }, [inheritedFeatureKeys]);

  const totalFeatures = useMemo(
    () => catalog.reduce((sum, cat) => sum + (cat.features?.length || 0), 0),
    [catalog],
  );

  const exclusiveCount = useMemo(
    () => [...selectedFeatures].filter((key) => !inheritedFeatureKeys.has(key)).length,
    [selectedFeatures, inheritedFeatureKeys],
  );

  const updateField = (name, value) => {
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const toggleFeature = (featureKey) => {
    if (inheritedFeatureKeys.has(featureKey)) return;
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
        if (inheritedFeatureKeys.has(key)) {
          next.add(key);
        } else if (selectAll) {
          next.add(key);
        } else {
          next.delete(key);
        }
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

  const getCategoryMeta = (category) => {
    const keys = category.features.map((f) => f.feature_key || f.slug);
    const selected = keys.filter((key) => selectedFeatures.has(key));
    const inherited = keys.filter((key) => inheritedFeatureKeys.has(key));
    const inheritedSelected = selected.filter((key) => inheritedFeatureKeys.has(key));
    const additionalSelected = selected.length - inheritedSelected.length;
    const allInherited = keys.length > 0 && inherited.length === keys.length;
    const fullyInheritedSelected = selected.length > 0 && additionalSelected === 0;
    return {
      selectedCount: selected.length,
      totalCount: keys.length,
      inheritedCount: inherited.length,
      additionalSelected,
      allInherited,
      fullyInheritedSelected,
    };
  };

  const expandAllModules = () => {
    const open = {};
    catalog.forEach((cat) => { open[cat.slug] = true; });
    setExpanded(open);
  };

  const collapseAllModules = () => {
    const closed = {};
    catalog.forEach((cat) => { closed[cat.slug] = false; });
    setExpanded(closed);
  };

  const buildPayload = () => ({
    ...form,
    price_monthly: Number(form.price_monthly) || 0,
    price_yearly: Number(form.price_yearly) || Number(form.price_monthly) * 10 || 0,
    max_students: 0,
    max_staff: 0,
    max_parents: 0,
    max_branches: 0,
    enabled_feature_keys: Array.from(selectedFeatures),
  });

  return {
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
    isNew: !plan,
  };
}