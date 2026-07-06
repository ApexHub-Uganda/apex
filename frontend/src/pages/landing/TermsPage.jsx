import { Link } from 'react-router-dom';
import Logo from '../../components/Logo';
import './landing.css';

const TERMS_SECTIONS = [
  {
    title: '1. Acceptance of Terms',
    body: 'By accessing or using Apex Hub, you agree to be bound by these Terms and Conditions. If you do not agree, you may not use the platform. These terms apply to schools, administrators, staff, students, parents, and any authorized users.',
  },
  {
    title: '2. Description of Service',
    body: 'Apex Hub is a cloud-based school management platform that provides modules for admissions, academics, finance, attendance, communication, and related institutional operations. Features available to your organization depend on your subscription plan.',
  },
  {
    title: '3. Accounts and Responsibilities',
    body: 'You are responsible for maintaining the confidentiality of account credentials and for all activity under your account. School administrators must ensure that user access is granted appropriately and that institutional data is handled in compliance with applicable laws.',
  },
  {
    title: '4. Acceptable Use',
    body: 'You agree not to misuse the platform, attempt unauthorized access, interfere with service operations, upload malicious content, or use Apex Hub in violation of applicable laws or institutional policies. We reserve the right to suspend access for violations.',
  },
  {
    title: '5. Subscription and Billing',
    body: 'Paid plans, trials, renewals, and billing terms are governed by the plan selected at registration or upgrade. Fees, limits, and feature availability are described in your subscription agreement and may change with notice as permitted by your contract.',
  },
  {
    title: '6. Data and Privacy',
    body: 'We process institutional and user data to provide the service. Data ownership remains with your institution. Our handling of personal information is described in our Privacy Policy, which forms part of these terms.',
  },
  {
    title: '7. Intellectual Property',
    body: 'Apex Hub, including its software, branding, documentation, and related materials, is owned by us or our licensors. You receive a limited, non-exclusive license to use the platform according to your subscription while your account remains active and in good standing.',
  },
  {
    title: '8. Availability and Support',
    body: 'We strive to maintain reliable service but do not guarantee uninterrupted availability. Maintenance, updates, and support response times may vary by plan. Critical issues should be reported through your designated support channels.',
  },
  {
    title: '9. Limitation of Liability',
    body: 'To the fullest extent permitted by law, Apex Hub shall not be liable for indirect, incidental, special, or consequential damages arising from use of the platform. Our total liability is limited to the fees paid for the service during the preceding billing period, where applicable.',
  },
  {
    title: '10. Changes to These Terms',
    body: 'We may update these Terms and Conditions from time to time. Material changes will be communicated through the platform or by email where appropriate. Continued use after changes become effective constitutes acceptance of the revised terms.',
  },
  {
    title: '11. Contact',
    body: 'For questions about these Terms and Conditions, contact your Apex Hub account representative or email sales@apexhub.io.',
  },
];

export function TermsPage() {
  return (
    <div className="apex-landing lp-legal-page" data-landing-theme="light">
      <header className="lp-legal-header">
        <div className="lp-container lp-legal-header-inner">
          <Link to="/" className="lp-logo-link" aria-label="Back to Apex Hub home">
            <Logo size={40} />
          </Link>
          <Link to="/" className="lp-btn lp-btn-secondary btn-sm">Back to Home</Link>
        </div>
      </header>

      <main className="lp-legal-main">
        <div className="lp-container">
          <div className="lp-legal-card">
            <p className="lp-eyebrow">Legal</p>
            <h1 className="lp-title text-start">Terms and Conditions</h1>
            <p className="lp-subtitle text-start mb-4">
              Last updated: July 3, 2026. Customize this document to match your organization&apos;s legal requirements.
            </p>

            <div className="lp-legal-body">
              {TERMS_SECTIONS.map((section) => (
                <section key={section.title} className="lp-legal-section">
                  <h2>{section.title}</h2>
                  <p>{section.body}</p>
                </section>
              ))}
            </div>
          </div>
        </div>
      </main>

      <footer className="lp-legal-footer">
        <div className="lp-container lp-footer-bottom">
          <span>&copy; 2026 Apex Hub. All rights reserved.</span>
          <nav className="lp-footer-bottom-links" aria-label="Footer legal and social">
            <a href="/#privacy">Privacy</a>
            <Link to="/terms">Terms</Link>
            <a href="https://twitter.com" target="_blank" rel="noopener noreferrer">Twitter</a>
            <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer">LinkedIn</a>
          </nav>
        </div>
      </footer>
    </div>
  );
}

export default TermsPage;