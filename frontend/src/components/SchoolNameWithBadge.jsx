import PlanVerifiedBadge from './PlanVerifiedBadge';

export function SchoolNameWithBadge({
  name,
  planSlug,
  size = 'md',
  className = '',
  nameClassName = '',
  as: Component = 'span',
}) {
  if (!name) return null;

  return (
    <Component className={`verified-name-inline verified-name-inline--${size} ${nameClassName} ${className}`.trim()}>
      <span className="verified-name-inline-label">{name}</span>
      <PlanVerifiedBadge planSlug={planSlug} size={size} />
    </Component>
  );
}

export default SchoolNameWithBadge;