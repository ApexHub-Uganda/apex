import PlanVerifiedBadge from './PlanVerifiedBadge';
import { getPlanDisplayName } from '../utils/planBadge';

export function PlanNameWithBadge({
  planSlug,
  planName,
  size = 'sm',
  className = '',
  nameClassName = '',
  as: Component = 'span',
}) {
  const label = getPlanDisplayName(planSlug, planName);

  return (
    <Component className={`verified-name-inline verified-name-inline--${size} ${nameClassName} ${className}`.trim()}>
      <span className="verified-name-inline-label">{label}</span>
      <PlanVerifiedBadge planSlug={planSlug} size={size} />
    </Component>
  );
}

export default PlanNameWithBadge;