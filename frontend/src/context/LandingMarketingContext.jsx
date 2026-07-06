import { createContext, useContext, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { landingService } from '../services/landingService';
import { FEATURES as FALLBACK_FEATURES, PRICING_PLANS as FALLBACK_PLANS, STATS as FALLBACK_STATS } from '../pages/landing/landingData';

const LandingMarketingContext = createContext(null);

export function LandingMarketingProvider({ children }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['landing', 'marketing'],
    queryFn: () => landingService.getMarketingCatalog(),
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });

  const value = useMemo(() => ({
    plans: data?.plans?.length ? data.plans : null,
    features: data?.features?.length ? data.features : null,
    stats: data?.stats?.length ? data.stats : null,
    comparison: data?.comparison?.length ? data.comparison : null,
    platform: data?.platform || null,
    loading: isLoading,
    isLive: Boolean(data?.plans?.length),
    isError,
    fallbackFeatures: FALLBACK_FEATURES,
    fallbackPlans: FALLBACK_PLANS,
    fallbackStats: FALLBACK_STATS,
  }), [data, isLoading, isError]);

  return (
    <LandingMarketingContext.Provider value={value}>
      {children}
    </LandingMarketingContext.Provider>
  );
}

export function useLandingMarketing() {
  const ctx = useContext(LandingMarketingContext);
  if (!ctx) throw new Error('useLandingMarketing must be used within LandingMarketingProvider');
  return ctx;
}

export default LandingMarketingContext;