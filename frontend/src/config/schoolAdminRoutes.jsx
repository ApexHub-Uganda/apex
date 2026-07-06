import { Route } from 'react-router-dom';
import ModuleHub from '../pages/school-admin/ModuleHub';
import SubModulePage from '../pages/school-admin/SubModulePage';
import FeatureGate from '../components/FeatureGate';
import ModuleHubGate from '../components/ModuleHubGate';
import { SCHOOL_MODULES } from './schoolModules';

const Gated = ({ featureKey, children }) => (
  <FeatureGate featureKey={featureKey}>{children}</FeatureGate>
);

/** Paths served by dedicated page components — skip SubModulePage generation. */
const DEDICATED_SEGMENTS = new Set([
  '', 'students', 'students/new', 'parents', 'parents/new', 'staff', 'classes',
  'academics/terms', 'attendance', 'finance', 'library',
  'hostel', 'transport', 'inventory', 'hr', 'hr/staffs', 'hr/staffs/new', 'payroll', 'reports',
  'communication', 'settings', 'settings/plans', 'notifications',
  'examinations/marks',
]);

/** Modules that use ModuleHub as their landing page. */
const HUB_MODULE_KEYS = new Set([
  'core_management', 'academics', 'admissions', 'examinations',
  'events', 'analytics', 'support',
]);

export function renderModuleHubRoutes() {
  return SCHOOL_MODULES
    .filter((mod) => HUB_MODULE_KEYS.has(mod.key))
    .map((mod) => {
      const segment = mod.path.replace('/school-admin/', '');
      return (
        <Route
          key={`hub-${mod.key}`}
          path={segment}
          element={(
            <ModuleHubGate moduleKey={mod.key}>
              <ModuleHub moduleKey={mod.key} />
            </ModuleHubGate>
          )}
        />
      );
    });
}

export function renderChildSubRoutes() {
  const routes = [];
  const seen = new Set();

  SCHOOL_MODULES.forEach((mod) => {
    (mod.children || []).forEach((child) => {
      const segment = child.path.replace('/school-admin/', '');
      if (!segment || DEDICATED_SEGMENTS.has(segment) || seen.has(segment)) return;
      seen.add(segment);
      routes.push(
        <Route
          key={`child-${segment}`}
          path={segment}
          element={(
            <Gated featureKey={child.feature_key}>
              <SubModulePage title={child.label} featureKey={child.feature_key} />
            </Gated>
          )}
        />,
      );
    });
  });

  return routes;
}