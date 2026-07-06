import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Line, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Filler, ArcElement, Tooltip, Legend,
} from 'chart.js';
import { DASHBOARD_TABS } from '../../pages/landing/landingData';

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement, Filler,
  ArcElement, Tooltip, Legend,
);

const TAB_CONTENT = {
  admin: { title: 'School Admin Dashboard', stats: [['Students', '—'], ['Staff', '—'], ['Modules', '—']] },
  teacher: { title: 'Teacher Portal', stats: [['Classes', '—'], ['Attendance', 'Today'], ['Assignments', '—']] },
  parent: { title: 'Parent Portal', stats: [['Children', '—'], ['Fees', '—'], ['Messages', '—']] },
  student: { title: 'Student Portal', stats: [['Schedule', 'Active'], ['Attendance', '—'], ['Homework', '—']] },
  finance: { title: 'Finance Module', stats: [['Collected', '—'], ['Outstanding', '—'], ['Invoices', '—']] },
  analytics: { title: 'Analytics Suite', stats: [['Reports', '—'], ['Trends', 'Live'], ['Exports', '—']] },
};

const linePrimary = {
  labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
  datasets: [{
    label: 'Enrollment',
    data: [72, 78, 81, 85, 88, 92],
    borderColor: '#0F766E',
    backgroundColor: 'rgba(15, 118, 110, 0.08)',
    fill: true,
    tension: 0.42,
    pointRadius: 3,
    pointBackgroundColor: '#0F766E',
    borderWidth: 2,
  }],
};

const lineSecondary = {
  labels: ['W1', 'W2', 'W3', 'W4', 'W5', 'W6'],
  datasets: [{
    label: 'Attendance %',
    data: [91, 93, 90, 94, 95, 96],
    borderColor: '#14B8A6',
    backgroundColor: 'rgba(20, 184, 166, 0.06)',
    fill: true,
    tension: 0.42,
    pointRadius: 3,
    pointBackgroundColor: '#14B8A6',
    borderWidth: 2,
  }],
};

const buildLineOpts = (isDark) => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#0F172A',
      padding: 10,
      cornerRadius: 8,
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { color: isDark ? '#94A3B8' : '#64748B', font: { size: 11 } },
    },
    y: {
      grid: { color: isDark ? 'rgba(148, 163, 184, 0.12)' : 'rgba(148, 163, 184, 0.2)' },
      ticks: { color: isDark ? '#94A3B8' : '#64748B', font: { size: 11 } },
    },
  },
});

const doughnutData = {
  labels: ['Paid', 'Pending', 'Overdue'],
  datasets: [{
    data: [72, 18, 10],
    backgroundColor: ['#0F766E', '#F5E6CA', '#FF7F50'],
    borderWidth: 0,
  }],
};

const buildDoughnutOpts = (isDark) => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom',
      labels: {
        boxWidth: 10,
        padding: 14,
        font: { size: 11 },
        color: isDark ? '#CBD5E1' : '#475569',
      },
    },
  },
});

export function LandingShowcase({ theme = 'light' }) {
  const [active, setActive] = useState('admin');
  const content = TAB_CONTENT[active];
  const isDark = theme === 'dark';
  const lineOpts = buildLineOpts(isDark);
  const doughnutOpts = buildDoughnutOpts(isDark);

  return (
    <section id="solutions" className="lp-section lp-showcase" aria-labelledby="showcase-heading">
      <div className="lp-container">
        <div className="lp-section-header" data-aos="fade-up">
          <span className="lp-eyebrow">Interactive Preview</span>
          <h2 id="showcase-heading" className="lp-title">Experience Apex Hub in Action</h2>
          <p className="lp-subtitle">
            Switch between portals and modules to see how every role interacts with the platform.
          </p>
        </div>

        <div className="lp-showcase-tabs" role="tablist" aria-label="Dashboard previews">
          {DASHBOARD_TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={active === tab.id}
              className={`lp-showcase-tab ${active === tab.id ? 'active' : ''}`}
              onClick={() => setActive(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={active}
            className="lp-showcase-preview"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ duration: 0.35 }}
            role="tabpanel"
          >
            <div className="p-4">
              <h3 className="h5 fw-bold mb-4">{content.title}</h3>
              <div className="row g-3 mb-4">
                {content.stats.map(([label, value]) => (
                  <div key={label} className="col-md-4">
                    <div className="lp-dash-stat">
                      <div className="lp-dash-stat-label">{label}</div>
                      <div className="lp-dash-stat-value">{value}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="row g-3">
                <div className="col-md-7">
                  <p className="small text-muted mb-2 fw-medium">Enrollment trend</p>
                  <div className="lp-dash-chart-wrap" style={{ height: 200 }}>
                    <Line data={linePrimary} options={lineOpts} />
                  </div>
                </div>
                <div className="col-md-5">
                  <p className="small text-muted mb-2 fw-medium">Attendance trend</p>
                  <div className="lp-dash-chart-wrap" style={{ height: 120 }}>
                    <Line data={lineSecondary} options={lineOpts} />
                  </div>
                  <p className="small text-muted mb-2 fw-medium mt-3">Fee status</p>
                  <div className="lp-dash-chart-wrap" style={{ height: 120 }}>
                    <Doughnut data={doughnutData} options={doughnutOpts} />
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}

export default LandingShowcase;