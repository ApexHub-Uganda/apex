import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { emailValidationRules } from '../utils/emailValidation';
import { FiMapPin, FiPhone, FiUser } from 'react-icons/fi';
import { WorkspaceFieldGrid, WorkspaceSection } from './WorkspaceShell';

const GENDER_OPTIONS = [
  { value: '', label: 'Not specified' },
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
];

const RELATIONSHIP_OPTIONS = [
  { value: 'father', label: 'Father' },
  { value: 'mother', label: 'Mother' },
  { value: 'guardian', label: 'Guardian' },
  { value: 'sponsor', label: 'Sponsor' },
  { value: 'other', label: 'Other' },
];

const CONTACT_OPTIONS = [
  { value: 'sms', label: 'SMS' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'phone', label: 'Phone Call' },
  { value: 'email', label: 'Email' },
];

const Field = ({ label, required, error, children, hint, className = 'col-md-6' }) => (
  <div className={className}>
    <label className="form-label small fw-medium">
      {label}
      {required && <span className="text-danger ms-1">*</span>}
    </label>
    {children}
    {hint && <div className="form-text">{hint}</div>}
    {error && <div className="text-danger small mt-1">{error}</div>}
  </div>
);

export function ParentForm({ onSubmit, initialValues, submitLabel = 'Save parent', mode = 'create' }) {
  const [saving, setSaving] = useState(false);
  const [activeSection, setActiveSection] = useState('personal');

  const { register, handleSubmit, formState: { errors } } = useForm({
    defaultValues: {
      country: 'Uganda',
      relationship_to_student: 'guardian',
      preferred_contact_method: 'sms',
      consent_for_sms: true,
      is_fee_payer: false,
      is_emergency_contact: true,
      ...initialValues,
    },
  });

  const wrapSubmit = async (data) => {
    setSaving(true);
    try {
      await onSubmit(data);
    } finally {
      setSaving(false);
    }
  };

  const sections = [
    { id: 'personal', label: 'Personal', icon: FiUser },
    { id: 'contact', label: 'Contact', icon: FiPhone },
    { id: 'location', label: 'Location', icon: FiMapPin },
  ];

  return (
    <form onSubmit={handleSubmit(wrapSubmit)}>
      {mode === 'create' && (
        <div className="alert alert-light border small mb-3">
          <strong>Personal</strong> and <strong>Contact</strong> tabs are enough to register a parent.
          Address and M-Pesa details can be completed in the full profile later.
        </div>
      )}
      <div className="apex-workspace-tabs mb-3">
        {sections.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`apex-workspace-tab ${activeSection === id ? 'is-active' : ''}`}
            onClick={() => setActiveSection(id)}
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {activeSection === 'personal' && (
        <WorkspaceSection title="Personal details">
          <WorkspaceFieldGrid>
            <Field label="First Name" required error={errors.first_name?.message}>
              <input className="form-control" {...register('first_name', { required: 'Required' })} />
            </Field>
            <Field label="Middle Name">
              <input className="form-control" {...register('middle_name')} />
            </Field>
            <Field label="Last Name" required error={errors.last_name?.message}>
              <input className="form-control" {...register('last_name', { required: 'Required' })} />
            </Field>
            <Field label="Gender">
              <select className="form-select" {...register('gender')}>
                {GENDER_OPTIONS.map((o) => <option key={o.value || 'na'} value={o.value}>{o.label}</option>)}
              </select>
            </Field>
            <Field label="National ID">
              <input className="form-control" {...register('national_id')} />
            </Field>
            <Field label="Relationship to Student">
              <select className="form-select" {...register('relationship_to_student')}>
                {RELATIONSHIP_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </Field>
            <Field label="Occupation">
              <input className="form-control" {...register('occupation')} />
            </Field>
            <Field label="Employer">
              <input className="form-control" {...register('employer')} />
            </Field>
          </WorkspaceFieldGrid>
        </WorkspaceSection>
      )}

      {activeSection === 'contact' && (
        <WorkspaceSection title="Contact & payments" description="Mobile money and SMS preferences for East African schools">
          <WorkspaceFieldGrid>
            <Field label="Primary Email" required error={errors.email?.message}>
              <input type="email" className="form-control" {...register('email', emailValidationRules({ label: 'Primary email' }))} />
            </Field>
            <Field label="Alternate Email" error={errors.alternate_email?.message}>
              <input type="email" className="form-control" {...register('alternate_email', emailValidationRules({ required: false, label: 'Alternate email' }))} />
            </Field>
            <Field label="Phone" required error={errors.phone?.message}>
              <input className="form-control" {...register('phone', { required: 'Required' })} />
            </Field>
            <Field label="Alternate Phone">
              <input className="form-control" {...register('alternate_phone')} />
            </Field>
            <Field label="M-Pesa Phone" hint="Number used for fee payments">
              <input className="form-control" {...register('mpesa_phone')} />
            </Field>
            <Field label="Preferred Contact">
              <select className="form-select" {...register('preferred_contact_method')}>
                {CONTACT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </Field>
            <Field label="Fee Payer" className="col-md-4">
              <div className="form-check form-switch mt-2">
                <input type="checkbox" className="form-check-input" {...register('is_fee_payer')} />
                <label className="form-check-label small">Primary fee payer</label>
              </div>
            </Field>
            <Field label="SMS Consent" className="col-md-4">
              <div className="form-check form-switch mt-2">
                <input type="checkbox" className="form-check-input" {...register('consent_for_sms')} />
                <label className="form-check-label small">Consent for SMS alerts</label>
              </div>
            </Field>
          </WorkspaceFieldGrid>
        </WorkspaceSection>
      )}

      {activeSection === 'location' && (
        <WorkspaceSection title="Address">
          <WorkspaceFieldGrid>
            <Field label="County">
              <input className="form-control" {...register('county')} />
            </Field>
            <Field label="Sub-County">
              <input className="form-control" {...register('sub_county')} />
            </Field>
            <Field label="City / Town">
              <input className="form-control" {...register('city')} />
            </Field>
            <Field label="Country">
              <input className="form-control" {...register('country')} />
            </Field>
            <Field label="Postal Code">
              <input className="form-control" {...register('postal_code')} />
            </Field>
            <Field label="Address" className="col-12">
              <textarea className="form-control" rows={2} {...register('address')} />
            </Field>
            <Field label="Notes" className="col-12">
              <textarea className="form-control" rows={2} {...register('notes')} />
            </Field>
          </WorkspaceFieldGrid>
        </WorkspaceSection>
      )}

      <div className="d-flex justify-content-end mt-3 pt-3 border-top">
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? 'Saving…' : submitLabel}
        </button>
      </div>
    </form>
  );
}

export default ParentForm;