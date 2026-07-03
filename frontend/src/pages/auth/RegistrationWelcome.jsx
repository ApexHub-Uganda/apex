import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  FiMail, FiCheckCircle, FiAlertTriangle, FiCreditCard, FiArrowRight, FiShield,
} from 'react-icons/fi';
import { registrationService } from '../../services/registrationService';
import RegistrationCheckoutModal from '../../components/RegistrationCheckoutModal';
import { Skeleton } from '../../components/LoadingSkeleton';
import { extractApiError, notify } from '../../utils/notify';

function OnboardingState({ icon: Icon, title, children, variant = 'warning' }) {
  return (
    <div className="onboarding-welcome">
      <section className="onboarding-state">
        <div className="container-xl">
          <div className="onboarding-state-card text-center">
            <div className={`onboarding-state-icon onboarding-state-icon--${variant}`}>
              <Icon size={32} />
            </div>
            <h2 className="fw-bold mb-3">{title}</h2>
            {children}
          </div>
        </div>
      </section>
    </div>
  );
}

function OnboardingSkeleton() {
  return (
    <div className="onboarding-welcome">
      <section className="onboarding-hero">
        <div className="container-xl text-center">
          <Skeleton width={64} height={64} rounded={32} className="mx-auto mb-4" />
          <Skeleton width="40%" height={40} className="mx-auto mb-3" />
          <Skeleton width="55%" height={18} className="mx-auto mb-2" />
          <Skeleton width={120} height={28} rounded={20} className="mx-auto" />
        </div>
      </section>
      <section className="container-xl pb-5">
        <Skeleton width="100%" height={72} rounded={12} className="mb-4" />
        <div className="row g-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="col-lg-4">
              <Skeleton width="100%" height={280} rounded={16} />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export function RegistrationWelcome() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const tenantId = searchParams.get('school');
  const [loading, setLoading] = useState('');
  const [checkoutPlan, setCheckoutPlan] = useState(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['onboarding', tenantId],
    queryFn: () => registrationService.getOnboarding(tenantId),
    enabled: !!tenantId,
  });

  if (!tenantId) {
    return (
      <OnboardingState icon={FiAlertTriangle} title="Invalid registration link">
        <p className="text-muted mb-4">This onboarding link is missing a school identifier. Please register again.</p>
        <Link to="/register" className="btn btn-primary">Register again</Link>
      </OnboardingState>
    );
  }

  if (isLoading) return <OnboardingSkeleton />;

  if (isError || !data) {
    return (
      <OnboardingState icon={FiAlertTriangle} title="Unable to load onboarding">
        <p className="text-muted mb-4">We couldn&apos;t load your school details. Try signing in or contact support.</p>
        <Link to="/login" className="btn btn-primary">Go to sign in</Link>
      </OnboardingState>
    );
  }

  const school = data.school ?? {};
  const plans = data.plans ?? [];
  const settings = data.settings ?? {};
  const supportEmail = settings.support_email || 'support@apexhub.io';

  const trialPlans = plans.filter((p) => Number(p.price_monthly) === 0);
  const paidPlans = plans.filter((p) => Number(p.price_monthly) > 0);

  const handleClaimTrial = async () => {
    setLoading('trial');
    try {
      const result = await registrationService.claimTrialEmail(tenantId);
      notify.success(result.message);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to submit trial request.'));
    } finally {
      setLoading('');
    }
  };

  const handleSelectPlan = async (planSlug) => {
    setLoading(planSlug);
    try {
      const result = await registrationService.selectPlan(tenantId, planSlug);
      notify.success(result.message);
      setTimeout(() => navigate('/login', {
        state: { message: 'Plan selected. Sign in — your account awaits super admin approval.' },
      }), 1500);
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to select plan.'));
    } finally {
      setLoading('');
    }
  };

  const handleCheckoutSubmit = async (paymentPayload) => {
    if (!checkoutPlan) return;
    setLoading(`pay-${checkoutPlan.slug}`);
    try {
      const body = await registrationService.checkout(
        tenantId,
        checkoutPlan.slug,
        'monthly',
        paymentPayload,
      );
      notify.warning(body?.message || 'Payment could not be processed. Your registration is recorded.');
      setCheckoutPlan(null);
      setTimeout(() => navigate('/login', {
        state: {
          message: 'Payment recorded. Sign in after super admin activates your account.',
        },
      }), 2000);
    } catch (err) {
      notify.error(extractApiError(err, 'Payment could not be processed.'));
    } finally {
      setLoading('');
    }
  };

  return (
    <motion.div
      className="onboarding-welcome"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <section className="onboarding-hero">
        <div className="container-xl">
          <div className="onboarding-hero-content text-center">
            <div className="onboarding-hero-icon">
              <FiCheckCircle size={36} />
            </div>
            <h1 className="onboarding-hero-title">Welcome, {school.name}!</h1>
            <p className="onboarding-hero-subtitle">
              Your school account has been created. Choose how you&apos;d like to get started with Apex Hub.
            </p>
            {school.code && (
              <span className="onboarding-school-code">
                School code: <strong>{school.code}</strong>
              </span>
            )}
          </div>
        </div>
      </section>

      <section className="container-xl onboarding-notice-wrap">
        <div className="onboarding-notice">
          <FiShield className="onboarding-notice-icon" />
          <div>
            <strong>Approval required</strong>
            <p className="mb-0">
              All new schools require <strong>super admin approval</strong> before dashboard access is granted.
              Paid registrations also require account activation after payment verification.
            </p>
          </div>
        </div>
      </section>

      <section className="container-xl onboarding-options pb-4">
        <div className="row g-4">
          <div className="col-lg-4">
            <div className="onboarding-option-card h-100">
              <div className="onboarding-option-header">
                <span className="onboarding-option-icon onboarding-option-icon--primary">
                  <FiMail size={20} />
                </span>
                <h3 className="onboarding-option-title">Claim Free Trial via Email</h3>
              </div>
              <p className="onboarding-option-desc">
                Contact our team at{' '}
                <a href={`mailto:${supportEmail}?subject=Free Trial Request - ${school.name}`}>
                  {supportEmail}
                </a>
                {' '}to claim your free trial. We&apos;ll notify the admin to approve your account.
              </p>
              <div className="onboarding-option-actions mt-auto">
                <a
                  href={`mailto:${supportEmail}?subject=Free Trial Request - ${school.name}&body=Hello, I would like to claim the free trial for ${school.name} (code: ${school.code}).`}
                  className="btn btn-outline-primary btn-sm"
                >
                  Email Support
                </a>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  disabled={loading === 'trial'}
                  onClick={handleClaimTrial}
                >
                  {loading === 'trial' ? 'Recording...' : "I've contacted support"}
                </button>
              </div>
            </div>
          </div>

          {trialPlans.length > 0 && (
            <div className="col-lg-4">
              <div className="onboarding-option-card h-100">
                <div className="onboarding-option-header">
                  <span className="onboarding-option-icon onboarding-option-icon--primary">
                    <FiCheckCircle size={20} />
                  </span>
                  <h3 className="onboarding-option-title">Free Trial Plans</h3>
                </div>
                <p className="onboarding-option-desc">
                  Select a trial plan to proceed. You can sign in immediately, but dashboard access
                  unlocks after super admin approval.
                </p>
                <div className="onboarding-plan-list">
                  {trialPlans.map((plan) => (
                    <div key={plan.id} className="onboarding-plan-item">
                      <div className="onboarding-plan-info">
                        <div className="fw-semibold">{plan.name}</div>
                        <div className="text-muted small">
                          {plan.description || `${plan.trial_days} day trial`}
                        </div>
                      </div>
                      <div className="onboarding-plan-price">Free</div>
                      <button
                        type="button"
                        className="btn btn-sm btn-primary"
                        disabled={!!loading}
                        onClick={() => handleSelectPlan(plan.slug)}
                      >
                        {loading === plan.slug ? 'Selecting...' : 'Select'}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {paidPlans.length > 0 && (
            <div className="col-lg-4">
              <div className="onboarding-option-card h-100">
                <div className="onboarding-option-header">
                  <span className="onboarding-option-icon onboarding-option-icon--secondary">
                    <FiCreditCard size={20} />
                  </span>
                  <h3 className="onboarding-option-title">Paid Plans</h3>
                </div>
                <p className="onboarding-option-desc">
                  Subscribe with payment. Processing requires live API credentials — your registration
                  will be recorded and a super admin will activate your account.
                </p>
                <div className="onboarding-plan-list">
                  {paidPlans.map((plan) => (
                    <div key={plan.id} className="onboarding-plan-item">
                      <div className="onboarding-plan-info">
                        <div className="fw-semibold">{plan.name}</div>
                        <div className="text-muted small">{plan.description}</div>
                      </div>
                      <div className="onboarding-plan-price">
                        ${Number(plan.price_monthly).toFixed(2)}
                        <span className="onboarding-plan-period">/mo</span>
                      </div>
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-secondary"
                        disabled={!!loading}
                        onClick={() => setCheckoutPlan(plan)}
                      >
                        {loading === `pay-${plan.slug}` ? 'Processing...' : 'Pay'}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="container-xl onboarding-skip pb-5">
        <Link to="/login" className="onboarding-skip-link">
          Skip for now — Sign in <FiArrowRight className="ms-1" />
        </Link>
      </section>

      <RegistrationCheckoutModal
        open={Boolean(checkoutPlan)}
        onClose={() => setCheckoutPlan(null)}
        plan={checkoutPlan}
        loading={Boolean(checkoutPlan && loading === `pay-${checkoutPlan.slug}`)}
        onSubmit={handleCheckoutSubmit}
      />
    </motion.div>
  );
}

export default RegistrationWelcome;