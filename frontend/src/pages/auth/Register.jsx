import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import { FiUser, FiMail, FiLock, FiBriefcase } from 'react-icons/fi';
import { registrationService } from '../../services/registrationService';
import { extractApiError, notify } from '../../utils/notify';
import { emailValidationRules } from '../../utils/emailValidation';

export function Register() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const { register, handleSubmit, watch, formState: { errors } } = useForm();
  const password = watch('password');

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      const result = await registrationService.register({
        name: data.school_name,
        email: data.email,
        country: data.country || 'Uganda',
        admin_email: data.email,
        admin_password: data.password,
        admin_first_name: data.first_name,
        admin_last_name: data.last_name,
      });
      const tenantId = result.tenant_id || result.tenant?.id;
      notify.success('School account created! Complete onboarding to get started.');
      navigate(`/register/welcome?school=${tenantId}`);
    } catch (err) {
      notify.error(extractApiError(err, 'Registration failed. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div className="apex-glass p-4 p-md-5" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <h2 className="fw-bold mb-1">Create account</h2>
      <p className="text-muted mb-4 small">Register your school on Apex Hub</p>

      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="row g-3">
          <div className="col-6">
            <label className="form-label small fw-medium">First Name</label>
            <div className="position-relative">
              <FiUser className="position-absolute text-muted" style={{ left: 12, top: '50%', transform: 'translateY(-50%)' }} />
              <input className="form-control ps-5" {...register('first_name', { required: true })} />
            </div>
          </div>
          <div className="col-6">
            <label className="form-label small fw-medium">Last Name</label>
            <input className="form-control" {...register('last_name', { required: true })} />
          </div>
        </div>

        <div className="mb-3 mt-3">
          <label className="form-label small fw-medium">School Name</label>
          <div className="position-relative">
            <FiBriefcase className="position-absolute text-muted" style={{ left: 12, top: '50%', transform: 'translateY(-50%)' }} />
            <input
              className="form-control ps-5"
              {...register('school_name', {
                required: 'School name is required',
                minLength: { value: 3, message: 'Enter your school\'s full official name' },
              })}
            />
          </div>
        </div>

        <div className="mb-3">
          <label className="form-label small fw-medium">Country</label>
          <input className="form-control" defaultValue="Uganda" {...register('country')} />
        </div>

        <div className="mb-3">
          <label className="form-label small fw-medium">Email</label>
          <div className="position-relative">
            <FiMail className="position-absolute text-muted" style={{ left: 12, top: '50%', transform: 'translateY(-50%)' }} />
            <input type="email" className="form-control ps-5" {...register('email', emailValidationRules({ label: 'Email' }))} />
          </div>
        </div>

        <div className="mb-3">
          <label className="form-label small fw-medium">Password</label>
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
          {loading ? 'Creating account...' : 'Create Account'}
        </button>
      </form>

      <div className="text-center mt-4">
        <span className="text-muted small">Already have an account? </span>
        <Link to="/login" className="small fw-semibold">Sign in</Link>
      </div>
    </motion.div>
  );
}

export default Register;