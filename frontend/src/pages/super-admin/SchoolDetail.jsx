import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FiArrowLeft, FiUsers, FiBriefcase, FiBook, FiMapPin, FiMail, FiPhone,
  FiAlertTriangle, FiLayers, FiGlobe, FiCheckCircle, FiXCircle, FiEdit3, FiTrash2,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import SchoolNameWithBadge from '../../components/SchoolNameWithBadge';
import StatCard from '../../components/StatCard';
import StatusBadge from '../../components/StatusBadge';
import ChangeSchoolPlanModal from '../../components/ChangeSchoolPlanModal';
import SchoolDeleteModal from '../../components/SchoolDeleteModal';
import { PageSkeleton } from '../../components/LoadingSkeleton';
import { schoolsService } from '../../services/moduleService';
import { alert, extractApiError, notify } from '../../utils/notify';

const formatDate = (value) => {
  if (!value) return '—';
  return new Date(value).toLocaleDateString();
};

export function SchoolDetail() {
  const { schoolId } = useParams();
  const navigate = useNavigate();
  const [planModalOpen, setPlanModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [planSaving, setPlanSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['school-detail', schoolId],
    queryFn: () => schoolsService.getDetail(schoolId),
    enabled: !!schoolId,
  });

  const { data: deletionPreview, isLoading: previewLoading, refetch: refetchPreview } = useQuery({
    queryKey: ['school-deletion-preview', schoolId],
    queryFn: () => schoolsService.getDeletionPreview(schoolId),
    enabled: false,
  });

  if (isLoading) return <PageSkeleton />;

  if (isError || !data) {
    return (
      <div className="apex-card p-5 text-center">
        <FiAlertTriangle size={32} className="text-warning mb-3" />
        <h5 className="fw-bold">Unable to load school details</h5>
        <button className="btn btn-outline-secondary btn-sm mt-3 me-2" onClick={() => navigate('/super-admin/schools')}>
          Back to Schools
        </button>
        <button className="btn btn-primary btn-sm mt-3" onClick={() => refetch()}>Retry</button>
      </div>
    );
  }

  const school = data.school ?? {};
  const subscription = data.subscription ?? {};
  const stats = data.stats ?? {};

  const handleSuspendToggle = async () => {
    if (school.is_suspended) {
      const result = await alert.confirm({
        title: 'Unsuspend school?',
        text: `${school.name} will regain access to the platform.`,
        confirmText: 'Yes, unsuspend',
        icon: 'info',
      });
      if (!result.isConfirmed) return;
      try {
        await schoolsService.unsuspend(school.id);
        notify.success(`${school.name} has been unsuspended.`);
        refetch();
      } catch (err) {
        notify.error(extractApiError(err, 'Unable to unsuspend school.'));
      }
      return;
    }
    const result = await alert.confirm({
      title: 'Suspend school?',
      text: `${school.name} will lose access until unsuspended.`,
      confirmText: 'Yes, suspend',
      danger: true,
      icon: 'warning',
    });
    if (!result.isConfirmed) return;
    try {
      await schoolsService.suspend(school.id, 'Suspended by super admin');
      notify.warning(`${school.name} has been suspended.`);
      refetch();
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to suspend school.'));
    }
  };

  const handleApprove = async () => {
    const result = await alert.confirm({
      title: 'Approve school?',
      text: `${school.name} will be activated and the school admin can access their dashboard.`,
      confirmText: 'Approve',
      icon: 'question',
    });
    if (!result.isConfirmed) return;
    try {
      await schoolsService.verify(school.id);
      notify.success(`${school.name} approved and activated.`);
      refetch();
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to approve school.'));
    }
  };

  const handleChangePlan = async (payload) => {
    setPlanSaving(true);
    try {
      const result = await schoolsService.changePlan(school.id, payload);
      const modules = result?.module_count ?? result?.data?.module_count;
      notify.success(
        modules != null
          ? `Plan updated for ${school.name}. ${modules} modules are now active in the database.`
          : `Plan updated for ${school.name}. School admin can sign in to see modules.`,
      );
      setPlanModalOpen(false);
      refetch();
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to change plan.'));
    } finally {
      setPlanSaving(false);
    }
  };

  const openDeleteFlow = async () => {
    setDeleteModalOpen(true);
    refetchPreview();
  };

  const handlePermanentDelete = async (payload) => {
    setDeleting(true);
    try {
      await schoolsService.permanentDelete(school.id, payload);
      notify.success(`"${school.name}" has been permanently removed.`);
      setDeleteModalOpen(false);
      navigate('/super-admin/schools');
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to delete school.'));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div>
      <div className="d-flex align-items-center gap-2 mb-3">
        <button
          className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1"
          onClick={() => navigate('/super-admin/schools')}
        >
          <FiArrowLeft size={14} /> Back to Schools
        </button>
      </div>

      <PageHeader
        title={(
          <SchoolNameWithBadge
            name={school.name}
            planSlug={subscription.plan_slug}
            size="lg"
            className="fw-bold"
          />
        )}
        subtitle={`${school.city ? `${school.city}, ` : ''}${school.country || ''}`}
        actions={
          <div className="d-flex align-items-center gap-2 flex-wrap">
            <StatusBadge status={school.is_suspended ? 'suspended' : school.status} />
            {!school.is_verified && (
              <button type="button" className="btn btn-sm btn-success" onClick={handleApprove}>
                Approve School
              </button>
            )}
            <button
              type="button"
              className="btn btn-sm btn-outline-primary d-flex align-items-center gap-1"
              onClick={() => setPlanModalOpen(true)}
            >
              <FiEdit3 size={14} /> Change Plan
            </button>
            <button
              className={`btn btn-sm ${school.is_suspended ? 'btn-outline-success' : 'btn-outline-warning'}`}
              onClick={handleSuspendToggle}
            >
              {school.is_suspended ? 'Unsuspend' : 'Suspend'}
            </button>
          </div>
        }
      />

      <div className="row g-3 mb-4">
        <div className="col-lg-8">
          <motion.div className="apex-card p-4 h-100" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <h5 className="fw-bold mb-3">School Information</h5>
            <div className="row g-3">
              <div className="col-md-6">
                <div className="small text-muted">School Code</div>
                <div className="fw-semibold">{school.code || '—'}</div>
              </div>
              <div className="col-md-6">
                <div className="small text-muted">Joined</div>
                <div className="fw-semibold">{formatDate(school.created_at)}</div>
              </div>
              <div className="col-md-6 d-flex align-items-start gap-2">
                <FiMail className="text-muted mt-1" />
                <div>
                  <div className="small text-muted">Email</div>
                  <div className="fw-semibold">{school.email || '—'}</div>
                </div>
              </div>
              <div className="col-md-6 d-flex align-items-start gap-2">
                <FiPhone className="text-muted mt-1" />
                <div>
                  <div className="small text-muted">Phone</div>
                  <div className="fw-semibold">{school.phone || '—'}</div>
                </div>
              </div>
              <div className="col-md-6 d-flex align-items-start gap-2">
                <FiMapPin className="text-muted mt-1" />
                <div>
                  <div className="small text-muted">Address</div>
                  <div className="fw-semibold">{school.address || '—'}</div>
                </div>
              </div>
              <div className="col-md-6 d-flex align-items-start gap-2">
                <FiGlobe className="text-muted mt-1" />
                <div>
                  <div className="small text-muted">Admin Email</div>
                  <div className="fw-semibold">{school.admin_email || '—'}</div>
                </div>
              </div>
              {school.tagline && (
                <div className="col-12">
                  <div className="small text-muted">Tagline</div>
                  <div className="fst-italic">{school.tagline}</div>
                </div>
              )}
            </div>
          </motion.div>
        </div>

        <div className="col-lg-4">
          <motion.div className="apex-card p-4 h-100" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
            <div className="d-flex align-items-center justify-content-between mb-3">
              <div className="d-flex align-items-center gap-2">
                <FiLayers style={{ color: 'var(--apex-primary)' }} />
                <h5 className="fw-bold mb-0">Subscription</h5>
              </div>
              <button
                type="button"
                className="btn btn-sm btn-outline-primary"
                onClick={() => setPlanModalOpen(true)}
              >
                Change
              </button>
            </div>
            <div className="d-flex flex-column gap-3">
              <div className="d-flex justify-content-between">
                <span className="text-muted small">Plan</span>
                <span className="fw-semibold">{subscription.plan || '—'}</span>
              </div>
              <div className="d-flex justify-content-between">
                <span className="text-muted small">Status</span>
                <StatusBadge status={subscription.status || 'none'} />
              </div>
              <div className="d-flex justify-content-between">
                <span className="text-muted small">Billing</span>
                <span className="fw-semibold text-capitalize">{subscription.billing_cycle || '—'}</span>
              </div>
              <div className="d-flex justify-content-between">
                <span className="text-muted small">Features</span>
                <span className="fw-semibold">{subscription.feature_count ?? school.enabled_feature_count ?? 0}</span>
              </div>
              <div className="d-flex justify-content-between">
                <span className="text-muted small">Monthly Amount</span>
                <span className="fw-semibold">${Number(subscription.monthly_amount || 0).toFixed(2)}</span>
              </div>
              <div className="d-flex justify-content-between">
                <span className="text-muted small">Renewal / Trial End</span>
                <span className="fw-semibold">{formatDate(subscription.current_period_end || subscription.trial_ends_at)}</span>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-sm-6 col-xl-4">
          <StatCard title="Students" value={stats.total_students ?? 0} icon={FiUsers} color="primary" />
        </div>
        <div className="col-sm-6 col-xl-4">
          <StatCard title="Staff" value={stats.total_staff ?? 0} icon={FiBriefcase} color="secondary" />
        </div>
        <div className="col-sm-6 col-xl-4">
          <StatCard title="Classes" value={stats.active_classes ?? 0} icon={FiBook} color="accent" />
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-lg-6">
          <motion.div className="apex-card p-4 h-100" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h5 className="fw-bold mb-3">Account Status</h5>
            <div className="d-flex flex-column gap-3">
              <div className="d-flex justify-content-between align-items-center">
                <span className="text-muted small">Verification</span>
                <span className="d-flex align-items-center gap-1 small fw-semibold">
                  {school.is_verified ? (
                    <>
                      <FiCheckCircle className="text-success" />
                      Verified
                    </>
                  ) : (
                    <>
                      <FiXCircle className="text-warning" />
                      Not verified
                    </>
                  )}
                </span>
              </div>
              <div className="d-flex justify-content-between align-items-center">
                <span className="text-muted small">School Status</span>
                <StatusBadge status={school.status} />
              </div>
              <div className="d-flex justify-content-between align-items-center">
                <span className="text-muted small">Registration Type</span>
                <span className="fw-semibold text-capitalize">
                  {(school.registration_type || 'pending').replace(/_/g, ' ')}
                </span>
              </div>
              <div className="d-flex justify-content-between align-items-center">
                <span className="text-muted small">Enabled Features</span>
                <span className="fw-semibold">{school.enabled_feature_count ?? subscription.feature_count ?? 0}</span>
              </div>
            </div>
          </motion.div>
        </div>

        <div className="col-lg-6">
          <motion.div className="apex-card p-4 h-100" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <h5 className="fw-bold mb-3">Capacity</h5>
            <p className="text-muted small mb-2">
              User limits are not enforced — schools may add unlimited students, staff, and parents.
            </p>
            <div className="d-flex flex-column gap-2">
              <div className="d-flex justify-content-between small">
                <span className="text-muted">Students enrolled</span>
                <span className="fw-semibold">{stats.total_students ?? 0} · Unlimited</span>
              </div>
              <div className="d-flex justify-content-between small">
                <span className="text-muted">Staff members</span>
                <span className="fw-semibold">{stats.total_staff ?? 0} · Unlimited</span>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      <motion.div
        className="apex-card p-4 border border-danger border-opacity-25"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <div className="d-flex flex-wrap align-items-start justify-content-between gap-3">
          <div>
            <h5 className="fw-bold text-danger mb-1 d-flex align-items-center gap-2">
              <FiTrash2 /> Danger Zone
            </h5>
            <p className="text-muted small mb-0">
              Permanently delete this school and all associated users, records, subscriptions, and files.
              This requires a three-step confirmation process.
            </p>
          </div>
          <button type="button" className="btn btn-outline-danger btn-sm" onClick={openDeleteFlow}>
            Delete School…
          </button>
        </div>
      </motion.div>

      <ChangeSchoolPlanModal
        show={planModalOpen}
        onHide={() => setPlanModalOpen(false)}
        school={school}
        subscription={subscription}
        onSave={handleChangePlan}
        saving={planSaving}
      />

      <SchoolDeleteModal
        show={deleteModalOpen}
        onHide={() => !deleting && setDeleteModalOpen(false)}
        school={school}
        preview={deletionPreview}
        previewLoading={previewLoading}
        onConfirmDelete={handlePermanentDelete}
        deleting={deleting}
      />
    </div>
  );
}

export default SchoolDetail;