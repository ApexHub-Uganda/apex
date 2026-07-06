import { CORE_FEATURE_KEYS } from '../config/navigation';

export function canAccessNavFeature(featureKey, canAccessFeature, isSchoolAdmin) {
  if (!featureKey) return true;
  if (isSchoolAdmin) return true;
  if (CORE_FEATURE_KEYS.includes(featureKey)) return true;
  return canAccessFeature(featureKey, false);
}

/**
 * Filter sub-module links using API-provided can_read when available.
 * Parent modules stay visible as long as at least one child remains.
 */
export function filterNavChildren(children = [], canAccessFeature, isSchoolAdmin) {
  if (isSchoolAdmin) return children;

  return children.filter((child) => {
    if (child.can_read === false) return false;
    if (child.can_read === true) return true;
    return canAccessNavFeature(child.feature_key, canAccessFeature, isSchoolAdmin);
  });
}

/** Sub-modules only — no synthetic Overview links. */
export function buildAccessibleSubLinks(item, { canAccessFeature, isSchoolAdmin }) {
  return filterNavChildren(item.children, canAccessFeature, isSchoolAdmin);
}

/** First allowed sub-module path (never a hub overview). */
export function getModuleEntryPath(module) {
  const children = module?.children || [];
  if (!children.length) return module?.path || null;
  return children[0]?.path || module?.path || null;
}

export function filterSchoolAdminNavItems(items = [], { canAccessFeature, isSchoolAdmin }) {
  const filtered = [];

  items.forEach((item) => {
    if (item.divider) {
      if (filtered.length > 0 && !filtered[filtered.length - 1]?.divider) {
        filtered.push(item);
      }
      return;
    }

    const hasChildNav = Array.isArray(item.children) && item.children.length > 0;
    if (hasChildNav) {
      const children = buildAccessibleSubLinks(item, { canAccessFeature, isSchoolAdmin });
      if (!children.length) return;
      filtered.push({ ...item, children });
      return;
    }

    if (item.featureKey && !canAccessNavFeature(item.featureKey, canAccessFeature, isSchoolAdmin)) {
      return;
    }

    filtered.push(item);
  });

  while (filtered.length > 0 && filtered[filtered.length - 1]?.divider) {
    filtered.pop();
  }

  return filtered;
}