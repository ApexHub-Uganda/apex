import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import { FiMail, FiArrowLeft } from 'react-icons/fi';
import { authService } from '../../services/authService';
import { notify } from '../../utils/notify';

export function ForgotPassword() {
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit } = useForm();

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      await authService.forgotPassword(data.email);
    } catch { /* show success anyway for security */ }
    setSent(true);
    notify.info('If an account exists with that email, you will receive reset instructions shortly.');
    setLoading(false);
  };

  return (
    <motion.div className="apex-glass p-4 p-md-5" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <Link to="/login" className="d-inline-flex align-items-center gap-1 small text-muted mb-3">
        <FiArrowLeft /> Back to login
      </Link>

      <h2 className="fw-bold mb-1">Forgot password?</h2>
      <p className="text-muted mb-4 small">Enter your email and we&apos;ll send reset instructions</p>

      {sent ? (
        <p className="text-muted small mb-0">
          Check your inbox for further instructions. You can close this page or return to sign in.
        </p>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="mb-4">
            <label className="form-label small fw-medium">Email address</label>
            <div className="position-relative">
              <FiMail className="position-absolute text-muted" style={{ left: 12, top: '50%', transform: 'translateY(-50%)' }} />
              <input type="email" className="form-control ps-5" placeholder="you@school.edu" {...register('email', { required: true })} />
            </div>
          </div>
          <button type="submit" className="btn btn-primary w-100 py-2" disabled={loading}>
            {loading ? 'Sending...' : 'Send Reset Link'}
          </button>
        </form>
      )}
    </motion.div>
  );
}

export default ForgotPassword;