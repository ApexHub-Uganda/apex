export const VERIFIED_PLAN_SLUGS = ['basic', 'premium', 'premium_plus'];

export const BADGE_ASSET_BASE = '/assets/badges';

export const PLAN_BADGE_VARIANTS = {
  basic: {
    slug: 'basic',
    tierLabel: 'Basic',
    badgeSrc: `${BADGE_ASSET_BASE}/verified-basic.svg`,
  },
  premium: {
    slug: 'premium',
    tierLabel: 'Premium',
    badgeSrc: `${BADGE_ASSET_BASE}/verified-premium.svg`,
  },
  premium_plus: {
    slug: 'premium_plus',
    tierLabel: 'Premium Plus',
    badgeSrc: `${BADGE_ASSET_BASE}/verified-premium-plus.svg`,
  },
};

export const BADGE_DISPLAY_SIZES = {
  sm: 18,
  md: 22,
  lg: 26,
};

export const normalizePlanSlug = (value) => {
  if (!value) return null;
  return String(value).trim().toLowerCase().replace(/\s+/g, '_');
};

export const isTopTierPlanSlug = (planSlug) => normalizePlanSlug(planSlug) === 'premium_plus';

export const getPlanBadgeVariant = (planSlug) => {
  const slug = normalizePlanSlug(planSlug);
  if (!slug || slug === 'free_trial') return null;
  return PLAN_BADGE_VARIANTS[slug] || null;
};

export const shouldShowPlanVerifiedBadge = (planSlug) => Boolean(getPlanBadgeVariant(planSlug));

const PLAN_DISPLAY_NAMES = {
  free_trial: 'Free Trial',
  basic: 'Basic',
  premium: 'Premium',
  premium_plus: 'Premium Plus',
};

export const getPlanDisplayName = (planSlug, planName) => {
  if (planName?.trim()) return planName.trim();
  const slug = normalizePlanSlug(planSlug);
  if (slug && PLAN_DISPLAY_NAMES[slug]) return PLAN_DISPLAY_NAMES[slug];
  if (slug) {
    return slug
      .split('_')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');
  }
  return 'Your Plan';
};