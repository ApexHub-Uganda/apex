import { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import { FiLock } from 'react-icons/fi';
import { authService } from '../../services/authService';
import { extractApiError, notify } from '../../utils/notify';

export function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';
  const [loading, setLoading] = useState(false);

  const { register, handleSubmit, watch, formState: { errors } } = useForm();
  const password = watch('password');

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      await authService.resetPassword(token, data.password);
      navigate('/login', { state: { message: 'Password reset successful! You can now sign in.' } });
    } catch (err) {
      notify.error(extractApiError(err, 'Invalid or expired reset link.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div className="apex-glass p-4 p-md-5" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <h2 className="fw-bold mb-1">Reset password</h2>
      <p className="text-muted mb-4 small">Enter your new password below</p>

      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="mb-3">
          <label className="form-label small fw-medium">New Password</label>
          <div className="position-relative">
            <FiLock className="position-absolute text-muted" style={{ left: 12, top: '50%', transform: 'translateY(-50%)' }} />
            <input type="password" className="form-control ps-5" {...register('password', { required: true, minLength: 8 })} />
          </div>
        </div>
        <div className="mb-4">
          <label className="form-label small fw-medium">Confirm Password</label>
          <input
            type="password"
            className="form-control"
            {...register('confirm_password', { required: true, validate: (v) => v === password || 'Passwords do not match' })}
          />
          {errors.confirm_password && <div className="text-danger small">{errors.confirm_password.message}</div>}
        </div>
        <button type="submit" className="btn btn-primary w-100 py-2" disabled={loading}>
          {loading ? 'Resetting...' : 'Reset Password'}
        </button>
      </form>

      <div className="text-center mt-4">
        <Link to="/login" className="small">Back to login</Link>
      </div>
    </motion.div>
  );
}

export default ResetPassword;