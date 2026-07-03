import { buildRouteFeatureMap } from './schoolModules';

/** Maps school-admin route paths to subscription feature keys. */
export const SCHOOL_ROUTE_FEATURES = buildRouteFeatureMap();

export const getFeatureKeyForPath = (pathname) => {
  const relative = pathname.replace('/school-admin', '').replace(/^\//, '');
  if (!relative) return SCHOOL_ROUTE_FEATURES[''];
  if (SCHOOL_ROUTE_FEATURES[relative]) return SCHOOL_ROUTE_FEATURES[relative];
  const segment = relative.split('/')[0];
  return SCHOOL_ROUTE_FEATURES[segment] || null;
};