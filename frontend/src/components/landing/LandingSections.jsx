import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { FiCheck, FiChevronDown, FiStar, FiMail, FiBell, FiSearch } from 'react-icons/fi';
import { resolveFeatureIcon } from '../../utils/featureIcons';
import { SCHOOL_MODULES } from '../../config/schoolModules';
import { useLandingMarketing } from '../../context/LandingMarketingContext';
import { landingService } from '../../services/landingService';
import {
  TRUSTED_LOGOS, WHY_BENEFITS, WORKFLOW_STEPS,
  TESTIMONIALS, CASE_STUDIES, SECURITY_ITEMS, MOBILE_APPS, FAQ_ITEMS,
  RESOURCES, INTEGRATIONS, ROADMAP_ITEMS, THEME_PRESETS,
  AWARDS, UPDATES, ONBOARDING_STEPS, FOOTER_LINKS, BRAND,
} from '../../pages/landing/landingData';

function useCounter(end, duration = 2000, decimals = 0, start = false) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!start) return;
    let startTime;
    const step = (ts) => {
      if (!startTime) startTime = ts;
      const p = Math.min((ts - startTime) / duration, 1);
      const eased = 1 - (1 - p) ** 3;
      setValue(Number((end * eased).toFixed(decimals)));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [end, duration, decimals, start]);
  return value;
}

function StatCounter({ stat, active }) {
  const val = useCounter(stat.value, 2200, stat.decimals || 0, active);
  if (stat.display) {
    return <h3>{active ? stat.display : '0'}</h3>;
  }
  const formatted = stat.decimals
    ? val.toFixed(stat.decimals)
    : Math.round(val).toLocaleString();
  const display = stat.suffix === 'M+'
    ? `${Math.round(val)}M+`
    : `${formatted}${stat.suffix || ''}`;
  return <h3>{display}</h3>;
}

export function LandingAdmissionVacancies() {
  const { data: vacancies = [], isLoading } = useQuery({
    queryKey: ['landing', 'admission-vacancies'],
    queryFn: () => landingService.getAdmissionVacancies(),
    staleTime: 60_000,
    retry: 1,
  });

  if (!isLoading && vacancies.length === 0) return null;

  return (
    <section className="lp-vacancies" id="admissions" aria-label="Open admissions">
      <div className="lp-container" data-aos="fade-up">
        <div className="text-center mb-4">
          <p className="lp-section-eyebrow mb-2">Admissions</p>
          <h2 className="lp-section-title">Open Grade Vacancies</h2>
          <p className="text-muted mb-0">
            Schools on Apex Hub publish live openings — apply directly through your institution.
          </p>
        </div>
        <div className="row g-3" aria-busy={isLoading}>
          {(isLoading ? Array.from({ length: 3 }, (_, i) => ({ id: `sk-${i}` })) : vacancies).map((vacancy) => (
            <div className="col-md-6 col-lg-4" key={vacancy.id}>
              <div className="lp-vacancy-card h-100 p-4">
                {isLoading ? (
                  <div className="placeholder-glow">
                    <span className="placeholder col-8 mb-2" />
                    <span className="placeholder col-12 mb-2" />
                    <span className="placeholder col-6" />
                  </div>
                ) : (
                  <>
                    <div className="small text-muted mb-1">{vacancy.school_name}</div>
                    <h5 className="fw-bold mb-2">{vacancy.title}</h5>
                    {vacancy.grade_levels && (
                      <div className="small mb-2"><strong>Grades:</strong> {vacancy.grade_levels}</div>
                    )}
                    {vacancy.description && (
                      <p className="text-muted small mb-3">{vacancy.description}</p>
                    )}
                    <div className="d-flex flex-wrap gap-2 small">
                      <span className="badge text-bg-primary-subtle border text-primary">
                        {vacancy.remaining_openings} opening{vacancy.remaining_openings === 1 ? '' : 's'}
                      </span>
                      {vacancy.application_deadline && (
                        <span className="badge text-bg-light border">
                          Deadline: {vacancy.application_deadline}
                        </span>
                      )}
                    </div>
                    {(vacancy.contact_email || vacancy.contact_phone) && (
                      <div className="small text-muted mt-3">
                        Contact: {vacancy.contact_email || vacancy.contact_phone}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function LandingTrustedBy() {
  const { data, isLoading } = useQuery({
    queryKey: ['landing', 'trusted-schools'],
    queryFn: () => landingService.getTrustedSchools(8),
    staleTime: 0,
    gcTime: 0,
    refetchOnMount: 'always',
    retry: 1,
  });

  const schools = data?.schools?.length
    ? data.schools
    : TRUSTED_LOGOS.map((name, index) => ({ id: `fallback-${index}`, name }));

  return (
    <section className="lp-trusted" aria-label="Trusted by">
      <div className="lp-container text-center" data-aos="fade-up">
        <p className="text-muted mb-0 small fw-medium">Trusted by educational institutions across Africa.</p>
        <div className="lp-trusted-logos" aria-busy={isLoading}>
          {schools.map((school) => (
            <span key={school.id} className="lp-trusted-logo">{school.name}</span>
          ))}
        </div>
      </div>
    </section>
  );
}

const FALLBACK_TITLE_CATEGORY = {
  Admissions: 'Admissions',
  Attendance: 'Attendance',
  Examinations: 'Examinations',
  'Academic Reports': 'Academics',
  Fees: 'Finance',
  Payroll: 'Human Resource',
  Inventory: 'Inventory',
  Library: 'Library',
  Transport: 'Transport',
  Hostel: 'Hostel',
  'Parent Portal': 'Portals',
  'Student Portal': 'Portals',
  'Teacher Portal': 'Portals',
  Analytics: 'Analytics',
  Communication: 'Communication',
  'AI Insights': 'Analytics',
  'Role Management': 'Core Management',
  'Multi-Campus': 'Core Management',
  'Custom Branding': 'Core Management',
  'Cloud Backup': 'Core Management',
};

function resolveFeatureCategory(featureKey, title, apiCategory) {
  if (apiCategory) return apiCategory;
  if (featureKey) {
    for (const mod of SCHOOL_MODULES) {
      if (mod.feature_keys?.includes(featureKey)) return mod.label;
      if (mod.children?.some((c) => c.feature_key === featureKey)) return mod.label;
    }
  }
  return FALLBACK_TITLE_CATEGORY[title] || 'Platform';
}

function groupFeaturesByCategory(rawItems) {
  const groups = new Map();
  rawItems.forEach((f) => {
    const category = resolveFeatureCategory(f.feature_key, f.title, f.category);
    if (!groups.has(category)) groups.set(category, []);
    groups.get(category).push({
      key: f.feature_key || f.title,
      title: f.title,
      desc: f.description || f.desc,
      icon: typeof f.icon === 'string' ? resolveFeatureIcon(f.icon) : f.icon,
    });
  });
  const moduleOrder = SCHOOL_MODULES.map((m) => m.label);
  return [...groups.entries()]
    .sort(([a], [b]) => {
      const ai = moduleOrder.indexOf(a);
      const bi = moduleOrder.indexOf(b);
      if (ai === -1 && bi === -1) return a.localeCompare(b);
      if (ai === -1) return 1;
      if (bi === -1) return -1;
      return ai - bi;
    })
    .map(([name, items]) => ({
      name,
      items,
      icon: SCHOOL_MODULES.find((m) => m.label === name)?.icon || 'FiGrid',
    }));
}

export function LandingFeatures() {
  const { features, fallbackFeatures, platform, loading, isLive } = useLandingMarketing();
  const [expanded, setExpanded] = useState(null);

  const rawItems = features || fallbackFeatures;
  const categories = groupFeaturesByCategory(
    rawItems.map((f) => ({
      ...f,
      title: f.title,
      feature_key: f.feature_key,
      category: f.category,
      description: f.description,
      desc: f.desc,
      icon: f.icon,
    })),
  );

  const totalFeatures = categories.reduce((n, c) => n + c.items.length, 0);

  const toggleCategory = (name) => {
    setExpanded((prev) => (prev === name ? null : name));
  };

  return (
    <section id="features" className="lp-section" aria-labelledby="features-heading">
      <div className="lp-container">
        <div className="lp-section-header" data-aos="fade-up">
          <span className="lp-eyebrow">Platform Capabilities</span>
          <h2 id="features-heading" className="lp-title">Everything Your Institution Needs</h2>
          <p className="lp-subtitle">
            {isLive
              ? `${platform?.feature_count || totalFeatures} capabilities organized by module — expand each row to explore.`
              : 'Integrated modules designed for real school operations — expand each category to explore.'}
            {loading && <span className="d-block small mt-1 text-muted">Loading features…</span>}
          </p>
        </div>

        <div className="lp-features-accordion" data-aos="fade-up">
          {categories.map((group, index) => {
            const isOpen = expanded === group.name;
            const GroupIcon = resolveFeatureIcon(group.icon);
            return (
              <div
                key={group.name}
                className={`lp-feature-category ${isOpen ? 'is-open' : ''}`}
              >
                <button
                  type="button"
                  className="lp-feature-category-trigger"
                  onClick={() => toggleCategory(group.name)}
                  aria-expanded={isOpen}
                  aria-controls={`feature-panel-${index}`}
                >
                  <span className="lp-feature-category-leading">
                    <span className="lp-feature-category-icon" aria-hidden>
                      <GroupIcon size={18} />
                    </span>
                    <span>
                      <span className="lp-feature-category-name">{group.name}</span>
                      <span className="lp-feature-category-count">
                        {group.items.length} {group.items.length === 1 ? 'feature' : 'features'}
                      </span>
                    </span>
                  </span>
                  <FiChevronDown
                    className="lp-feature-category-chevron"
                    aria-hidden
                  />
                </button>

                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      id={`feature-panel-${index}`}
                      className="lp-feature-category-panel"
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.28, ease: 'easeInOut' }}
                    >
                      <div className="lp-feature-row">
                        {group.items.map((f) => {
                          const Icon = typeof f.icon === 'function' ? f.icon : resolveFeatureIcon('FiGrid');
                          return (
                            <div key={f.key} className="lp-feature-row-item">
                              <div className="lp-feature-row-icon"><Icon size={16} /></div>
                              <div className="lp-feature-row-body">
                                <div className="lp-feature-row-title">{f.title}</div>
                                <div className="lp-feature-row-desc">{f.desc}</div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export function LandingWhy() {
  return (
    <section id="about" className="lp-section" style={{ background: 'var(--lp-gray-50)' }} aria-labelledby="why-heading">
      <div className="lp-container">
        <div className="lp-why-grid">
          <div data-aos="fade-right">
            <div className="lp-dashboard-main" style={{ transform: 'none' }}>
              <div className="lp-dashboard-topbar">
                <div className="lp-dashboard-dots">
                  <span style={{ background: '#EF4444' }} />
                  <span style={{ background: '#F59E0B' }} />
                  <span style={{ background: '#10B981' }} />
                </div>
              </div>
              <div className="p-4">
                <div className="lp-dash-stats mb-3">
                  <div className="lp-dash-stat"><div className="lp-dash-stat-label">Efficiency</div><div className="lp-dash-stat-value">+62%</div></div>
                  <div className="lp-dash-stat"><div className="lp-dash-stat-label">Time Saved</div><div className="lp-dash-stat-value">18hrs/wk</div></div>
                  <div className="lp-dash-stat"><div className="lp-dash-stat-label">Satisfaction</div><div className="lp-dash-stat-value">4.9/5</div></div>
                </div>
                <div className="p-3 rounded-3" style={{ background: 'color-mix(in srgb, var(--lp-primary) 8%, var(--lp-surface-raised))' }}>
                  <p className="small mb-0 fw-medium text-muted">Why institutions choose Apex Hub</p>
                  <p className="mb-0 fw-bold mt-1">Trusted. Simple. Complete.</p>
                </div>
              </div>
            </div>
          </div>
          <div data-aos="fade-left">
            <span className="lp-eyebrow">Why Apex Hub</span>
            <h2 id="why-heading" className="lp-title">Built for Modern Education</h2>
            <p className="lp-subtitle text-start mb-4">
              Enterprise power without enterprise complexity. Deploy in days, scale for decades.
            </p>
            <div className="lp-benefits-list">
              {WHY_BENEFITS.map((b) => {
                const Icon = b.icon;
                return (
                  <div key={b.title} className="lp-benefit-item">
                    <div className="lp-benefit-icon"><Icon size={18} /></div>
                    <div>
                      <div className="fw-semibold">{b.title}</div>
                      <div className="small text-muted">{b.desc}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function LandingWorkflow() {
  return (
    <section className="lp-section" aria-labelledby="workflow-heading">
      <div className="lp-container">
        <div className="lp-section-header" data-aos="fade-up">
          <span className="lp-eyebrow">How It Works</span>
          <h2 id="workflow-heading" className="lp-title">From Registration to Results</h2>
          <p className="lp-subtitle">A guided path that gets your institution running in days, not months.</p>
        </div>
        <div className="lp-workflow-track" data-aos="fade-up">
          {WORKFLOW_STEPS.map((s) => (
            <div key={s.step} className="lp-workflow-step">
              <div className="lp-workflow-num">{s.step}</div>
              <h3 className="h6 fw-bold">{s.title}</h3>
              <p className="small text-muted mb-0">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function LandingPricing() {
  const [yearly, setYearly] = useState(false);
  const { plans, fallbackPlans, loading, isLive } = useLandingMarketing();
  const planList = plans || fallbackPlans.map((p) => ({
    ...p,
    currency: 'USD',
    sms: p.sms,
    email: p.email,
    trial_days: 14,
    feature_count: p.features?.length,
  }));

  const formatPrice = (plan) => {
    const amount = yearly ? plan.yearly : plan.monthly;
    const symbol = plan.currency === 'USD' ? '$' : `${plan.currency} `;
    return `${symbol}${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
  };

  return (
    <section id="pricing" className="lp-section" style={{ background: 'var(--lp-gray-50)' }} aria-labelledby="pricing-heading">
      <div className="lp-container">
        <div className="lp-section-header" data-aos="fade-up">
          <span className="lp-eyebrow">Transparent Pricing</span>
          <h2 id="pricing-heading" className="lp-title">Plans That Scale With You</h2>
          <p className="lp-subtitle">
            {isLive ? 'Live plans from your Apex Hub subscription catalog.' : 'Choose the plan that fits your institution.'}
            {loading && <span className="d-block small mt-1">Loading plans…</span>}
          </p>
          <div className="lp-pricing-toggle mt-3">
            <button type="button" className={!yearly ? 'active' : ''} onClick={() => setYearly(false)}>Monthly</button>
            <button type="button" className={yearly ? 'active' : ''} onClick={() => setYearly(true)}>Yearly</button>
          </div>
        </div>
        <div className={`lp-pricing-grid lp-pricing-grid--${planList.length}`}>
          {planList.map((plan, i) => (
            <motion.div
              key={plan.id || plan.slug}
              className={`lp-pricing-card ${plan.recommended ? 'is-recommended' : ''}`}
              data-aos="fade-up"
              data-aos-delay={i * 80}
              whileHover={{ y: -6 }}
            >
              {plan.recommended && <span className="lp-pricing-badge">Recommended</span>}
              <h3 className="h5 fw-bold">{plan.name}</h3>
              <div className="lp-pricing-price mt-3">
                {formatPrice(plan)}
                <span>/{yearly ? 'yr' : 'mo'}</span>
              </div>
              <p className="lp-pricing-meta small text-muted mt-2 mb-0">
                {plan.students} students · {plan.users} staff · {plan.storage}
              </p>
              <ul className="lp-pricing-features">
                {(plan.features || []).slice(0, 4).map((f) => (
                  <li key={f}><FiCheck size={16} /> {f}</li>
                ))}
                {(plan.features?.length || 0) > 4 && (
                  <li className="lp-pricing-more">
                    +{(plan.features.length - 4)} more included
                  </li>
                )}
              </ul>
              <Link
                to={plan.cta === 'Contact Sales' ? '#contact' : '/register'}
                className={`lp-btn w-100 ${plan.recommended ? 'lp-btn-primary' : 'lp-btn-secondary'}`}
              >
                {plan.cta || 'Start Free Trial'}
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function LandingStats() {
  const ref = useRef(null);
  const [active, setActive] = useState(false);
  const { stats, fallbackStats, isLive } = useLandingMarketing();
  const statList = stats || fallbackStats;

  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setActive(true); }, { threshold: 0.3 });
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);

  return (
    <section className="lp-section" aria-label="Statistics" ref={ref}>
      <div className="lp-container">
        {isLive && (
          <p className="text-center small text-muted mb-4" data-aos="fade-up">
            Live platform metrics from registered institutions
          </p>
        )}
        <div className="lp-stats-grid">
          {statList.map((s) => (
            <div key={s.label} className="lp-stat-item" data-aos="zoom-in">
              <StatCounter stat={s} active={active} />
              <p>{s.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function LandingTestimonials() {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setIdx((i) => (i + 1) % TESTIMONIALS.length), 5000);
    return () => clearInterval(t);
  }, []);
  const t = TESTIMONIALS[idx];
  return (
    <section id="testimonials" className="lp-section" style={{ background: 'var(--lp-gray-50)' }} aria-labelledby="testimonials-heading">
      <div className="lp-container">
        <div className="lp-section-header" data-aos="fade-up">
          <span className="lp-eyebrow">Testimonials</span>
          <h2 id="testimonials-heading" className="lp-title">Loved by Educators</h2>
        </div>
        <AnimatePresence mode="wait">
          <motion.div
            key={idx}
            className="lp-testimonial-card mx-auto"
            style={{ maxWidth: 640 }}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
          >
            <div className="d-flex align-items-center gap-3">
              <div className="lp-testimonial-avatar">{t.avatar}</div>
              <div>
                <div className="fw-bold">{t.name}</div>
                <div className="small text-muted">{t.role}, {t.school}</div>
              </div>
            </div>
            <div className="lp-testimonial-stars" aria-label={`${t.rating} stars`}>
              {Array.from({ length: t.rating }).map((_, i) => <FiStar key={i} size={16} fill="currentColor" />)}
            </div>
            <p className="mb-0 fst-italic text-muted">&ldquo;{t.quote}&rdquo;</p>
          </motion.div>
        </AnimatePresence>
        <div className="d-flex justify-content-center gap-2 mt-4">
          {TESTIMONIALS.map((_, i) => (
            <button
              key={i}
              type="button"
              className="btn btn-sm rounded-circle p-0"
              style={{ width: 8, height: 8, background: i === idx ? 'var(--lp-primary)' : 'var(--lp-gray-200)', border: 'none' }}
              onClick={() => setIdx(i)}
              aria-label={`Testimonial ${i + 1}`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

export function LandingCaseStudies() {
  return (
    <section className="lp-section" aria-labelledby="cases-heading">
      <div className="lp-container">
        <div className="lp-section-header" data-aos="fade-up">
          <span className="lp-eyebrow">Case Studies</span>
          <h2 id="cases-heading" className="lp-title">Real Results, Real Schools</h2>
        </div>
        <div className="row g-4">
          {CASE_STUDIES.map((c, i) => (
            <div key={c.school} className="col-md-4" data-aos="fade-up" data-aos-delay={i * 80}>
              <div className="lp-case-card">
                <h3 className="h6 fw-bold">{c.school}</h3>
                <p className="small text-muted mb-1"><strong>Before:</strong> {c.before}</p>
                <p className="small text-muted mb-0"><strong>After:</strong> {c.after}</p>
                <div className="lp-case-metric">{c.metric}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function LandingSecurity() {
  return (
    <section className="lp-section" style={{ background: 'var(--lp-gray-50)' }} aria-labelledby="security-heading">
      <div className="lp-container">
        <div className="lp-section-header" data-aos="fade-up">
          <span className="lp-eyebrow">Security & Compliance</span>
          <h2 id="security-heading" className="lp-title">Enterprise-Grade Protection</h2>
          <p className="lp-subtitle">Your data is protected with the same standards trusted by leading SaaS platforms.</p>
        </div>
        <div className="lp-security-grid">
          {SECURITY_ITEMS.map((s, i) => {
            const Icon = s.icon;
            return (
              <div key={s.title} className="lp-security-card" data-aos="fade-up" data-aos-delay={i * 50}>
                <div className="lp-feature-icon mb-2"><Icon size={20} /></div>
                <h3 className="h6 fw-bold">{s.title}</h3>
                <p className="small text-muted mb-0">{s.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export function LandingMobile() {
  return (
    <section className="lp-section" aria-labelledby="mobile-heading">
      <div className="lp-container">
        <div className="lp-section-header" data-aos="fade-up">
          <span className="lp-eyebrow">Mobile Experience</span>
          <h2 id="mobile-heading" className="lp-title">Power in Every Pocket</h2>
          <p className="lp-subtitle">Fully responsive portals for parents, teachers, students, and finance teams.</p>
        </div>
        <div className="lp-mobile-row">
          {MOBILE_APPS.map((app, i) => (
            <motion.figure
              key={app.id}
              className="lp-mobile-shot"
              data-aos="fade-up"
              data-aos-delay={i * 100}
              whileHover={{ y: -8 }}
            >
              <img
                className="lp-mobile-shot-image"
                src={app.image}
                alt={app.alt || app.name}
                loading="lazy"
                decoding="async"
              />
              <figcaption className="lp-mobile-shot-caption">{app.name}</figcaption>
            </motion.figure>
          ))}
        </div>
      </div>
    </section>
  );
}

export function LandingFAQ() {
  const [open, setOpen] = useState(0);
  return (
    <section className="lp-section" style={{ background: 'var(--lp-gray-50)' }} aria-labelledby="faq-heading">
      <div className="lp-container" style={{ maxWidth: 760 }}>
        <div className="lp-section-header" data-aos="fade-up">
          <span className="lp-eyebrow">FAQ</span>
          <h2 id="faq-heading" className="lp-title">Frequently Asked Questions</h2>
        </div>
        {FAQ_ITEMS.map((item, i) => (
          <div key={item.q} className="lp-faq-item" data-aos="fade-up">
            <button
              type="button"
              className="lp-faq-trigger"
              onClick={() => setOpen(open === i ? -1 : i)}
              aria-expanded={open === i}
            >
              {item.q}
              <FiChevronDown style={{ transform: open === i ? 'rotate(180deg)' : 'none', transition: '0.3s' }} />
            </button>
            <AnimatePresence>
              {open === i && (
                <motion.div className="lp-faq-body" initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }}>
                  <p>{item.a}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>
    </section>
  );
}

export function LandingResources() {
  return (
    <section id="resources" className="lp-section" aria-labelledby="resources-heading">
      <div className="lp-container">
        <div className="lp-section-header" data-aos="fade-up">
          <span className="lp-eyebrow">Resources</span>
          <h2 id="resources-heading" className="lp-title">Learn, Build, and Grow</h2>
        </div>
        <div className="row g-3">
          {RESOURCES.map((r, i) => (
            <div key={r.title} className="col-md-4" data-aos="fade-up" data-aos-delay={i * 50}>
              <a href={r.href} className="lp-feature-card d-block text-decoration-none h-100">
                <h3 className="h6">{r.title}</h3>
                <p>{r.desc}</p>
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function LandingPremiumExtras() {
  const [notifIdx, setNotifIdx] = useState(0);
  const notifs = [
    { icon: FiBell, text: 'Fee payment received — Grade 10-A' },
    { icon: FiMail, text: 'Parent meeting reminder sent' },
    { icon: FiCheck, text: 'Attendance marked for 32 classes' },
  ];
  useEffect(() => {
    const t = setInterval(() => setNotifIdx((i) => (i + 1) % notifs.length), 3000);
    return () => clearInterval(t);
  }, []);

  return (
    <>
      <section className="lp-section" style={{ background: 'var(--lp-gray-50)' }} aria-labelledby="extras-heading">
        <div className="lp-container">
          <div className="lp-section-header" data-aos="fade-up">
            <span className="lp-eyebrow">Enterprise Features</span>
            <h2 id="extras-heading" className="lp-title">Built for Scale</h2>
          </div>
          <div className="lp-extras-grid mb-5">
            <div className="lp-extra-card" data-aos="fade-up">
              <h3 className="h6 fw-bold mb-3">Customer Success Metrics</h3>
              <div className="row g-2 text-center">
                <div className="col-4"><div className="lp-dash-stat"><div className="lp-dash-stat-value" style={{ fontSize: '1.1rem' }}>98%</div><div className="lp-dash-stat-label">Retention</div></div></div>
                <div className="col-4"><div className="lp-dash-stat"><div className="lp-dash-stat-value" style={{ fontSize: '1.1rem' }}>4.9</div><div className="lp-dash-stat-label">NPS Score</div></div></div>
                <div className="col-4"><div className="lp-dash-stat"><div className="lp-dash-stat-value" style={{ fontSize: '1.1rem' }}>24h</div><div className="lp-dash-stat-label">Support SLA</div></div></div>
              </div>
            </div>
            <div className="lp-extra-card" data-aos="fade-up" data-aos-delay="80">
              <h3 className="h6 fw-bold mb-3">Live Notifications</h3>
              <div className="lp-notif-sim">
                {notifs.map((n, i) => {
                  const Icon = n.icon;
                  return (
                    <div key={n.text} className="lp-notif-item" style={{ opacity: i === notifIdx ? 1 : 0.4 }}>
                      <Icon size={16} color="var(--lp-primary)" />
                      {n.text}
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="lp-extra-card" data-aos="fade-up">
              <h3 className="h6 fw-bold mb-3">Global Search Preview</h3>
              <div className="d-flex align-items-center gap-2 p-2 rounded-3 border mb-2">
                <FiSearch className="text-muted" />
                <span className="small text-muted">Search students, staff, classes…</span>
              </div>
              <div className="small text-muted">Instant results across your entire institution.</div>
            </div>
            <div className="lp-extra-card" data-aos="fade-up" data-aos-delay="80">
              <h3 className="h6 fw-bold mb-3">AI-Powered Insights</h3>
              <p className="small text-muted mb-2">Predictive alerts for at-risk students, fee defaults, and attendance patterns.</p>
              <span className="lp-integration-pill">Coming Q3 2026</span>
            </div>
          </div>

          <div className="row g-4 mb-5">
            <div className="col-lg-6" data-aos="fade-right">
              <h3 className="h5 fw-bold mb-3">Integrations</h3>
              <div className="d-flex flex-wrap gap-2">
                {INTEGRATIONS.map((name) => (
                  <span key={name} className="lp-integration-pill">{name}</span>
                ))}
              </div>
            </div>
            <div className="col-lg-6" data-aos="fade-left">
              <h3 className="h5 fw-bold mb-3">Product Roadmap</h3>
              {ROADMAP_ITEMS.map((r) => (
                <div key={r.title} className="d-flex justify-content-between align-items-center py-2 border-bottom">
                  <div><span className="small text-muted">{r.quarter}</span><div className="fw-medium">{r.title}</div></div>
                  <span className="lp-integration-pill">{r.status}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="row g-4 mb-5">
            <div className="col-md-6" data-aos="fade-up">
              <h3 className="h5 fw-bold mb-3">Multi-School SaaS Architecture</h3>
              <div className="lp-arch-diagram">
                <div className="lp-arch-layer"><span className="lp-arch-node">School A</span><span className="lp-arch-node">School B</span><span className="lp-arch-node">School C</span></div>
                <div className="lp-arch-connector" />
                <div className="lp-arch-layer"><span className="lp-arch-node">Apex Hub Cloud</span></div>
                <div className="lp-arch-connector" />
                <div className="lp-arch-layer"><span className="lp-arch-node">Shared Infrastructure</span><span className="lp-arch-node">Isolated Data</span></div>
              </div>
            </div>
            <div className="col-md-6" data-aos="fade-up" data-aos-delay="80">
              <h3 className="h5 fw-bold mb-3">Theme Customization</h3>
              <div className="row g-2">
                {THEME_PRESETS.map((t) => (
                  <div key={t.name} className="col-4">
                    <div className="lp-theme-swatch" style={{ background: `linear-gradient(135deg, ${t.primary}, ${t.secondary})` }}>
                      {t.name}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="row g-4">
            <div className="col-md-6" data-aos="fade-up">
              <h3 className="h5 fw-bold mb-3">Awards & Certifications</h3>
              <div className="d-flex flex-wrap gap-2">
                {AWARDS.map((a) => <span key={a} className="lp-integration-pill">{a}</span>)}
              </div>
            </div>
            <div className="col-md-6" data-aos="fade-up" data-aos-delay="80">
              <h3 className="h5 fw-bold mb-3">Recent Updates</h3>
              {UPDATES.map((u) => (
                <div key={u.title} className="py-2 border-bottom">
                  <span className="small text-muted">{u.date}</span>
                  <div className="fw-medium">{u.title}</div>
                  <div className="small text-muted">{u.desc}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="lp-extra-card mt-5" data-aos="fade-up">
            <h3 className="h5 fw-bold mb-3 text-center">Client Onboarding Process</h3>
            <div className="d-flex flex-wrap justify-content-center gap-2">
              {ONBOARDING_STEPS.map((step, i) => (
                <span key={step} className="lp-integration-pill">
                  {i + 1}. {step}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

export function LandingCTA() {
  return (
    <section className="lp-cta" aria-labelledby="cta-heading">
      <div className="lp-container" data-aos="zoom-in">
        <h2 id="cta-heading" className="lp-title">Ready to modernize your institution?</h2>
        <p className="lp-subtitle mx-auto mb-4" style={{ maxWidth: 520 }}>
          Join hundreds of schools already running on Apex Hub. Start your free trial today.
        </p>
        <div className="d-flex flex-wrap justify-content-center gap-3">
          <Link to="/register" className="lp-btn lp-btn-coral">Start Free Trial</Link>
          <a href="#contact" className="lp-btn lp-btn-secondary" style={{ color: 'white', borderColor: 'rgba(255,255,255,0.4)' }}>Schedule Demo</a>
        </div>
      </div>
    </section>
  );
}

export function LandingContact() {
  return (
    <section id="contact" className="lp-section" aria-labelledby="contact-heading">
      <div className="lp-container">
        <div className="row g-4 align-items-center">
          <div className="col-lg-6" data-aos="fade-right">
            <span className="lp-eyebrow">Contact Sales</span>
            <h2 id="contact-heading" className="lp-title">Let&apos;s Talk About Your School</h2>
            <p className="lp-subtitle text-start">
              Our team will help you choose the right plan, migrate your data, and train your staff.
            </p>
            <p className="small text-muted">sales@apexhub.io · +254 700 000 000</p>
          </div>
          <div className="col-lg-6" data-aos="fade-left">
            <form className="lp-extra-card" onSubmit={(e) => e.preventDefault()}>
              <div className="row g-3">
                <div className="col-md-6"><input className="form-control" placeholder="Full name" required aria-label="Full name" /></div>
                <div className="col-md-6"><input className="form-control" type="email" placeholder="Email" required aria-label="Email" /></div>
                <div className="col-12"><input className="form-control" placeholder="Institution name" required aria-label="Institution" /></div>
                <div className="col-12"><textarea className="form-control" rows={3} placeholder="Tell us about your needs" aria-label="Message" /></div>
                <div className="col-12"><button type="submit" className="lp-btn lp-btn-primary w-100">Request Demo</button></div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}

export function LandingFooter() {
  return (
    <footer className="lp-footer" role="contentinfo">
      <div className="lp-container">
        <div className="row g-4">
          <div className="col-lg-4">
            <div className="lp-logo mb-3">
              <span className="lp-logo-mark">A</span>
              <span><span className="lp-logo-text text-white">{BRAND.name}</span><span className="lp-logo-tag">{BRAND.tagline}</span></span>
            </div>
            <p className="small">The complete cloud ERP for educational institutions across Africa and beyond.</p>
            <form className="mt-3" onSubmit={(e) => e.preventDefault()}>
              <label className="small d-block mb-2">Newsletter</label>
              <div className="d-flex gap-2">
                <input className="form-control form-control-sm" type="email" placeholder="Your email" aria-label="Newsletter email" />
                <button type="submit" className="lp-btn lp-btn-primary btn-sm">Subscribe</button>
              </div>
            </form>
          </div>
          {Object.entries(FOOTER_LINKS).map(([group, links]) => (
            <div key={group} className="col-6 col-lg-2">
              <h6>{group}</h6>
              <ul className="list-unstyled d-flex flex-column gap-2">
                {links.map((l) => <li key={l}><a href={`#${l.toLowerCase()}`}>{l}</a></li>)}
              </ul>
            </div>
          ))}
        </div>
        <div className="lp-footer-bottom">
          <span>&copy; 2026 {BRAND.name}. All rights reserved.</span>
          <nav className="lp-footer-bottom-links" aria-label="Footer legal and social">
            <a href="#privacy">Privacy</a>
            <Link to="/terms">Terms</Link>
            <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" aria-label="Twitter">Twitter</a>
            <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn">LinkedIn</a>
          </nav>
        </div>
      </div>
    </footer>
  );
}