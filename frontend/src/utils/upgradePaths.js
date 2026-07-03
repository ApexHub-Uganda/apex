export const UPGRADE_PATH = '/school-admin/upgrade';

export function buildUpgradePath(planSlug) {
  if (!planSlug) return UPGRADE_PATH;
  return `${UPGRADE_PATH}?plan=${encodeURIComponent(planSlug)}`;
}