import { useEffect, useState, useCallback } from 'react';
import AOS from 'aos';
import 'aos/dist/aos.css';
import './landing.css';

import LandingLoader from '../../components/landing/LandingLoader';
import LandingNavbar from '../../components/landing/LandingNavbar';
import LandingHero from '../../components/landing/LandingHero';
import LandingShowcase from '../../components/landing/LandingShowcase';
import LandingFloatingUI from '../../components/landing/LandingFloatingUI';
import { LandingMarketingProvider } from '../../context/LandingMarketingContext';
import {
  LandingTrustedBy, LandingAdmissionVacancies, LandingFeatures, LandingWhy,
  LandingWorkflow, LandingPricing, LandingStats, LandingTestimonials,
  LandingCaseStudies, LandingSecurity, LandingMobile, LandingFAQ,
  LandingResources, LandingPremiumExtras, LandingCTA, LandingContact, LandingFooter,
} from '../../components/landing/LandingSections';

export function LandingPage() {
  const [loading, setLoading] = useState(true);
  const [theme, setTheme] = useState(() => localStorage.getItem('apex_landing_theme') || 'light');

  const onLoaderComplete = useCallback(() => setLoading(false), []);

  const toggleTheme = useCallback(() => {
    setTheme((t) => {
      const next = t === 'light' ? 'dark' : 'light';
      localStorage.setItem('apex_landing_theme', next);
      return next;
    });
  }, []);

  useEffect(() => {
    AOS.init({ duration: 700, once: true, offset: 80, easing: 'ease-out-cubic' });
  }, [loading]);

  useEffect(() => {
    document.documentElement.style.scrollBehavior = 'smooth';
    return () => { document.documentElement.style.scrollBehavior = ''; };
  }, []);

  return (
    <LandingMarketingProvider>
      <div className="apex-landing" data-landing-theme={theme}>
        {loading && <LandingLoader onComplete={onLoaderComplete} />}
        <LandingFloatingUI />
        <LandingNavbar theme={theme} onToggleTheme={toggleTheme} />
        <main>
          <LandingHero />
          <LandingTrustedBy />
          <LandingAdmissionVacancies />
          <LandingFeatures />
          <LandingShowcase theme={theme} />
          <LandingWhy />
          <LandingWorkflow />
          <LandingPricing />
          <LandingStats />
          <LandingTestimonials />
          <LandingCaseStudies />
          <LandingSecurity />
          <LandingMobile />
          <LandingPremiumExtras />
          <LandingFAQ />
          <LandingResources />
          <LandingCTA />
          <LandingContact />
        </main>
        <LandingFooter />
      </div>
    </LandingMarketingProvider>
  );
}

export default LandingPage;