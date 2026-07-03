import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { FiSave, FiDroplet, FiToggleLeft, FiShield } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import { useTenant } from '../../hooks/useTenant';
import { DEFAULT_FEATURE_FLAGS } from '../../utils/mockData';
import { notify } from '../../utils/notify';

export function SchoolAdminSettings() {
  const { tenant, featureFlags } = useTenant();

  const { register, handleSubmit } = useForm({
    defaultValues: {
      school_name: tenant?.name || 'Demo School',
      primary_color: tenant?.theme?.primary || '#0F766E',
      secondary_color: tenant?.theme?.secondary || '#FF7F50',
      accent_color: tenant?.theme?.accent || '#F5E6CA',
      academic_year: '2025-2026',
      timezone: 'UTC',
      ...Object.fromEntries(
        Object.entries(featureFlags || DEFAULT_FEATURE_FLAGS).map(([k, v]) => [`feature_${k}`, v])
      ),
    },
  });

  const onSubmit = (data) => {
    const root = document.documentElement;
    if (data.primary_color) root.style.setProperty('--apex-primary', data.primary_color);
    if (data.secondary_color) root.style.setProperty('--apex-secondary', data.secondary_color);
    if (data.accent_color) root.style.setProperty('--apex-accent', data.accent_color);
    notify.success('School settings saved.');
  };

  const featureList = Object.keys(DEFAULT_FEATURE_FLAGS);

  return (
    <div>
      <PageHeader title="School Settings" subtitle="Customize your school portal and features" />

      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="row g-4">
          <div className="col-lg-6">
            <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <h5 className="fw-bold mb-3">General</h5>
              <div className="mb-3">
                <label className="form-label small fw-medium">School Name</label>
                <input className="form-control" {...register('school_name')} />
              </div>
              <div className="mb-3">
                <label className="form-label small fw-medium">Academic Year</label>
                <input className="form-control" {...register('academic_year')} />
              </div>
              <div className="mb-3">
                <label className="form-label small fw-medium">Timezone</label>
                <select className="form-select" {...register('timezone')}>
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">Eastern Time</option>
                  <option value="Europe/London">London</option>
                  <option value="Asia/Kolkata">India Standard Time</option>
                  <option value="Africa/Nairobi">East Africa Time</option>
                </select>
              </div>
            </motion.div>
          </div>

          <div className="col-lg-6">
            <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
              <h5 className="fw-bold mb-3 d-flex align-items-center gap-2"><FiDroplet /> Theme Customization</h5>
              <div className="row g-3">
                <div className="col-4">
                  <label className="form-label small fw-medium">Primary</label>
                  <input type="color" className="form-control form-control-color w-100" {...register('primary_color')} />
                </div>
                <div className="col-4">
                  <label className="form-label small fw-medium">Secondary</label>
                  <input type="color" className="form-control form-control-color w-100" {...register('secondary_color')} />
                </div>
                <div className="col-4">
                  <label className="form-label small fw-medium">Accent</label>
                  <input type="color" className="form-control form-control-color w-100" {...register('accent_color')} />
                </div>
              </div>
              <p className="text-muted small mt-2">Customize colors to match your school branding.</p>
            </motion.div>
          </div>

          <div className="col-12">
            <motion.div className="apex-card p-4 mb-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}>
              <div className="d-flex flex-wrap align-items-center justify-content-between gap-3">
                <div>
                  <h5 className="fw-bold mb-1 d-flex align-items-center gap-2"><FiShield /> Role Permissions</h5>
                  <p className="text-muted small mb-0">
                    Configure read/write access for each staff role and parent portal users.
                  </p>
                </div>
                <Link to="/school-admin/settings/permissions" className="btn btn-outline-primary btn-sm">
                  Open Permission Settings
                </Link>
              </div>
            </motion.div>
          </div>

          <div className="col-12">
            <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
              <h5 className="fw-bold mb-3 d-flex align-items-center gap-2"><FiToggleLeft /> Feature Modules</h5>
              <div className="row g-3">
                {featureList.map((feature) => (
                  <div key={feature} className="col-sm-6 col-md-4 col-lg-3">
                    <div className="form-check form-switch">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id={`feature_${feature}`}
                        {...register(`feature_${feature}`)}
                      />
                      <label className="form-check-label text-capitalize" htmlFor={`feature_${feature}`}>
                        {feature}
                      </label>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>

        <button type="submit" className="btn btn-primary mt-4 d-flex align-items-center gap-2">
          <FiSave /> Save Settings
        </button>
      </form>
    </div>
  );
}

export default SchoolAdminSettings;