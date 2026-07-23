import { useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Link, Navigate } from 'react-router-dom';
import {
  FiSave, FiDroplet, FiShield, FiImage, FiFileText, FiMapPin, FiMail, FiPhone, FiGlobe, FiRotateCcw, FiUsers,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import { useTenant } from '../../hooks/useTenant';
import { useAuth } from '../../hooks/useAuth';
import { tenantService } from '../../services/tenantService';
import { notify } from '../../utils/notify';

const TIMEZONES = [
  { value: 'Africa/Nairobi', label: 'East Africa Time (Nairobi)' },
  { value: 'Africa/Lagos', label: 'West Africa Time (Lagos)' },
  { value: 'Africa/Johannesburg', label: 'South Africa Standard Time' },
  { value: 'UTC', label: 'UTC' },
  { value: 'Europe/London', label: 'London' },
  { value: 'America/New_York', label: 'Eastern Time' },
  { value: 'Asia/Kolkata', label: 'India Standard Time' },
];

/** Platform default palette (Apex brand) — same as :root in global.css */
const APEX_DEFAULT_THEME = {
  primary_color: '#0F766E',
  secondary_color: '#FF7F50',
  accent_color: '#F5E6CA',
};

const applyLiveTheme = (colors) => {
  const root = document.documentElement;
  if (colors.primary_color) root.style.setProperty('--apex-primary', colors.primary_color);
  if (colors.secondary_color) root.style.setProperty('--apex-secondary', colors.secondary_color);
  if (colors.accent_color) root.style.setProperty('--apex-accent', colors.accent_color);
};

export function SchoolAdminSettings() {
  const { tenant, refetch, isSchoolAdmin } = useTenant();
  const { isSchoolAdmin: authIsSchoolAdmin, isSuperAdmin } = useAuth();
  const canManageSettings = Boolean(isSchoolAdmin || authIsSchoolAdmin || isSuperAdmin);
  const queryClient = useQueryClient();
  const [logoFile, setLogoFile] = useState(null);
  const [logoPreview, setLogoPreview] = useState(tenant?.logo || null);
  const [clearLogo, setClearLogo] = useState(false);
  const [previewing, setPreviewing] = useState(false);

  const defaults = useMemo(() => ({
    school_name: tenant?.name || '',
    email: tenant?.email || '',
    phone: tenant?.phone || '',
    address: tenant?.address || '',
    city: tenant?.city || '',
    country: tenant?.country || 'Uganda',
    website: tenant?.website || '',
    tagline: tenant?.tagline || '',
    timezone: tenant?.timezone || 'Africa/Nairobi',
    primary_color: tenant?.theme?.primary || tenant?.primary_color || '#0F766E',
    secondary_color: tenant?.theme?.secondary || tenant?.secondary_color || '#FF7F50',
    accent_color: tenant?.theme?.accent || tenant?.accent_color || '#F5E6CA',
  }), [tenant]);

  const { register, handleSubmit, watch, reset, setValue, formState: { isDirty, isSubmitting } } = useForm({
    defaultValues: defaults,
  });

  useEffect(() => {
    reset(defaults);
    setLogoPreview(tenant?.logo || null);
    setLogoFile(null);
    setClearLogo(false);
  }, [defaults, reset, tenant?.logo]);

  // Live theme preview while picking colours (before save).
  const watchedColors = watch(['primary_color', 'secondary_color', 'accent_color']);
  useEffect(() => {
    applyLiveTheme({
      primary_color: watchedColors[0],
      secondary_color: watchedColors[1],
      accent_color: watchedColors[2],
    });
  }, [watchedColors]);

  const saveMutation = useMutation({
    mutationFn: async (formValues) => {
      const fd = new FormData();
      fd.append('name', formValues.school_name || '');
      fd.append('email', formValues.email || '');
      fd.append('phone', formValues.phone || '');
      fd.append('address', formValues.address || '');
      fd.append('city', formValues.city || '');
      fd.append('country', formValues.country || '');
      fd.append('website', formValues.website || '');
      fd.append('tagline', formValues.tagline || '');
      fd.append('timezone', formValues.timezone || 'Africa/Nairobi');
      fd.append('primary_color', formValues.primary_color || '#0F766E');
      fd.append('secondary_color', formValues.secondary_color || '#FF7F50');
      fd.append('accent_color', formValues.accent_color || '#F5E6CA');
      if (clearLogo) {
        fd.append('clear_logo', 'true');
      }
      if (logoFile) {
        fd.append('logo', logoFile);
      }
      return tenantService.updateSettings(fd);
    },
    onSuccess: async (data) => {
      const patch = data?.context_patch || data;
      if (patch?.primary_color) {
        applyLiveTheme({
          primary_color: patch.primary_color,
          secondary_color: patch.secondary_color,
          accent_color: patch.accent_color,
        });
      }
      if (data?.logo_url) {
        setLogoPreview(data.logo_url);
      } else if (clearLogo) {
        setLogoPreview(null);
      }
      setLogoFile(null);
      setClearLogo(false);
      await queryClient.invalidateQueries({ queryKey: ['tenant'] });
      await refetch?.();
      notify.success('School settings saved. Branding will apply to the portal and PDFs.');
    },
    onError: (err) => {
      const msg = err?.response?.data?.error?.message
        || err?.response?.data?.message
        || Object.values(err?.response?.data || {}).flat?.()?.[0]
        || err?.message
        || 'Could not save school settings.';
      notify.error(typeof msg === 'string' ? msg : 'Could not save school settings.');
    },
  });

  const onSubmit = (formValues) => saveMutation.mutateAsync(formValues);

  const onLogoChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      notify.error('Please choose an image file for the school logo.');
      return;
    }
    if (file.size > 4 * 1024 * 1024) {
      notify.error('Logo must be 4 MB or smaller.');
      return;
    }
    setLogoFile(file);
    setClearLogo(false);
    const url = URL.createObjectURL(file);
    setLogoPreview(url);
  };

  const handlePdfPreview = async () => {
    setPreviewing(true);
    try {
      if (isDirty || logoFile || clearLogo) {
        notify.info('Save your settings first so the preview matches the latest branding.');
      }
      await tenantService.downloadPdfPreview();
      notify.success('PDF template preview downloaded.');
    } catch (err) {
      notify.error(err?.message || 'Unable to generate PDF preview.');
    } finally {
      setPreviewing(false);
    }
  };

  const resetThemeToApexDefaults = () => {
    setValue('primary_color', APEX_DEFAULT_THEME.primary_color, { shouldDirty: true, shouldTouch: true });
    setValue('secondary_color', APEX_DEFAULT_THEME.secondary_color, { shouldDirty: true, shouldTouch: true });
    setValue('accent_color', APEX_DEFAULT_THEME.accent_color, { shouldDirty: true, shouldTouch: true });
    applyLiveTheme(APEX_DEFAULT_THEME);
    notify.info('Colours reset to Apex defaults. Save settings to apply permanently.');
  };

  const colorsAreDefault = (
    (watchedColors[0] || '').toUpperCase() === APEX_DEFAULT_THEME.primary_color.toUpperCase()
    && (watchedColors[1] || '').toUpperCase() === APEX_DEFAULT_THEME.secondary_color.toUpperCase()
    && (watchedColors[2] || '').toUpperCase() === APEX_DEFAULT_THEME.accent_color.toUpperCase()
  );

  const saving = isSubmitting || saveMutation.isPending;

  // Defense in depth: never render school settings UI for non-admins
  // (route guard also enforces school_admin; keep this after all hooks)
  if (!canManageSettings) {
    return <Navigate to="/school-admin" replace />;
  }

  return (
    <div>
      <PageHeader
        title="School Settings"
        subtitle="Institution profile, colour scheme, logo, and PDF document branding"
      />

      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="row g-4">
          {/* Institution profile */}
          <div className="col-lg-7">
            <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <h5 className="fw-bold mb-1">Institution information</h5>
              <p className="text-muted small mb-3">
                Shown on official PDFs (header centre) and across the school portal.
              </p>

              <div className="mb-3">
                <label className="form-label small fw-medium">School name</label>
                <input className="form-control" {...register('school_name', { required: true })} disabled={!isSchoolAdmin} />
              </div>

              <div className="row g-3">
                <div className="col-md-6">
                  <label className="form-label small fw-medium d-flex align-items-center gap-1">
                    <FiMail size={14} /> Contact email
                  </label>
                  <input type="email" className="form-control" {...register('email', { required: true })} disabled={!isSchoolAdmin} />
                </div>
                <div className="col-md-6">
                  <label className="form-label small fw-medium d-flex align-items-center gap-1">
                    <FiPhone size={14} /> Phone
                  </label>
                  <input className="form-control" {...register('phone')} disabled={!isSchoolAdmin} placeholder="+254..." />
                </div>
              </div>

              <div className="mt-3 mb-3">
                <label className="form-label small fw-medium d-flex align-items-center gap-1">
                  <FiMapPin size={14} /> Physical address
                </label>
                <textarea className="form-control" rows={2} {...register('address')} disabled={!isSchoolAdmin} placeholder="Street, building, P.O. Box..." />
              </div>

              <div className="row g-3">
                <div className="col-md-4">
                  <label className="form-label small fw-medium">City</label>
                  <input className="form-control" {...register('city')} disabled={!isSchoolAdmin} />
                </div>
                <div className="col-md-4">
                  <label className="form-label small fw-medium">Country</label>
                  <input className="form-control" {...register('country')} disabled={!isSchoolAdmin} />
                </div>
                <div className="col-md-4">
                  <label className="form-label small fw-medium">Timezone</label>
                  <select className="form-select" {...register('timezone')} disabled={!isSchoolAdmin}>
                    {TIMEZONES.map((tz) => (
                      <option key={tz.value} value={tz.value}>{tz.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="row g-3 mt-1">
                <div className="col-md-6">
                  <label className="form-label small fw-medium d-flex align-items-center gap-1">
                    <FiGlobe size={14} /> Website
                  </label>
                  <input className="form-control" {...register('website')} disabled={!isSchoolAdmin} placeholder="https://" />
                </div>
                <div className="col-md-6">
                  <label className="form-label small fw-medium">Motto / tagline</label>
                  <input
                    className="form-control"
                    {...register('tagline')}
                    disabled={!isSchoolAdmin}
                    placeholder="Excellence in education"
                  />
                  <div className="form-text">Appears under the PDF footer underline.</div>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Logo + theme */}
          <div className="col-lg-5">
            <motion.div className="apex-card p-4 mb-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.05 }}>
              <h5 className="fw-bold mb-1 d-flex align-items-center gap-2">
                <FiImage /> Institution logo
              </h5>
              <p className="text-muted small mb-3">
                Used on the top-left of every branded PDF (report cards, letters, statements).
              </p>
              <div className="d-flex align-items-center gap-3 mb-3">
                <div
                  className="border rounded d-flex align-items-center justify-content-center bg-white"
                  style={{ width: 88, height: 88, overflow: 'hidden' }}
                >
                  {logoPreview && !clearLogo ? (
                    <img src={logoPreview} alt="School logo" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
                  ) : (
                    <span className="text-muted small text-center px-2">No logo</span>
                  )}
                </div>
                <div className="flex-grow-1">
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/gif"
                    className="form-control form-control-sm"
                    onChange={onLogoChange}
                    disabled={!isSchoolAdmin}
                  />
                  <div className="form-text">PNG or JPG, max 4 MB. Square logos work best.</div>
                  {(logoPreview || logoFile) && isSchoolAdmin && (
                    <button
                      type="button"
                      className="btn btn-link btn-sm text-danger px-0 mt-1"
                      onClick={() => {
                        setLogoFile(null);
                        setClearLogo(true);
                        setLogoPreview(null);
                      }}
                    >
                      Remove logo
                    </button>
                  )}
                </div>
              </div>
            </motion.div>

            <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
              <div className="d-flex flex-wrap align-items-start justify-content-between gap-2 mb-1">
                <h5 className="fw-bold mb-0 d-flex align-items-center gap-2">
                  <FiDroplet /> Colour scheme
                </h5>
                {isSchoolAdmin && (
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm d-inline-flex align-items-center gap-1"
                    onClick={resetThemeToApexDefaults}
                    disabled={colorsAreDefault}
                    title="Restore Apex platform colours (teal / coral / cream)"
                  >
                    <FiRotateCcw size={14} />
                    Reset to Apex defaults
                  </button>
                )}
              </div>
              <p className="text-muted small mb-3">
                Applies to the school portal theme and PDF header/footer underlines.
                Defaults: primary <code>{APEX_DEFAULT_THEME.primary_color}</code>,
                secondary <code>{APEX_DEFAULT_THEME.secondary_color}</code>,
                accent <code>{APEX_DEFAULT_THEME.accent_color}</code>.
              </p>
              <div className="row g-3">
                <div className="col-4">
                  <label className="form-label small fw-medium">Primary</label>
                  <input type="color" className="form-control form-control-color w-100" {...register('primary_color')} disabled={!isSchoolAdmin} />
                </div>
                <div className="col-4">
                  <label className="form-label small fw-medium">Secondary</label>
                  <input type="color" className="form-control form-control-color w-100" {...register('secondary_color')} disabled={!isSchoolAdmin} />
                </div>
                <div className="col-4">
                  <label className="form-label small fw-medium">Accent</label>
                  <input type="color" className="form-control form-control-color w-100" {...register('accent_color')} disabled={!isSchoolAdmin} />
                </div>
              </div>
              <div
                className="mt-3 rounded border p-3"
                style={{
                  borderColor: 'var(--apex-border)',
                  background: 'linear-gradient(90deg, var(--apex-primary), var(--apex-secondary))',
                  minHeight: 12,
                }}
              />
              <p className="text-muted small mt-2 mb-0">
                Preview bar updates as you pick colours.
                {colorsAreDefault
                  ? ' Currently matching Apex defaults.'
                  : ' Click “Reset to Apex defaults”, then Save settings to keep the change.'}
              </p>
            </motion.div>
          </div>

          {/* PDF template preview */}
          <div className="col-12">
            <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.12 }}>
              <div className="d-flex flex-wrap align-items-start justify-content-between gap-3">
                <div style={{ maxWidth: 640 }}>
                  <h5 className="fw-bold mb-1 d-flex align-items-center gap-2">
                    <FiFileText /> PDF template
                  </h5>
                  <p className="text-muted small mb-2">
                    All official school documents use a shared A4 layout: logo (left), school details (centre),
                    document QR (right), colour-matched header/footer rules, motto and print timestamp in the footer.
                    Body content sits in the middle of the page on a white background.
                  </p>
                  <ul className="small text-muted mb-0 ps-3">
                    <li>Header & footer underlines use your <strong>primary</strong> colour (secondary accent line)</li>
                    <li>QR encodes document type and reference metadata (results, admission letters, etc.)</li>
                    <li>Save branding above before previewing so the PDF matches your latest settings</li>
                  </ul>
                </div>
                <button
                  type="button"
                  className="btn btn-outline-primary d-flex align-items-center gap-2"
                  onClick={handlePdfPreview}
                  disabled={previewing || !isSchoolAdmin}
                >
                  <FiFileText />
                  {previewing ? 'Generating…' : 'Download PDF preview'}
                </button>
              </div>
            </motion.div>
          </div>

          <div className="col-12">
            <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}>
              <div className="d-flex flex-wrap align-items-center justify-content-between gap-3">
                <div>
                  <h5 className="fw-bold mb-1 d-flex align-items-center gap-2"><FiShield /> Role permissions</h5>
                  <p className="text-muted small mb-0">
                    Configure read/write access for each staff role and parent portal users.
                  </p>
                </div>
                <Link to="/school-admin/settings/permissions" className="btn btn-outline-primary btn-sm">
                  Open permission settings
                </Link>
              </div>
            </motion.div>
          </div>

          <div className="col-12">
            <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.18 }}>
              <div className="d-flex flex-wrap align-items-center justify-content-between gap-3">
                <div>
                  <h5 className="fw-bold mb-1 d-flex align-items-center gap-2"><FiUsers /> Dual roles</h5>
                  <p className="text-muted small mb-0">
                    Grant a second portal role to a user (e.g. teacher + parent). Same login; they switch from the avatar menu.
                  </p>
                </div>
                <Link to="/school-admin/settings/dual-roles" className="btn btn-outline-primary btn-sm">
                  Configure dual roles
                </Link>
              </div>
            </motion.div>
          </div>

          <div className="col-12">
            <motion.div className="apex-card p-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
              <div className="d-flex flex-wrap align-items-center justify-content-between gap-3">
                <div>
                  <h5 className="fw-bold mb-1 d-flex align-items-center gap-2"><FiMapPin /> School boundary</h5>
                  <p className="text-muted small mb-0">
                    Set the campus GPS perimeter on free OpenStreetMap (at least 4 corners). Staff must be on campus to sign in and to mark class attendance.
                  </p>
                </div>
                <Link to="/school-admin/settings/school-boundary" className="btn btn-outline-primary btn-sm">
                  Configure school boundary
                </Link>
              </div>
            </motion.div>
          </div>
        </div>

        {isSchoolAdmin && (
          <button
            type="submit"
            className="btn btn-primary mt-4 d-flex align-items-center gap-2"
            disabled={saving}
          >
            <FiSave />
            {saving ? 'Saving…' : 'Save settings'}
          </button>
        )}
      </form>
    </div>
  );
}

export default SchoolAdminSettings;
