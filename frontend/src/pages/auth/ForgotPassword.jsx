import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import { FiMail, FiArrowLeft, FiShield } from 'react-icons/fi';
import { authService } from '../../services/authService';
import { extractApiError, notify } from '../../utils/notify';
import { emailValidationRules } from '../../utils/emailValidation';

export function ForgotPassword() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm();

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      const result = await authService.requestPasswordResetOtp(data.email);
      notify.success(result?.message || 'Verification code sent.');
      navigate('/reset-password', {
        state: {
          email: data.email.trim(),
          expiresInMinutes: result?.data?.expires_in_minutes ?? 10,
        },
      });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to send verification code.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div className="apex-glass p-4 p-md-5" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <Link to="/login" className="d-inline-flex align-items-center gap-1 small text-muted mb-3">
        <FiArrowLeft /> Back to login
      </Link>

      <div className="d-flex align-items-center gap-2 mb-2">
        <div
          className="d-inline-flex align-items-center justify-content-center rounded-3"
          style={{ width: 40, height: 40, background: 'rgba(37, 99, 235, 0.1)', color: '#2563eb' }}
        >
          <FiShield size={18} />
        </div>
        <div>
          <h2 className="fw-bold mb-0">Forgot password?</h2>
        </div>
      </div>
      <p className="text-muted mb-4 small">
        Enter the email on your account. We&apos;ll send a 6-digit verification code from
        {' '}<strong>client.apexhub@gmail.com</strong> to reset your password securely.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="mb-4">
          <label className="form-label small fw-medium" htmlFor="reset-email">Email address</label>
          <div className="position-relative">
            <FiMail
              className="position-absolute text-muted"
              style={{ left: 12, top: '50%', transform: 'translateY(-50%)' }}
            />
            <input
              id="reset-email"
              type="email"
              autoComplete="email"
              className={`form-control ps-5${errors.email ? ' is-invalid' : ''}`}
              placeholder="you@school.edu"
              disabled={loading}
              {...register('email', emailValidationRules({ label: 'Email address' }))}
            />
            {errors.email && <div className="invalid-feedback">{errors.email.message}</div>}
          </div>
        </div>
        <button type="submit" className="btn btn-primary w-100 py-2" disabled={loading}>
          {loading ? 'Sending code…' : 'Send verification code'}
        </button>
      </form>
    </motion.div>
  );
}

export default ForgotPassword;