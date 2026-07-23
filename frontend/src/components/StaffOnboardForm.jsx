import { useEffect, useMemo, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useQuery } from '@tanstack/react-query';
import { FiBriefcase, FiLock, FiMail, FiUser, FiUsers } from 'react-icons/fi';
import { staffService, departmentsService } from '../services/moduleService';
import { FALLBACK_STAFF_ROLES, STAFF_CATEGORIES, EMPLOYMENT_TYPES, GENDER_OPTIONS } from '../config/staffRoleConfig';
import { usePermissions } from '../hooks/usePermissions';
import { useAuth } from '../hooks/useAuth';
import { emailValidationRules } from '../utils/emailValidation';

const Section = ({ title, icon: Icon, children }) => (
  <div className="staff-form-section">
    <div className="staff-form-section-header">
      {Icon && <Icon size={18} className="text-primary" />}
      <h6 className="fw-bold mb-0">{title}</h6>
    </div>
    <div className="row g-3">{children}</div>
  </div>
);

const Field = ({ label, required, error, children, hint }) => (
  <div className="col-md-6">
    <label className="form-label small fw-medium">
      {label}
      {required && <span className="text-danger ms-1">*</span>}
    </label>
    {children}
    {hint && <div className="form-text">{hint}</div>}
    {error && <div className="text-danger small mt-1">{error}</div>}
  </div>
);

export function StaffOnboardForm({
  onSubmit,
  saving: savingProp,
  initialValues,
  submitLabel = 'Add Staff Member',
  mode = 'create',
  adminMode = false,
}) {
  const [savingLocal, setSavingLocal] = useState(false);
  const saving = savingProp ?? savingLocal;
  const { isSchoolAdmin } = useAuth();
  const { canWriteModule } = usePermissions();
  const canSubmit = adminMode || isSchoolAdmin || canWriteModule('human_resource') || canWriteModule('core_management');

  const { register, handleSubmit, setValue, control, formState: { errors } } = useForm({
    defaultValues: {
      has_portal_access: true,
      employment_type: 'full_time',
      status: 'active',
      nationality: 'Ugandan',
      portal_role: 'teacher',
      date_joined: new Date().toISOString().slice(0, 10),
      ...initialValues,
    },
  });

  const wrapSubmit = async (data) => {
    setSavingLocal(true);
    try {
      await onSubmit(data);
    } finally {
      setSavingLocal(false);
    }
  };

  const portalRole = useWatch({ control, name: 'portal_role' });
  const hasPortalAccess = useWatch({ control, name: 'has_portal_access' });
  const staffCategory = useWatch({ control, name: 'staff_category' });

  const { data: roleOptions = FALLBACK_STAFF_ROLES } = useQuery({
    queryKey: ['staff', 'role-options'],
    queryFn: () => staffService.getRoleOptions(),
    staleTime: 5 * 60 * 1000,
  });

  const { data: departments = [] } = useQuery({
    queryKey: ['departments'],
    queryFn: () => departmentsService.list(),
  });

  const selectedRole = useMemo(
    () => roleOptions.find((r) => r.role === portalRole) || FALLBACK_STAFF_ROLES[4],
    [roleOptions, portalRole],
  );

  useEffect(() => {
    if (!selectedRole || mode === 'edit') return;
    setValue('staff_category', selectedRole.category);
    setValue('designation', selectedRole.default_designation);
    setValue('has_portal_access', selectedRole.portal_access_default);
  }, [selectedRole, setValue, mode]);

  const showTeachingFields = selectedRole?.requires_teacher_profile
    || staffCategory === 'teaching';

  // Drop nested teacher values when role is not teaching so empty years_experience
  // is never submitted for bursars, librarians, etc.
  useEffect(() => {
    if (mode === 'edit') return;
    if (!showTeachingFields) {
      setValue('teacher', undefined);
    }
  }, [showTeachingFields, setValue, mode]);

  return (
    <form onSubmit={handleSubmit(wrapSubmit)} className="staff-onboard-form">
      <Section title="Personal Information" icon={FiUser}>
        <Field label="First Name" required error={errors.first_name?.message}>
          <input className="form-control" {...register('first_name', { required: 'First name is required' })} />
        </Field>
        <Field label="Middle Name" error={errors.middle_name?.message}>
          <input className="form-control" {...register('middle_name')} />
        </Field>
        <Field label="Last Name" required error={errors.last_name?.message}>
          <input className="form-control" {...register('last_name', { required: 'Last name is required' })} />
        </Field>
        <Field label="Gender" error={errors.gender?.message}>
          <select className="form-select" {...register('gender')}>
            {GENDER_OPTIONS.map((o) => (
              <option key={o.value || 'na'} value={o.value}>{o.label}</option>
            ))}
          </select>
        </Field>
        <Field label="Date of Birth" error={errors.date_of_birth?.message}>
          <input type="date" className="form-control" {...register('date_of_birth')} />
        </Field>
        <Field label="National ID / Passport" error={errors.national_id?.message}>
          <input className="form-control" {...register('national_id')} />
        </Field>
        <Field label="Nationality" error={errors.nationality?.message}>
          <input className="form-control" {...register('nationality')} />
        </Field>
      </Section>

      <Section title="Contact Details" icon={FiMail}>
        <Field
          label="Work Email"
          required
          error={errors.email?.message}
          hint="Used for official communication and portal login"
        >
          <input
            type="email"
            className="form-control"
            {...register('email', emailValidationRules({ label: 'Work email' }))}
          />
        </Field>
        <Field label="Personal Email" error={errors.personal_email?.message}>
          <input type="email" className="form-control" {...register('personal_email', emailValidationRules({ required: false, label: 'Personal email' }))} />
        </Field>
        <Field label="Phone" required error={errors.phone?.message}>
          <input className="form-control" {...register('phone', { required: 'Phone is required' })} />
        </Field>
        <Field label="Alternate Phone" error={errors.alternate_phone?.message}>
          <input className="form-control" {...register('alternate_phone')} />
        </Field>
        <div className="col-12">
          <Field label="Residential Address" error={errors.address?.message}>
            <textarea className="form-control" rows={2} {...register('address')} />
          </Field>
        </div>
        <Field label="Emergency Contact Name" error={errors.emergency_contact?.message}>
          <input className="form-control" {...register('emergency_contact')} />
        </Field>
        <Field label="Emergency Contact Phone" error={errors.emergency_phone?.message}>
          <input className="form-control" {...register('emergency_phone')} />
        </Field>
        <Field label="Relationship to Emergency Contact" error={errors.emergency_relationship?.message}>
          <input className="form-control" placeholder="e.g. Spouse, Parent" {...register('emergency_relationship')} />
        </Field>
      </Section>

      <Section title="Employment & Role" icon={FiBriefcase}>
        <Field label="Employee ID" hint={mode === 'create' ? 'Leave blank to auto-generate' : 'Admin-managed identifier'} error={errors.employee_id?.message}>
          <input className="form-control" placeholder="Auto-generated if empty" readOnly={mode === 'edit' && !adminMode} {...register('employee_id')} />
        </Field>
        <Field label="Dashboard Role" required error={errors.portal_role?.message}>
          <select className="form-select" {...register('portal_role', { required: true })}>
            {roleOptions.map((r) => (
              <option key={r.role} value={r.role}>{r.label}</option>
            ))}
          </select>
          {selectedRole?.description && (
            <div className="staff-role-hint mt-2">
              <span className="badge text-bg-light border me-1">{selectedRole.category}</span>
              {selectedRole.description}
            </div>
          )}
        </Field>
        <Field
          label="Staff Category"
          error={errors.staff_category?.message}
          hint="Defaults from the selected dashboard role; can be changed later"
        >
          <select className="form-select" {...register('staff_category')}>
            {STAFF_CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </Field>
        <Field
          label="Designation / Job Title"
          error={errors.designation?.message}
          hint="Optional — defaults from role; staff can complete this in My Profile"
        >
          <input className="form-control" {...register('designation')} />
        </Field>
        <Field label="Department" error={errors.department?.message}>
          <select className="form-select" {...register('department')}>
            <option value="">— Select department —</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </Field>
        <Field label="Employment Type" error={errors.employment_type?.message}>
          <select className="form-select" {...register('employment_type')}>
            {EMPLOYMENT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </Field>
        <Field
          label="Date Joined"
          error={errors.date_joined?.message}
          hint="Optional — defaults to today if left blank"
        >
          <input type="date" className="form-control" {...register('date_joined')} />
        </Field>
        <Field label="Status" error={errors.status?.message}>
          <select className="form-select" {...register('status')}>
            <option value="active">Active</option>
            <option value="on_leave">On Leave</option>
            <option value="suspended">Suspended</option>
            <option value="terminated">Terminated</option>
          </select>
        </Field>
        <div className="col-12">
          <Field label="Qualifications Summary" error={errors.qualification_summary?.message}>
            <textarea className="form-control" rows={2} {...register('qualification_summary')} />
          </Field>
        </div>
      </Section>

      {showTeachingFields && (
        <Section title="Teaching Profile" icon={FiUsers}>
          <div className="col-12">
            <p className="text-muted small mb-0">
              Optional for now — teachers can finish these details later under My Profile.
            </p>
          </div>
          <Field label="Highest Qualification" error={errors['teacher.qualification']?.message}>
            <input className="form-control" {...register('teacher.qualification')} />
          </Field>
          <Field label="Specialization" error={errors['teacher.specialization']?.message}>
            <input className="form-control" {...register('teacher.specialization')} />
          </Field>
          <Field
            label="Years of Experience"
            error={errors['teacher.years_experience']?.message}
            hint="Leave blank if unknown"
          >
            <input type="number" min={0} className="form-control" {...register('teacher.years_experience')} />
          </Field>
          <div className="col-md-6 d-flex align-items-end">
            <div className="form-check">
              <input type="checkbox" className="form-check-input" id="is_class_teacher" {...register('teacher.is_class_teacher')} />
              <label className="form-check-label small" htmlFor="is_class_teacher">Class Teacher</label>
            </div>
          </div>
        </Section>
      )}

      <Section title="Portal Access" icon={FiLock}>
        <div className="col-12">
          <div className="form-check form-switch mb-3">
            <input type="checkbox" className="form-check-input" id="has_portal_access" {...register('has_portal_access')} />
            <label className="form-check-label fw-medium" htmlFor="has_portal_access">
              Grant dashboard portal access
            </label>
            <div className="form-text">
              Creates a login account with the selected role. Permissions follow your school&apos;s plan and Permission Settings.
            </div>
          </div>
        </div>
        {hasPortalAccess && mode === 'create' && (
          <>
            <Field
              label="Initial Password"
              hint="Leave blank to auto-generate a 6-character one-time password (letters and numbers). The user must set a full password after first sign-in."
              error={errors.password?.message}
            >
              <input type="password" className="form-control" autoComplete="new-password" {...register('password', { minLength: { value: 8, message: 'If set manually, minimum 8 characters' } })} />
            </Field>
            <div className="col-md-6 d-flex align-items-end">
              <div className="form-check">
                <input type="checkbox" className="form-check-input" id="mark_email_verified" {...register('mark_email_verified')} />
                <label className="form-check-label small" htmlFor="mark_email_verified">Mark email as verified</label>
              </div>
            </div>
          </>
        )}
        <div className="col-12">
          <Field label="Internal Notes" error={errors.notes?.message}>
            <textarea className="form-control" rows={2} placeholder="HR notes (not visible to staff)" {...register('notes')} />
          </Field>
        </div>
      </Section>

      <div className="d-flex justify-content-end gap-2 pt-2">
        {!canSubmit && (
          <span className="text-muted small align-self-center me-2">You do not have permission to add staff.</span>
        )}
        <button type="submit" className="btn btn-primary" disabled={saving || !canSubmit}>
          {saving ? 'Saving…' : submitLabel}
        </button>
      </div>
    </form>
  );
}

export default StaffOnboardForm;