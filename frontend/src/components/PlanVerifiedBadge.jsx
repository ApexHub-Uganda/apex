import { BADGE_DISPLAY_SIZES, getPlanBadgeVariant } from '../utils/planBadge';

export function PlanVerifiedBadge({
  planSlug,
  size = 'md',
  className = '',
}) {
  const variant = getPlanBadgeVariant(planSlug);
  if (!variant) return null;

  const dimension = BADGE_DISPLAY_SIZES[size] || BADGE_DISPLAY_SIZES.md;

  return (
    <img
      src={variant.badgeSrc}
      width={dimension}
      height={dimension}
      className={`plan-verified-seal plan-verified-seal--${size} ${className}`.trim()}
      alt=""
      title={`${variant.tierLabel} verified`}
      aria-label={`${variant.tierLabel} verified`}
      loading="lazy"
      decoding="async"
      draggable={false}
    />
  );
}

export default PlanVerifiedBadge;