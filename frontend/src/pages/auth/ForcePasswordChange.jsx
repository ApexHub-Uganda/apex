import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { FiLock } from 'react-icons/fi';
import { useAuth } from '../../hooks/useAuth';
import { authService } from '../../services/authService';
import { notify } from '../../utils/notify';

export function ForcePasswordChange() {
  const { user, updateUser } = useAuth();
  const [saving, setSaving] = useState(false);
  const { register, handleSubmit, watch, formState: { errors } } = useForm();

  const newPassword = watch('new_password');

  const onSubmit = async (data) => {
    setSaving(true);
    try {
      await authService.changePassword({
        new_password: data.new_password,
        confirm_password: data.confirm_password,
      });
      updateUser({ must_change_password: false });
      notify.success('Password updated. You can now use the dashboard.');
    } catch (err) {
      notify.error(err?.response?.data?.message || 'Unable to update password.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="container py-5" style={{ maxWidth: 520 }}>
      <div className="apex-card p-4 p-md-5">
        <div className="d-flex align-items-center gap-2 mb-3">
          <FiLock className="text-primary" size={22} />
          <h4 className="mb-0">Set your password</h4>
        </div>
        <p className="text-muted small mb-4">
          Welcome{user?.first_name ? `, ${user.first_name}` : ''}. A one-time password was emailed to you.
          Choose a new password before continuing to the dashboard.
        </p>
        <form onSubmit={handleSubmit(onSubmit)} className="row g-3">
          <div className="col-12">
            <label className="form-label small fw-medium">New password</label>
            <input
              type="password"
              className="form-control"
              autoComplete="new-password"
              {...register('new_password', { required: 'Password is required', minLength: { value: 8, message: 'Minimum 8 characters' } })}
            />
            {errors.new_password && <div className="text-danger small mt-1">{errors.new_password.message}</div>}
          </div>
          <div className="col-12">
            <label className="form-label small fw-medium">Confirm password</label>
            <input
              type="password"
              className="form-control"
              autoComplete="new-password"
              {...register('confirm_password', {
                required: 'Please confirm your password',
                validate: (value) => value === newPassword || 'Passwords do not match',
              })}
            />
            {errors.confirm_password && <div className="text-danger small mt-1">{errors.confirm_password.message}</div>}
          </div>
          <div className="col-12">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving…' : 'Save password and continue'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ForcePasswordChange;