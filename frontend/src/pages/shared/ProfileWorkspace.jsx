import { useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  FiCamera, FiLock, FiMail, FiPhone, FiSave, FiShield, FiTrash2, FiUser, FiBriefcase,
} from 'react-icons/fi';
import UserAvatar from '../../components/UserAvatar';
import { useAuth } from '../../hooks/useAuth';
import { authService } from '../../services/authService';
import WorkspaceShell, { WorkspaceSection, WorkspaceFieldGrid, ReadOnlyField } from '../../components/WorkspaceShell';
import ProgressBar from '../../components/ProgressBar';
import { extractApiError, notify } from '../../utils/notify';
import { getRoleLabel } from '../../config/schoolRoles';
import { emailValidationRules } from '../../utils/emailValidation';
import { ApexLoader } from '../../components/ApexLoader';

const FIELD_LABELS = {
  first_name: 'First name',
  last_name: 'Last name',
  phone: 'Phone',
  avatar: 'Profile picture',
  address: 'Address',
  emergency_contact: 'Emergency contact',
  emergency_phone: 'Emergency phone',
  personal_email: 'Personal email',
  email: 'Email',
};

export function ProfileWorkspace() {
  const { user, updateUser, isSchoolAdmin } = useAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('personal');
  const [avatarPreview, setAvatarPreview] = useState(null);
  const basePath = user?.role === 'super_admin' ? '/super-admin' : '/school-admin';

  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile', 'me', user?.id],
    queryFn: () => authService.getProfile(),
    enabled: !!user,
  });

  const completion = profile?.profile_completion;
  const staffProfile = profile?.staff_profile;
  const parentProfile = profile?.parent_profile;
  const editable = profile?.editable_fields || {};
  const adminOnly = profile?.admin_only_fields || {};

  const { register, handleSubmit, reset, formState: { isDirty } } = useForm();
  const { register: registerPw, handleSubmit: handlePwSubmit, reset: resetPw, formState: { errors: pwErrors } } = useForm();

  useEffect(() => {
    if (!profile) return;
    reset({
      first_name: profile.first_name || '',
      last_name: profile.last_name || '',
      phone: profile.phone || '',
      staff_profile: {
        middle_name: staffProfile?.middle_name || '',
        phone: staffProfile?.phone || profile.phone || '',
        alternate_phone: staffProfile?.alternate_phone || '',
        personal_email: staffProfile?.personal_email || '',
        address: staffProfile?.address || '',
        emergency_contact: staffProfile?.emergency_contact || '',
        emergency_phone: staffProfile?.emergency_phone || '',
        emergency_relationship: staffProfile?.emergency_relationship || '',
        gender: staffProfile?.gender || '',
      },
      parent_profile: {
        phone: parentProfile?.phone || '',
        alternate_phone: parentProfile?.alternate_phone || '',
        alternate_email: parentProfile?.alternate_email || '',
        address: parentProfile?.address || '',
        city: parentProfile?.city || '',
        occupation: parentProfile?.occupation || '',
        employer: parentProfile?.employer || '',
        preferred_contact_method: parentProfile?.preferred_contact_method || 'email',
      },
    });
  }, [profile, staffProfile, parentProfile, reset]);

  const saveMutation = useMutation({
    mutationFn: (payload) => authService.updateProfile(payload),
    onSuccess: (data) => {
      updateUser(data);
      queryClient.setQueryData(['profile', 'me', user?.id], data);
      notify.success('Profile saved successfully.');
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to save profile.')),
  });

  const avatarMutation = useMutation({
    mutationFn: (file) => authService.uploadAvatar(file),
    onSuccess: (data) => {
      updateUser(data);
      queryClient.setQueryData(['profile', 'me', user?.id], data);
      setAvatarPreview(null);
      notify.success('Profile picture updated.');
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to upload profile picture.')),
  });

  const removeAvatarMutation = useMutation({
    mutationFn: () => authService.deleteAvatar(),
    onSuccess: (data) => {
      updateUser(data);
      queryClient.setQueryData(['profile', 'me', user?.id], data);
      setAvatarPreview(null);
      notify.success('Profile picture removed.');
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to remove profile picture.')),
  });

  const passwordMutation = useMutation({
    mutationFn: (payload) => authService.changePassword(payload),
    onSuccess: () => {
      resetPw();
      notify.success('Password changed successfully.');
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to change password.')),
  });

  const tabs = useMemo(() => {
    const items = [{ id: 'personal', label: 'Personal', icon: FiUser }];
    if (staffProfile) items.push({ id: 'employment', label: 'Employment', icon: FiBriefcase });
    if (staffProfile || parentProfile) items.push({ id: 'contact', label: 'Contact & Emergency', icon: FiPhone });
    items.push({ id: 'security', label: 'Security', icon: FiLock });
    return items;
  }, [staffProfile, parentProfile]);

  const canEditName = !staffProfile && !parentProfile;

  const onSave = (formData) => {
    const payload = {
      phone: formData.phone,
    };
    if (canEditName) {
      payload.first_name = formData.first_name;
      payload.last_name = formData.last_name;
    }
    if (staffProfile && formData.staff_profile) {
      payload.staff_profile = formData.staff_profile;
    }
    if (parentProfile && formData.parent_profile) {
      payload.parent_profile = formData.parent_profile;
    }
    saveMutation.mutate(payload);
  };

  if (isLoading && !profile) {
    return (
      <div className="py-5 text-center">
        <ApexLoader label="Loading…" />
      </div>
    );
  }

  return (
    <WorkspaceShell
      backTo={`${basePath}`}
      backLabel="Dashboard"
      title="My Profile"
      subtitle="Update your personal details. Employment and role information is managed by your school admin."
      actions={activeTab !== 'security' && (
        <button
          type="button"
          className="btn btn-primary d-inline-flex align-items-center gap-2"
          disabled={!isDirty || saveMutation.isPending}
          onClick={handleSubmit(onSave)}
        >
          <FiSave size={15} />
          {saveMutation.isPending ? 'Saving…' : 'Save changes'}
        </button>
      )}
    >
      {completion && !completion.is_complete && (
        <div className="apex-card p-4 mb-4 apex-workspace-completion">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
            <div>
              <h6 className="fw-bold mb-0">Complete your profile</h6>
              <p className="text-muted small mb-0">Fill in missing details for a complete school record.</p>
            </div>
            <span className="fw-bold">{completion.percent}%</span>
          </div>
          <ProgressBar value={completion.percent} />
          <div className="d-flex flex-wrap gap-2 mt-2">
            {(completion.missing_fields || []).slice(0, 6).map((field) => (
              <span key={field} className="badge text-bg-light border">
                {FIELD_LABELS[field.split('.').pop()] || field}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="apex-workspace-tabs mb-4">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              type="button"
              className={`apex-workspace-tab ${activeTab === tab.id ? 'is-active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon size={15} />
              {tab.label}
            </button>
          );
        })}
      </div>

      <form onSubmit={handleSubmit(onSave)}>
        {activeTab === 'personal' && (
          <WorkspaceSection title="Personal information" description="Basic account details you can update anytime." icon={FiUser}>
            <div className="apex-profile-avatar-panel mb-4">
              <div className="d-flex flex-wrap align-items-center gap-3">
                <div className="apex-profile-avatar-preview">
                  {avatarPreview ? (
                    <img src={avatarPreview} alt="Avatar preview" className="apex-user-avatar apex-user-avatar-image" />
                  ) : (
                    <UserAvatar user={profile || user} size={88} />
                  )}
                </div>
                <div className="flex-grow-1">
                  <h6 className="fw-semibold mb-1">Profile picture</h6>
                  <p className="text-muted small mb-2">
                    Shown on your dashboard and navbar. JPEG, PNG, WebP, or GIF up to 10 MB.
                  </p>
                  <div className="d-flex flex-wrap gap-2">
                    <label className="btn btn-outline-primary btn-sm mb-0">
                      <FiCamera size={14} className="me-1" />
                      {avatarMutation.isPending ? 'Uploading…' : 'Upload photo'}
                      <input
                        type="file"
                        accept="image/jpeg,image/png,image/webp,image/gif"
                        className="d-none"
                        disabled={avatarMutation.isPending || removeAvatarMutation.isPending}
                        onChange={(event) => {
                          const file = event.target.files?.[0];
                          event.target.value = '';
                          if (!file) return;
                          const reader = new FileReader();
                          reader.onload = () => setAvatarPreview(reader.result);
                          reader.readAsDataURL(file);
                          avatarMutation.mutate(file);
                        }}
                      />
                    </label>
                    {(profile?.has_avatar || user?.has_avatar) && (
                      <button
                        type="button"
                        className="btn btn-outline-danger btn-sm d-inline-flex align-items-center gap-1"
                        disabled={avatarMutation.isPending || removeAvatarMutation.isPending}
                        onClick={() => removeAvatarMutation.mutate()}
                      >
                        <FiTrash2 size={14} />
                        {removeAvatarMutation.isPending ? 'Removing…' : 'Remove'}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
            <WorkspaceFieldGrid>
              {(staffProfile || parentProfile) ? (
                <>
                  <ReadOnlyField label="First name" value={profile?.first_name} hint="Managed by your school admin." />
                  <ReadOnlyField label="Last name" value={profile?.last_name} hint="Managed by your school admin." />
                </>
              ) : (
                <>
                  <div className="col-md-6">
                    <label className="form-label small fw-medium">First name</label>
                    <input className="form-control" {...register('first_name')} />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label small fw-medium">Last name</label>
                    <input className="form-control" {...register('last_name')} />
                  </div>
                </>
              )}
              <ReadOnlyField label="Work email" value={profile?.email} hint="Contact your school admin to change your login email." />
              <div className="col-md-6">
                <label className="form-label small fw-medium">Phone</label>
                <input className="form-control" {...register('phone')} />
              </div>
              <ReadOnlyField label="Role" value={getRoleLabel(profile?.effective_role || profile?.role)} />
              {staffProfile && (
                <div className="col-md-6">
                  <label className="form-label small fw-medium">Middle name</label>
                  <input className="form-control" {...register('staff_profile.middle_name')} />
                </div>
              )}
            </WorkspaceFieldGrid>
          </WorkspaceSection>
        )}

        {activeTab === 'employment' && staffProfile && (
          <WorkspaceSection
            title="Employment record"
            description="Managed by school administration — read only for staff members."
            icon={FiShield}
          >
            <WorkspaceFieldGrid>
              <ReadOnlyField label="Employee ID" value={staffProfile.employee_id} />
              <ReadOnlyField label="Designation" value={staffProfile.designation} />
              <ReadOnlyField label="Dashboard role" value={getRoleLabel(staffProfile.portal_role)} />
              <ReadOnlyField label="Category" value={staffProfile.staff_category} />
              <ReadOnlyField label="Employment type" value={staffProfile.employment_type?.replace('_', ' ')} />
              <ReadOnlyField label="Status" value={staffProfile.status} />
              <ReadOnlyField label="Date joined" value={staffProfile.date_joined} />
              <ReadOnlyField label="National ID" value={staffProfile.national_id} hint="Admin-only field" />
              <ReadOnlyField label="Qualifications" value={staffProfile.qualification_summary} />
            </WorkspaceFieldGrid>
            {isSchoolAdmin && (
              <div className="mt-3">
                <a href="/school-admin/hr/staffs" className="btn btn-outline-primary btn-sm">
                  Manage staff records (admin)
                </a>
              </div>
            )}
          </WorkspaceSection>
        )}

        {activeTab === 'contact' && (
          <WorkspaceSection title="Contact & emergency" description="Keep your reachability and emergency details current." icon={FiPhone}>
            <WorkspaceFieldGrid>
              {staffProfile && (
                <>
                  <div className="col-md-6">
                    <label className="form-label small fw-medium">Personal email</label>
                    <input type="email" className="form-control" {...register('staff_profile.personal_email', emailValidationRules({ required: false, label: 'Personal email' }))} />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label small fw-medium">Alternate phone</label>
                    <input className="form-control" {...register('staff_profile.alternate_phone')} />
                  </div>
                  <div className="col-12">
                    <label className="form-label small fw-medium">Address</label>
                    <textarea className="form-control" rows={2} {...register('staff_profile.address')} />
                  </div>
                  <div className="col-md-4">
                    <label className="form-label small fw-medium">Emergency contact</label>
                    <input className="form-control" {...register('staff_profile.emergency_contact')} />
                  </div>
                  <div className="col-md-4">
                    <label className="form-label small fw-medium">Emergency phone</label>
                    <input className="form-control" {...register('staff_profile.emergency_phone')} />
                  </div>
                  <div className="col-md-4">
                    <label className="form-label small fw-medium">Relationship</label>
                    <input className="form-control" {...register('staff_profile.emergency_relationship')} />
                  </div>
                </>
              )}
              {parentProfile && (
                <>
                  <div className="col-md-6">
                    <label className="form-label small fw-medium">Phone</label>
                    <input className="form-control" {...register('parent_profile.phone')} />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label small fw-medium">Alternate email</label>
                    <input type="email" className="form-control" {...register('parent_profile.alternate_email', emailValidationRules({ required: false, label: 'Alternate email' }))} />
                  </div>
                  <div className="col-12">
                    <label className="form-label small fw-medium">Address</label>
                    <textarea className="form-control" rows={2} {...register('parent_profile.address')} />
                  </div>
                  <ReadOnlyField label="Primary email" value={parentProfile.email} hint="Admin-managed login email" />
                  <ReadOnlyField label="Relationship to student" value={parentProfile.relationship_to_student} />
                </>
              )}
            </WorkspaceFieldGrid>
          </WorkspaceSection>
        )}
      </form>

      {activeTab === 'security' && (
        <WorkspaceSection title="Password" description="Change your portal login password." icon={FiLock}>
          <form onSubmit={handlePwSubmit((data) => passwordMutation.mutate(data))} className="row g-3" style={{ maxWidth: 480 }}>
            <div className="col-12">
              <label className="form-label small fw-medium">Current password</label>
              <input type="password" className="form-control" {...registerPw('old_password', { required: true })} />
            </div>
            <div className="col-12">
              <label className="form-label small fw-medium">New password</label>
              <input type="password" className="form-control" {...registerPw('new_password', { required: true, minLength: 8 })} />
              {pwErrors.new_password && <div className="text-danger small">Minimum 8 characters</div>}
            </div>
            <div className="col-12">
              <button type="submit" className="btn btn-primary" disabled={passwordMutation.isPending}>
                {passwordMutation.isPending ? 'Updating…' : 'Update password'}
              </button>
            </div>
          </form>
        </WorkspaceSection>
      )}

      {(editable.staff_profile || adminOnly.staff_profile) && activeTab === 'personal' && (
        <p className="text-muted small mt-3 mb-0">
          <FiShield className="me-1" />
          Fields such as role, employee ID, and work email can only be changed by your school admin.
        </p>
      )}
    </WorkspaceShell>
  );
}

export default ProfileWorkspace;