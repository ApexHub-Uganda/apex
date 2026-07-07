import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import { FiLock, FiArrowLeft, FiRefreshCw } from 'react-icons/fi';
import { authService } from '../../services/authService';
import { extractApiError, notify } from '../../utils/notify';

const OTP_LENGTH = 6;

function OtpInput({ value, onChange, disabled = false }) {
  const inputsRef = useRef([]);
  const digits = useMemo(() => {
    const chars = (value || '').split('');
    return Array.from({ length: OTP_LENGTH }, (_, index) => chars[index] || '');
  }, [value]);

  const focusIndex = (index) => {
    inputsRef.current[index]?.focus();
    inputsRef.current[index]?.select();
  };

  const updateDigit = (index, raw) => {
    const digit = raw.replace(/\D/g, '').slice(-1);
    const next = digits.map((item, idx) => (idx === index ? digit : item));
    onChange(next.join('').slice(0, OTP_LENGTH));
    if (digit && index < OTP_LENGTH - 1) {
      focusIndex(index + 1);
    }
  };

  const handleKeyDown = (index, event) => {
    if (event.key === 'Backspace' && !digits[index] && index > 0) {
      focusIndex(index - 1);
    }
    if (event.key === 'ArrowLeft' && index > 0) {
      event.preventDefault();
      focusIndex(index - 1);
    }
    if (event.key === 'ArrowRight' && index < OTP_LENGTH - 1) {
      event.preventDefault();
      focusIndex(index + 1);
    }
  };

  const handlePaste = (event) => {
    event.preventDefault();
    const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, OTP_LENGTH);
    if (!pasted) return;
    onChange(pasted);
    focusIndex(Math.min(pasted.length, OTP_LENGTH) - 1);
  };

  return (
    <div className="d-flex justify-content-between gap-2" onPaste={handlePaste}>
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(node) => { inputsRef.current[index] = node; }}
          type="text"
          inputMode="numeric"
          autoComplete={index === 0 ? 'one-time-code' : 'off'}
          maxLength={1}
          className="form-control text-center fw-bold"
          style={{ fontSize: '1.35rem', letterSpacing: '0.08em', padding: '0.65rem 0' }}
          value={digit}
          disabled={disabled}
          aria-label={`Digit ${index + 1}`}
          onChange={(event) => updateDigit(index, event.target.value)}
          onKeyDown={(event) => handleKeyDown(index, event)}
          onFocus={(event) => event.target.select()}
        />
      ))}
    </div>
  );
}

export function ResetPassword() {
  const navigate = useNavigate();
  const location = useLocation();
  const email = location.state?.email || '';
  const expiresInMinutes = location.state?.expiresInMinutes ?? 10;

  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  const { register, handleSubmit, watch, formState: { errors } } = useForm();
  const password = watch('password');

  useEffect(() => {
    if (!email) {
      notify.warning('Start from the forgot password page to receive a verification code.');
      navigate('/forgot-password', { replace: true });
    }
  }, [email, navigate]);

  useEffect(() => {
    if (!cooldown) return undefined;
    const timer = window.setInterval(() => {
      setCooldown((value) => (value > 1 ? value - 1 : 0));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [cooldown]);

  const handleResend = async () => {
    if (!email || resending || cooldown > 0) return;
    setResending(true);
    try {
      const result = await authService.requestPasswordResetOtp(email);
      setOtp('');
      setCooldown(result?.data?.resend_cooldown_seconds ?? 60);
      notify.success(result?.message || 'A new verification code has been sent.');
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to resend verification code.'));
    } finally {
      setResending(false);
    }
  };

  const onSubmit = async (data) => {
    if (otp.length !== OTP_LENGTH) {
      notify.warning('Enter the complete 6-digit verification code.');
      return;
    }
    setLoading(true);
    try {
      const result = await authService.confirmPasswordReset({
        email,
        otp,
        newPassword: data.password,
      });
      navigate('/login', {
        state: { message: result?.message || 'Password reset successful. You can sign in now.' },
      });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to reset password.'));
    } finally {
      setLoading(false);
    }
  };

  if (!email) return null;

  return (
    <motion.div className="apex-glass p-4 p-md-5" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <Link to="/forgot-password" className="d-inline-flex align-items-center gap-1 small text-muted mb-3">
        <FiArrowLeft /> Change email
      </Link>

      <h2 className="fw-bold mb-1">Enter verification code</h2>
      <p className="text-muted mb-1 small">
        We sent a 6-digit code to <strong>{email}</strong>
      </p>
      <p className="text-muted mb-4 small">The code expires in {expiresInMinutes} minutes.</p>

      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="mb-4">
          <label className="form-label small fw-medium">Verification code</label>
          <OtpInput value={otp} onChange={setOtp} disabled={loading || resending} />
          <div className="d-flex justify-content-between align-items-center mt-2">
            <span className="small text-muted">Check your inbox and spam folder.</span>
            <button
              type="button"
              className="btn btn-link btn-sm p-0 text-decoration-none"
              onClick={handleResend}
              disabled={resending || loading || cooldown > 0}
            >
              <FiRefreshCw size={13} className="me-1" />
              {resending
                ? 'Sending…'
                : cooldown > 0
                  ? `Resend in ${cooldown}s`
                  : 'Resend code'}
            </button>
          </div>
        </div>

        <div className="mb-3">
          <label className="form-label small fw-medium">New password</label>
          <div className="position-relative">
            <FiLock
              className="position-absolute text-muted"
              style={{ left: 12, top: '50%', transform: 'translateY(-50%)' }}
            />
            <input
              type="password"
              autoComplete="new-password"
              className={`form-control ps-5${errors.password ? ' is-invalid' : ''}`}
              disabled={loading}
              {...register('password', {
                required: 'Password is required.',
                minLength: { value: 8, message: 'Use at least 8 characters.' },
              })}
            />
            {errors.password && <div className="invalid-feedback">{errors.password.message}</div>}
          </div>
        </div>

        <div className="mb-4">
          <label className="form-label small fw-medium">Confirm password</label>
          <input
            type="password"
            autoComplete="new-password"
            className={`form-control${errors.confirm_password ? ' is-invalid' : ''}`}
            disabled={loading}
            {...register('confirm_password', {
              required: 'Please confirm your password.',
              validate: (value) => value === password || 'Passwords do not match.',
            })}
          />
          {errors.confirm_password && (
            <div className="invalid-feedback">{errors.confirm_password.message}</div>
          )}
        </div>

        <button type="submit" className="btn btn-primary w-100 py-2" disabled={loading}>
          {loading ? 'Updating password…' : 'Reset password'}
        </button>
      </form>

      <div className="text-center mt-4">
        <Link to="/login" className="small">Back to login</Link>
      </div>
    </motion.div>
  );
}

export default ResetPassword;