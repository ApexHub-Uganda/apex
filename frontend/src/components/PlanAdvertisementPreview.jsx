import { Link } from 'react-router-dom';
import { FiArrowUpRight, FiCheck, FiTrendingUp } from 'react-icons/fi';
import { getPlanMeta } from '../config/schoolDashboard';
import { buildUpgradePath } from '../utils/upgradePaths';

export function PlanAdvertisementPreview({ item, compact = false }) {
  if (!item) return null;

  const meta = item.metadata || {};
  const suggestedSlug = meta.suggested_plan_slug;
  const planMeta = suggestedSlug ? getPlanMeta(suggestedSlug) : null;
  const highlights = meta.highlights || [];

  return (
    <div className={`plan-ad-preview ${compact ? 'plan-ad-preview--compact' : ''}`}>
      <div className="plan-ad-preview-badge-row">
        <span className="plan-ad-preview-eyebrow">
          <FiTrendingUp size={13} />
          Plan upgrade
        </span>
        {meta.target_plan_name && (
          <span className="plan-ad-preview-target small text-muted">
            For {meta.target_plan_name} schools
          </span>
        )}
      </div>

      {meta.headline && (
        <div className="plan-ad-preview-headline">{meta.headline}</div>
      )}

      <div className="plan-ad-preview-title">{item.title}</div>
      <p className="plan-ad-preview-message">{item.message}</p>

      {suggestedSlug && planMeta && (
        <span className={`school-plan-badge ${planMeta.badgeClass} plan-ad-preview-plan-badge`}>
          Suggested: {meta.suggested_plan_name || planMeta.label}
        </span>
      )}

      {highlights.length > 0 && (
        <ul className="plan-ad-preview-highlights">
          {highlights.map((point) => (
            <li key={point}>
              <FiCheck size={13} />
              <span>{point}</span>
            </li>
          ))}
        </ul>
      )}

      {!compact && (
        <Link
          to={buildUpgradePath(suggestedSlug)}
          className="plan-ad-preview-cta text-decoration-none"
          onClick={(e) => e.stopPropagation()}
        >
          <span>{meta.cta_label || 'Explore upgrade'}</span>
          <FiArrowUpRight size={14} />
        </Link>
      )}
    </div>
  );
}

export default PlanAdvertisementPreview;