import { useEffect, useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import { FiMail, FiLock, FiEye, FiEyeOff, FiSun, FiMoon } from 'react-icons/fi';
import { useAuth } from '../../hooks/useAuth';
import { isSchoolPortalRole } from '../../config/schoolRoles';
import { useTheme } from '../../hooks/useTheme';
import { getLoginErrorMessage } from '../../utils/authErrors';
import { notify } from '../../utils/notify';
import { emailFormatRules } from '../../utils/emailValidation';
import { InlineLoader } from '../../components/ApexLoader';

export function Login() {
  const { login } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm({
    defaultValues: { remember: true },
  });

  useEffect(() => {
    if (location.state?.message) {
      notify.info(location.state.message);
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location.state?.message, location.pathname, navigate]);

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      const result = await login(data);
      if (result.user?.must_change_password) {
        notify.info('Please set a new password to continue.');
        navigate('/school-admin', { replace: true });
        return;
      }
      notify.success(`Welcome back, ${result.user.first_name || 'there'}!`);
      const from = location.state?.from?.pathname;
      if (result.user.role === 'super_admin') {
        navigate(from || '/super-admin', { replace: true });
      } else if (isSchoolPortalRole(result.user.role) || result.user.is_school_portal_user) {
        navigate('/school-admin', { replace: true });
      } else {
        navigate(from || '/school-admin', { replace: true });
      }
    } catch (err) {
      notify.error(getLoginErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      className="apex-glass p-4 p-md-5"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: 0.1 }}
    >
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-bold mb-1">Welcome back</h2>
          <p className="text-muted mb-0 small">Sign in to your Apex Hub account</p>
        </div>
        <button className="btn btn-sm btn-outline-secondary border-0" onClick={toggleTheme}>
          {theme === 'light' ? <FiMoon /> : <FiSun />}
        </button>
      </div>

      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="mb-3">
          <label className="form-label fw-medium small">Email address</label>
          <div className="position-relative">
            <FiMail className="position-absolute text-muted" style={{ left: 14, top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="email"
              className="form-control ps-5"
              placeholder="you@school.edu"
              {...register('email', emailFormatRules({ label: 'Email address' }))}
            />
          </div>
          {errors.email && <div className="text-danger small mt-1">{errors.email.message}</div>}
        </div>

        <div className="mb-3">
          <label className="form-label fw-medium small">Password</label>
          <div className="position-relative">
            <FiLock className="position-absolute text-muted" style={{ left: 14, top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type={showPassword ? 'text' : 'password'}
              className="form-control ps-5 pe-5"
              placeholder="Enter your password"
              {...register('password', { required: 'Password is required' })}
            />
            <button
              type="button"
              className="btn btn-link position-absolute text-muted p-0"
              style={{ right: 14, top: '50%', transform: 'translateY(-50%)' }}
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? <FiEyeOff size={16} /> : <FiEye size={16} />}
            </button>
          </div>
          {errors.password && <div className="text-danger small mt-1">{errors.password.message}</div>}
        </div>

        <div className="d-flex justify-content-between align-items-center mb-4">
          <div className="form-check">
            <input type="checkbox" className="form-check-input" id="remember" {...register('remember')} />
            <label className="form-check-label small" htmlFor="remember">Remember me</label>
          </div>
          <Link to="/forgot-password" className="small fw-semibold">Forgot password?</Link>
        </div>

        <button type="submit" className="btn btn-primary w-100 py-2 d-flex align-items-center justify-content-center gap-2" disabled={loading}>
          {loading ? (
            <>
              <InlineLoader />
              <span>Signing in</span>
            </>
          ) : (
            'Sign In'
          )}
        </button>
      </form>

      <div className="text-center mt-4">
        <span className="text-muted small">Don&apos;t have an account? </span>
        <Link to="/register" className="small fw-semibold">Register your school</Link>
      </div>
      <div className="text-center mt-2">
        <Link to="/" className="small text-muted">← Back to Apex Hub</Link>
      </div>
    </motion.div>
  );
}

export default Login;