import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useQuery } from '@tanstack/react-query';
import {
  FiBook, FiHome, FiMapPin, FiUser, FiUsers,
} from 'react-icons/fi';
import {
  WorkspaceFieldGrid, WorkspaceSection,
} from './WorkspaceShell';
import { classesService, parentsService } from '../services/moduleService';
import { emailValidationRules } from '../utils/emailValidation';

const GENDER_OPTIONS = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
];

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'graduated', label: 'Graduated' },
  { value: 'transferred', label: 'Transferred' },
  { value: 'suspended', label: 'Suspended' },
  { value: 'withdrawn', label: 'Withdrawn' },
];

const CURRICULUM_OPTIONS = [
  { value: 'uneb', label: 'UNEB (Uganda)' },
  { value: 'uganda_cbe', label: 'Uganda Competence-Based' },
  { value: 'igcse', label: 'IGCSE' },
  { value: 'ace', label: 'ACE' },
  { value: 'cbc', label: 'CBC (Kenya)' },
  { value: '844', label: '8-4-4' },
  { value: 'other', label: 'Other' },
];

const BOARDING_OPTIONS = [
  { value: 'day', label: 'Day Scholar' },
  { value: 'boarding', label: 'Boarding' },
  { value: 'weekly', label: 'Weekly Boarding' },
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

export function StudentForm({
  onSubmit,
  initialValues,
  submitLabel = 'Save student',
  mode = 'create',
  lockClassFields = false,
  lockedClassLabel = '',
  lockedStreamLabel = '',
}) {
  const [saving, setSaving] = useState(false);
  const [activeSection, setActiveSection] = useState('identity');

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm({
    defaultValues: {
      gender: 'male',
      status: 'active',
      nationality: 'Ugandan',
      curriculum_pathway: 'uneb',
      boarding_status: 'day',
      special_needs: false,
      enrollment_date: new Date().toISOString().slice(0, 10),
      parents: [],
      ...initialValues,
    },
  });

  const schoolClassId = watch('school_class');
  const specialNeeds = watch('special_needs');

  const { data: classes = [] } = useQuery({
    queryKey: ['classes'],
    queryFn: () => classesService.list(),
  });

  const { data: parents = [] } = useQuery({
    queryKey: ['parents'],
    queryFn: () => parentsService.list(),
  });

  const { data: streams = [] } = useQuery({
    queryKey: ['streams', schoolClassId],
    queryFn: () => classesService.listStreams?.(schoolClassId) || Promise.resolve([]),
    enabled: Boolean(schoolClassId),
  });

  useEffect(() => {
    if (initialValues?.parents?.length) {
      setValue('parents', initialValues.parents.map((p) => (typeof p === 'object' ? p.id : p)));
    }
  }, [initialValues, setValue]);

  const wrapSubmit = async (data) => {
    setSaving(true);
    try {
      const payload = { ...data };
      if (!payload.stream) delete payload.stream;
      if (!payload.school_class) delete payload.school_class;
      if (!payload.parents?.length) delete payload.parents;
      await onSubmit(payload);
    } finally {
      setSaving(false);
    }
  };

  const sections = [
    { id: 'identity', label: 'Identity', icon: FiUser },
    { id: 'academic', label: 'Academic', icon: FiBook },
    { id: 'location', label: 'Location', icon: FiMapPin },
    { id: 'family', label: 'Family', icon: FiUsers },
    { id: 'other', label: 'Other', icon: FiHome },
  ];

  return (
    <form onSubmit={handleSubmit(wrapSubmit)}>
      {mode === 'create' && (
        <div className="alert alert-light border small mb-3">
          Only <strong>Identity</strong> and <strong>Academic</strong> tabs are needed to enroll.
          Other sections can be completed later by the class teacher.
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

      {activeSection === 'identity' && (
        <WorkspaceSection title="Student identity" description="Legal name, admission details, and national identifiers">
          <WorkspaceFieldGrid>
            <Field
              label="Admission Number"
              required={!lockClassFields}
              hint={lockClassFields ? 'Leave blank to auto-generate on enrollment.' : undefined}
              error={errors.admission_number?.message}
            >
              <input
                className="form-control"
                {...register('admission_number', { required: lockClassFields ? false : 'Required' })}
                readOnly={mode === 'edit'}
                placeholder={lockClassFields ? 'Auto-generated if empty' : undefined}
              />
            </Field>
            <Field label="Registration / Index number" hint="UNEB candidate or school registration number">
              <input className="form-control" {...register('registration_number')} />
            </Field>
            <Field label="Legacy national ID" hint="Optional legacy learner ID (e.g. former UPI)">
              <input className="form-control" {...register('upi_number')} />
            </Field>
            <Field label="First Name" required error={errors.first_name?.message}>
              <input className="form-control" {...register('first_name', { required: 'Required' })} />
            </Field>
            <Field label="Middle Name">
              <input className="form-control" {...register('middle_name')} />
            </Field>
            <Field label="Last Name" required error={errors.last_name?.message}>
              <input className="form-control" {...register('last_name', { required: 'Required' })} />
            </Field>
            <Field label="Gender" required>
              <select className="form-select" {...register('gender', { required: true })}>
                {GENDER_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </Field>
            <Field label="Date of Birth" required error={errors.date_of_birth?.message}>
              <input type="date" className="form-control" {...register('date_of_birth', { required: 'Required' })} />
            </Field>
            <Field label="Birth Certificate No.">
              <input className="form-control" {...register('birth_certificate_number')} />
            </Field>
            <Field label="National ID" hint="For older learners">
              <input className="form-control" {...register('national_id')} />
            </Field>
            <Field label="Place of Birth">
              <input className="form-control" {...register('place_of_birth')} />
            </Field>
          </WorkspaceFieldGrid>
        </WorkspaceSection>
      )}

      {activeSection === 'academic' && (
        <WorkspaceSection title="Academic placement" description="Class, stream, curriculum, and enrollment">
          <WorkspaceFieldGrid>
            <Field label="Class" required error={errors.school_class?.message}>
              {lockClassFields ? (
                <>
                  <input type="hidden" {...register('school_class', { required: 'Select a class' })} />
                  <div className="form-control bg-light">{lockedClassLabel || 'Selected class'}</div>
                </>
              ) : (
                <select className="form-select" {...register('school_class', { required: 'Select a class' })}>
                  <option value="">Select class</option>
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>{c.name} ({c.code})</option>
                  ))}
                </select>
              )}
            </Field>
            <Field label="Stream">
              {lockClassFields ? (
                <>
                  <input type="hidden" {...register('stream')} />
                  <div className="form-control bg-light">{lockedStreamLabel || 'Whole class'}</div>
                </>
              ) : (
                <select className="form-select" {...register('stream')}>
                  <option value="">No stream</option>
                  {(streams.length ? streams : []).map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              )}
            </Field>
            <Field label="Enrollment Date" required>
              <input type="date" className="form-control" {...register('enrollment_date', { required: true })} />
            </Field>
            <Field label="Status">
              <select className="form-select" {...register('status')}>
                {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </Field>
            <Field label="Curriculum Pathway">
              <select className="form-select" {...register('curriculum_pathway')}>
                {CURRICULUM_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </Field>
            <Field label="Boarding Status">
              <select className="form-select" {...register('boarding_status')}>
                {BOARDING_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </Field>
            <Field label="Previous School" className="col-12">
              <input className="form-control" {...register('previous_school')} />
            </Field>
          </WorkspaceFieldGrid>
        </WorkspaceSection>
      )}

      {activeSection === 'location' && (
        <WorkspaceSection title="Contact & location" description="District, county, and contact details">
          <WorkspaceFieldGrid>
            <Field label="Phone">
              <input className="form-control" {...register('phone')} />
            </Field>
            <Field label="Email" error={errors.email?.message}>
              <input type="email" className="form-control" {...register('email', emailValidationRules({ required: false, label: 'Email' }))} />
            </Field>
            <Field label="County">
              <input className="form-control" {...register('county')} placeholder="e.g. Nairobi, Kiambu" />
            </Field>
            <Field label="Sub-County">
              <input className="form-control" {...register('sub_county')} />
            </Field>
            <Field label="Ward">
              <input className="form-control" {...register('ward')} />
            </Field>
            <Field label="City / Town">
              <input className="form-control" {...register('city')} />
            </Field>
            <Field label="Nationality">
              <input className="form-control" {...register('nationality')} />
            </Field>
            <Field label="Religion">
              <input className="form-control" {...register('religion')} />
            </Field>
            <Field label="Address" className="col-12">
              <textarea className="form-control" rows={2} {...register('address')} />
            </Field>
          </WorkspaceFieldGrid>
        </WorkspaceSection>
      )}

      {activeSection === 'family' && (
        <WorkspaceSection title="Parents & emergency" description="Link parents and emergency contacts">
          <WorkspaceFieldGrid>
            <Field label="Linked Parents" className="col-12" hint="Hold Ctrl/Cmd to select multiple">
              <select className="form-select" multiple size={5} {...register('parents')}>
                {parents.map((p) => (
                  <option key={p.id} value={p.id}>{p.full_name} — {p.phone}</option>
                ))}
              </select>
            </Field>
            <Field label="Emergency Contact Name">
              <input className="form-control" {...register('emergency_contact_name')} />
            </Field>
            <Field label="Emergency Contact Phone">
              <input className="form-control" {...register('emergency_contact_phone')} />
            </Field>
          </WorkspaceFieldGrid>
        </WorkspaceSection>
      )}

      {activeSection === 'other' && (
        <WorkspaceSection title="Additional information">
          <WorkspaceFieldGrid>
            <Field label="Special Needs" className="col-md-4">
              <div className="form-check form-switch mt-2">
                <input type="checkbox" className="form-check-input" {...register('special_needs')} />
                <label className="form-check-label small">Learner has special needs</label>
              </div>
            </Field>
            {specialNeeds && (
              <Field label="Special Needs Details" className="col-12">
                <textarea className="form-control" rows={2} {...register('special_needs_details')} />
              </Field>
            )}
            <Field label="Notes" className="col-12">
              <textarea className="form-control" rows={3} {...register('notes')} />
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

export default StudentForm;