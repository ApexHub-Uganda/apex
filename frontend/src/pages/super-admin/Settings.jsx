import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { FiSave, FiGlobe, FiMail, FiShield, FiAlertTriangle } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import { PageSkeleton } from '../../components/LoadingSkeleton';
import { settingsService } from '../../services/moduleService';
import { extractApiError, notify } from '../../utils/notify';

export function SuperAdminSettings() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['platform-settings'],
    queryFn: () => settingsService.get(),
  });

  const { register, handleSubmit, reset, formState: { isDirty } } = useForm();

  useEffect(() => {
    if (data) {
      reset({
        platform_name: data.platform_name ?? '',
        platform_tagline: data.platform_tagline ?? '',
        support_email: data.support_email ?? '',
        default_plan: data.default_plan ?? 'premium',
        max_upload_size: data.max_upload_size ?? 10,
        maintenance_mode: data.maintenance_mode ?? false,
        default_timezone: data.default_timezone ?? 'Africa/Kampala',
        default_country: data.default_country ?? 'Uganda',
      });
    }
  }, [data, reset]);

  const saveMutation = useMutation({
    mutationFn: (payload) => settingsService.update(payload),
    onSuccess: (saved) => {
      reset(saved);
      notify.success('Platform settings saved successfully.');
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to save settings.')),
  });

  const onSubmit = (formData) => {
    saveMutation.mutate({
      ...formData,
      max_upload_size: Number(formData.max_upload_size),
      maintenance_mode: !!formData.maintenance_mode,
    });
  };

  if (isLoading) return <PageSkeleton />;

  if (isError) {
    return (
      <div className="apex-card p-5 text-center">
        <FiAlertTriangle size={32} className="text-warning mb-3" />
        <h5 className="fw-bold">Unable to load settings</h5>
        <button className="btn btn-primary btn-sm mt-2" onClick={() => refetch()}>Retry</button>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Platform Settings" subtitle="Configure global Apex Hub settings" />

      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="row g-4">
          <div className="col-lg-6">
            <motion.div className="apex-card p-4" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <h5 className="fw-bold mb-3 d-flex align-items-center gap-2"><FiGlobe /> General</h5>
              <div className="mb-3">
                <label className="form-label small fw-medium">Platform Name</label>
                <input className="form-control" {...register('platform_name')} />
              </div>
              <div className="mb-3">
                <label className="form-label small fw-medium">Tagline</label>
                <input className="form-control" {...register('platform_tagline')} />
              </div>
              <div className="mb-3">
                <label className="form-label small fw-medium">Default Plan</label>
                <select className="form-select" {...register('default_plan')}>
                  <option value="free_trial">Free Trial</option>
                  <option value="basic">Basic</option>
                  <option value="premium">Premium</option>
                  <option value="premium_plus">Premium Plus</option>
                </select>
              </div>
              <div className="mb-3">
                <label className="form-label small fw-medium">Default Timezone</label>
                <input className="form-control" {...register('default_timezone')} />
              </div>
              <div className="mb-3">
                <label className="form-label small fw-medium">Default Country</label>
                <input className="form-control" {...register('default_country')} />
              </div>
            </motion.div>
          </div>

          <div className="col-lg-6">
            <motion.div className="apex-card p-4" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <h5 className="fw-bold mb-3 d-flex align-items-center gap-2"><FiMail /> Email & Support</h5>
              <div className="mb-3">
                <label className="form-label small fw-medium">Support Email</label>
                <input type="email" className="form-control" {...register('support_email')} />
              </div>
              <div className="mb-3">
                <label className="form-label small fw-medium">Max Upload Size (MB)</label>
                <input type="number" className="form-control" {...register('max_upload_size')} />
              </div>
            </motion.div>
          </div>

          <div className="col-lg-6">
            <motion.div className="apex-card p-4" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <h5 className="fw-bold mb-3 d-flex align-items-center gap-2"><FiShield /> Security</h5>
              <div className="form-check form-switch">
                <input className="form-check-input" type="checkbox" {...register('maintenance_mode')} id="maintenance" />
                <label className="form-check-label" htmlFor="maintenance">Maintenance Mode</label>
              </div>
              <p className="text-muted small mt-2">When enabled, only super admins can access the platform.</p>
            </motion.div>
          </div>
        </div>

        <div className="d-flex align-items-center gap-3 mt-4">
          <button type="submit" className="btn btn-primary d-flex align-items-center gap-2" disabled={saveMutation.isPending || !isDirty}>
            <FiSave /> {saveMutation.isPending ? 'Saving...' : 'Save Settings'}
          </button>
          {saveMutation.isSuccess && <span className="text-success small">Settings saved successfully.</span>}
          {saveMutation.isError && <span className="text-danger small">Failed to save settings.</span>}
        </div>
      </form>
    </div>
  );
}

export default SuperAdminSettings;