import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import { FiUser, FiMail, FiPhone, FiSave } from 'react-icons/fi';
import { useAuth } from '../../hooks/useAuth';
import PageHeader from '../../components/PageHeader';
import { authService } from '../../services/authService';
import { extractApiError, notify } from '../../utils/notify';

export function Profile({ basePath = '' }) {
  const { user, updateUser } = useAuth();
  const { register, handleSubmit, formState: { isSubmitting } } = useForm({
    defaultValues: {
      first_name: user?.first_name || '',
      last_name: user?.last_name || '',
      email: user?.email || '',
      phone: user?.phone || '',
    },
  });

  const onSubmit = async (data) => {
    try {
      const updated = await authService.updateProfile(data);
      updateUser(updated);
      notify.success('Profile updated successfully.');
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to update profile.'));
    }
  };

  return (
    <div>
      <PageHeader title="Profile" subtitle="Manage your account information" />

      <div className="row g-4">
        <div className="col-lg-4">
          <motion.div className="apex-card p-4 text-center" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
            <div
              className="mx-auto mb-3 d-flex align-items-center justify-content-center text-white fw-bold"
              style={{
                width: 100, height: 100, borderRadius: 20,
                background: 'linear-gradient(135deg, var(--apex-primary), var(--apex-secondary))',
                fontSize: '2rem',
              }}
            >
              {user?.first_name?.[0]}{user?.last_name?.[0]}
            </div>
            <h5 className="fw-bold mb-1">{user?.first_name} {user?.last_name}</h5>
            <p className="text-muted small mb-2">{user?.email}</p>
            <span className="apex-badge apex-badge-info text-capitalize">{user?.role?.replace('_', ' ')}</span>
          </motion.div>
        </div>

        <div className="col-lg-8">
          <motion.div className="apex-card p-4" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}>
            <h5 className="fw-bold mb-4">Personal Information</h5>
            <form onSubmit={handleSubmit(onSubmit)}>
              <div className="row g-3">
                <div className="col-md-6">
                  <label className="form-label small fw-medium">First Name</label>
                  <div className="position-relative">
                    <FiUser className="position-absolute text-muted" style={{ left: 12, top: '50%', transform: 'translateY(-50%)' }} />
                    <input className="form-control ps-5" {...register('first_name')} />
                  </div>
                </div>
                <div className="col-md-6">
                  <label className="form-label small fw-medium">Last Name</label>
                  <input className="form-control" {...register('last_name')} />
                </div>
                <div className="col-md-6">
                  <label className="form-label small fw-medium">Email</label>
                  <div className="position-relative">
                    <FiMail className="position-absolute text-muted" style={{ left: 12, top: '50%', transform: 'translateY(-50%)' }} />
                    <input type="email" className="form-control ps-5" {...register('email')} />
                  </div>
                </div>
                <div className="col-md-6">
                  <label className="form-label small fw-medium">Phone</label>
                  <div className="position-relative">
                    <FiPhone className="position-absolute text-muted" style={{ left: 12, top: '50%', transform: 'translateY(-50%)' }} />
                    <input className="form-control ps-5" {...register('phone')} />
                  </div>
                </div>
              </div>
              <button type="submit" className="btn btn-primary mt-4 d-flex align-items-center gap-2" disabled={isSubmitting}>
                <FiSave /> Save Changes
              </button>
            </form>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

export default Profile;