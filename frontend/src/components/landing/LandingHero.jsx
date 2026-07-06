import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FiPlay } from 'react-icons/fi';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Filler, Tooltip,
} from 'chart.js';
import heroImage from '../../assets/landing/hero-learner.jpg';
import { TRUST_BADGES } from '../../pages/landing/landingData';
import { useLandingMarketing } from '../../context/LandingMarketingContext';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip);

const HERO_IMAGE_FALLBACK = 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=1920&q=85';
const HERO_IMAGE_ALT = 'Students laughing and amazed while collaborating on a laptop during a learning session';

const chartData = {
  labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
  datasets: [{
    data: [82, 88, 91, 87, 94, 89, 96],
    borderColor: '#0F766E',
    backgroundColor: 'rgba(15, 118, 110, 0.1)',
    fill: true,
    tension: 0.45,
    pointRadius: 2,
    pointBackgroundColor: '#0F766E',
    borderWidth: 2,
  }],
};

const chartOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { display: false },
    y: { display: false, min: 70, max: 100 },
  },
};

export function LandingHero() {
  const { stats, platform } = useLandingMarketing();
  const studentStat = stats?.find((s) => s.label === 'Students');
  const schoolStat = stats?.find((s) => s.label === 'Schools');
  const studentDisplay = studentStat
    ? `${Number(studentStat.value).toLocaleString()}${studentStat.suffix || ''}`
    : '—';
  const schoolDisplay = schoolStat
    ? `${Number(schoolStat.value).toLocaleString()}${schoolStat.suffix || ''}`
    : '—';

  return (
    <section id="home" className="lp-hero lp-hero--light" aria-labelledby="hero-heading">
      <div className="lp-hero-bg" aria-hidden>
        <img
          src={heroImage}
          alt={HERO_IMAGE_ALT}
          className="lp-hero-image"
          loading="eager"
          fetchPriority="high"
          onError={(e) => {
            if (e.currentTarget.dataset.fallbackApplied !== 'true') {
              e.currentTarget.dataset.fallbackApplied = 'true';
              e.currentTarget.src = HERO_IMAGE_FALLBACK;
            }
          }}
        />
        <div className="lp-hero-overlay lp-hero-overlay--light" />
      </div>

      <div className="lp-container lp-hero-content">
        <motion.div
          className="lp-hero-text"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
        >
          <p className="lp-eyebrow">Cloud School ERP · Africa & Beyond</p>
          <h1 id="hero-heading" className="lp-hero-headline">
            School Management, <span>Simplified.</span>
          </h1>
          <p className="lp-hero-desc">
            {platform?.name || 'Apex Hub'} is the complete cloud platform for schools, universities,
            and training institutions — admissions, academics, finance, and communication in one
            elegant system.
          </p>
          <div className="lp-hero-actions">
            <Link to="/register" className="lp-btn lp-btn-primary">Start Free Trial</Link>
            <a href="#contact" className="lp-btn lp-btn-secondary">Book Demo</a>
            <a href="#solutions" className="lp-btn lp-btn-ghost">
              <FiPlay size={16} /> Watch Overview
            </a>
          </div>
          <div className="lp-hero-badges">
            {TRUST_BADGES.map((b) => {
              const Icon = b.icon;
              return (
                <span key={b.label} className="lp-hero-badge">
                  <Icon size={16} /> {b.label}
                </span>
              );
            })}
          </div>
        </motion.div>

        <motion.div
          className="lp-dashboard-wrap"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.4 }}
        >
          <motion.div
            className="lp-dashboard-main"
            animate={{ y: [0, -6, 0] }}
            transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
          >
            <div className="lp-dashboard-topbar">
              <div className="lp-dashboard-dots">
                <span style={{ background: '#EF4444' }} />
                <span style={{ background: '#F59E0B' }} />
                <span style={{ background: '#10B981' }} />
              </div>
              <span className="small text-muted">dashboard.apexhub.io</span>
            </div>
            <div className="lp-dashboard-body">
              <div className="lp-dashboard-sidebar">
                {['Dashboard', 'Students', 'Classes', 'Finance', 'Reports'].map((item, i) => (
                  <div key={item} className={`lp-dash-nav-item ${i === 0 ? 'active' : ''}`}>{item}</div>
                ))}
              </div>
              <div className="lp-dashboard-main-area">
                <div className="lp-dash-stats">
                  <div className="lp-dash-stat">
                    <div className="lp-dash-stat-label">Students</div>
                    <div className="lp-dash-stat-value">{studentDisplay}</div>
                  </div>
                  <div className="lp-dash-stat">
                    <div className="lp-dash-stat-label">Schools</div>
                    <div className="lp-dash-stat-value">{schoolDisplay}</div>
                  </div>
                  <div className="lp-dash-stat">
                    <div className="lp-dash-stat-label">Modules</div>
                    <div className="lp-dash-stat-value">{platform?.feature_count ?? '—'}</div>
                  </div>
                </div>
                <div className="lp-dash-chart-wrap">
                  <Line data={chartData} options={chartOpts} />
                </div>
              </div>
            </div>
          </motion.div>

          <motion.div
            className="lp-float-card lp-float-card--attendance"
            animate={{ y: [0, -6, 0] }}
            transition={{ duration: 4, repeat: Infinity, delay: 0.5 }}
          >
            <div className="lp-float-card-title">Weekly Attendance</div>
            <div className="lp-float-card-value">94.2%</div>
          </motion.div>
          <motion.div
            className="lp-float-card lp-float-card--fees"
            animate={{ y: [0, 6, 0] }}
            transition={{ duration: 4.5, repeat: Infinity, delay: 1 }}
          >
            <div className="lp-float-card-title">Fee Collection</div>
            <div className="lp-float-card-value">On track</div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

export default LandingHero;