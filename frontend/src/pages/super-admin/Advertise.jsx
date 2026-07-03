import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FiBell, FiCheck, FiEdit2, FiLayers, FiPause, FiPlay, FiPlus, FiStopCircle, FiTrash2, FiX,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import PlanAdvertisementPreview from '../../components/PlanAdvertisementPreview';
import { PageSkeleton } from '../../components/LoadingSkeleton';
import { planAdvertisementService } from '../../services/moduleService';
import { extractApiError, notify } from '../../utils/notify';

const EMPTY_FORM = {
  target_plan_slug: '',
  suggested_plan_slug: '',
  title: '',
  headline: '',
  message: '',
  highlights: [],
  cta_label: 'Explore upgrade',
  cta_url: '/school-admin/notifications',
  status: 'draft',
  starts_at: '',
  ends_at: '',
};

const formatDateTimeLocal = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

function AdvertiseEditor({
  open,
  form,
  planOptions,
  highlightInput,
  onHighlightInputChange,
  onChange,
  onAddHighlight,
  onRemoveHighlight,
  onClose,
  onSave,
  saving,
}) {
  const selectedPlan = planOptions.find((p) => p.slug === form.target_plan_slug);
  const upgradeOptions = selectedPlan?.upgrade_options || [];

  const previewItem = {
    title: form.title || 'Upgrade title',
    message: form.message || 'Advertisement message preview.',
    metadata: {
      headline: form.headline,
      highlights: form.highlights,
      cta_label: form.cta_label,
      target_plan_name: selectedPlan?.name,
      suggested_plan_slug: form.suggested_plan_slug,
      suggested_plan_name: upgradeOptions.find((o) => o.slug === form.suggested_plan_slug)?.name,
    },
  };

  if (!open) return null;

  return (
    <div className="plan-ad-editor-overlay" onClick={onClose} role="presentation">
      <motion.div
        className="plan-ad-editor"
        initial={{ opacity: 0, y: 16, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 10, scale: 0.98 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="plan-ad-editor-header">
          <div>
            <h5 className="fw-bold mb-1">{form.id ? 'Edit Advertisement' : 'Create Advertisement'}</h5>
            <p className="text-muted small mb-0">Craft a plan upgrade message and broadcast it to matching schools.</p>
          </div>
          <button type="button" className="btn btn-link text-muted p-0" onClick={onClose} aria-label="Close">
            <FiX size={20} />
          </button>
        </div>

        <div className="plan-ad-editor-body">
          <div className="row g-4">
            <div className="col-lg-7">
              <div className="row g-3">
                <div className="col-md-6">
                  <label className="form-label small fw-semibold">Target plan</label>
                  <select
                    className="form-select"
                    value={form.target_plan_slug}
                    onChange={(e) => onChange('target_plan_slug', e.target.value)}
                    disabled={Boolean(form.id)}
                  >
                    <option value="">Select plan</option>
                    {planOptions.filter((p) => p.can_advertise).map((plan) => (
                      <option key={plan.slug} value={plan.slug}>{plan.name}</option>
                    ))}
                  </select>
                </div>
                <div className="col-md-6">
                  <label className="form-label small fw-semibold">Suggested upgrade</label>
                  <select
                    className="form-select"
                    value={form.suggested_plan_slug}
                    onChange={(e) => onChange('suggested_plan_slug', e.target.value)}
                  >
                    <option value="">Select upgrade plan</option>
                    {upgradeOptions.map((plan) => (
                      <option key={plan.slug} value={plan.slug}>{plan.name}</option>
                    ))}
                  </select>
                </div>
                <div className="col-12">
                  <label className="form-label small fw-semibold">Title</label>
                  <input
                    className="form-control"
                    value={form.title}
                    onChange={(e) => onChange('title', e.target.value)}
                    placeholder="Upgrade to Premium"
                  />
                </div>
                <div className="col-12">
                  <label className="form-label small fw-semibold">Headline</label>
                  <input
                    className="form-control"
                    value={form.headline}
                    onChange={(e) => onChange('headline', e.target.value)}
                    placeholder="Unlock more with Premium"
                  />
                </div>
                <div className="col-12">
                  <label className="form-label small fw-semibold">Message</label>
                  <textarea
                    className="form-control"
                    rows={4}
                    value={form.message}
                    onChange={(e) => onChange('message', e.target.value)}
                  />
                </div>
                <div className="col-12">
                  <label className="form-label small fw-semibold">Highlights</label>
                  <div className="d-flex gap-2 mb-2">
                    <input
                      className="form-control"
                      value={highlightInput}
                      onChange={(e) => onHighlightInputChange(e.target.value)}
                      placeholder="Add a benefit bullet"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          onAddHighlight();
                        }
                      }}
                    />
                    <button type="button" className="btn btn-outline-primary" onClick={onAddHighlight}>
                      Add
                    </button>
                  </div>
                  <div className="d-flex flex-wrap gap-2">
                    {form.highlights.map((item) => (
                      <span key={item} className="plan-ad-highlight-chip">
                        {item}
                        <button type="button" onClick={() => onRemoveHighlight(item)} aria-label={`Remove ${item}`}>
                          <FiX size={12} />
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
                <div className="col-md-6">
                  <label className="form-label small fw-semibold">CTA label</label>
                  <input
                    className="form-control"
                    value={form.cta_label}
                    onChange={(e) => onChange('cta_label', e.target.value)}
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label small fw-semibold">CTA URL</label>
                  <input
                    className="form-control"
                    value={form.cta_url}
                    onChange={(e) => onChange('cta_url', e.target.value)}
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label small fw-semibold">Starts at</label>
                  <input
                    type="datetime-local"
                    className="form-control"
                    value={form.starts_at}
                    onChange={(e) => onChange('starts_at', e.target.value)}
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label small fw-semibold">Ends at</label>
                  <input
                    type="datetime-local"
                    className="form-control"
                    value={form.ends_at}
                    onChange={(e) => onChange('ends_at', e.target.value)}
                  />
                </div>
              </div>
            </div>

            <div className="col-lg-5">
              <div className="plan-ad-editor-preview-wrap">
                <div className="small fw-semibold text-muted mb-2">School admin preview</div>
                <PlanAdvertisementPreview item={previewItem} />
              </div>
            </div>
          </div>
        </div>

        <div className="plan-ad-editor-footer">
          <button type="button" className="btn btn-light" onClick={onClose}>Cancel</button>
          <button type="button" className="btn btn-primary" onClick={onSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save draft'}
          </button>
        </div>
      </motion.div>
    </div>
  );
}

export function Advertise() {
  const queryClient = useQueryClient();
  const [activePlan, setActivePlan] = useState('');
  const [editorOpen, setEditorOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [highlightInput, setHighlightInput] = useState('');

  const { data: planOptions = [], isLoading: plansLoading } = useQuery({
    queryKey: ['plan-ad-options'],
    queryFn: () => planAdvertisementService.getPlanOptions(),
  });

  const advertisePlans = useMemo(
    () => planOptions.filter((plan) => plan.can_advertise),
    [planOptions],
  );

  useEffect(() => {
    if (!activePlan && advertisePlans.length > 0) {
      setActivePlan(advertisePlans[0].slug);
    }
  }, [activePlan, advertisePlans]);

  const { data: ads = [], isLoading } = useQuery({
    queryKey: ['plan-advertisements', activePlan],
    queryFn: () => planAdvertisementService.list({
      target_plan_slug: activePlan || undefined,
      ordering: '-updated_at',
      page_size: 50,
    }),
    enabled: !!activePlan,
  });

  const saveMutation = useMutation({
    mutationFn: async (payload) => {
      const body = {
        ...payload,
        starts_at: payload.starts_at ? new Date(payload.starts_at).toISOString() : null,
        ends_at: payload.ends_at ? new Date(payload.ends_at).toISOString() : null,
      };
      if (payload.id) return planAdvertisementService.update(payload.id, body);
      return planAdvertisementService.create(body);
    },
    onSuccess: () => {
      notify.success('Advertisement saved.');
      queryClient.invalidateQueries({ queryKey: ['plan-advertisements'] });
      setEditorOpen(false);
      setForm(EMPTY_FORM);
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to save advertisement.')),
  });

  const broadcastMutation = useMutation({
    mutationFn: (id) => planAdvertisementService.broadcast(id),
    onSuccess: (data) => {
      notify.success(data?.message || 'Advertisement broadcast.');
      queryClient.invalidateQueries({ queryKey: ['plan-advertisements'] });
      queryClient.invalidateQueries({ queryKey: ['notification-feed'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to broadcast advertisement.')),
  });

  const pauseMutation = useMutation({
    mutationFn: (id) => planAdvertisementService.pause(id),
    onSuccess: () => {
      notify.success('Advertisement paused.');
      queryClient.invalidateQueries({ queryKey: ['plan-advertisements'] });
      queryClient.invalidateQueries({ queryKey: ['notification-feed'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to pause advertisement.')),
  });

  const endMutation = useMutation({
    mutationFn: (id) => planAdvertisementService.end(id),
    onSuccess: () => {
      notify.success('Advertisement ended.');
      queryClient.invalidateQueries({ queryKey: ['plan-advertisements'] });
      queryClient.invalidateQueries({ queryKey: ['notification-feed'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to end advertisement.')),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => planAdvertisementService.delete(id),
    onSuccess: () => {
      notify.success('Advertisement deleted.');
      queryClient.invalidateQueries({ queryKey: ['plan-advertisements'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to delete advertisement.')),
  });

  const loadDefaults = async (targetSlug, suggestedSlug) => {
    const defaults = await planAdvertisementService.getDefaults({
      target_plan_slug: targetSlug,
      suggested_plan_slug: suggestedSlug,
    });
    setForm((prev) => ({
      ...prev,
      ...defaults,
      starts_at: '',
      ends_at: '',
    }));
  };

  const openCreate = async () => {
    const target = activePlan || advertisePlans[0]?.slug;
    if (!target) return;
    const suggested = advertisePlans.find((p) => p.slug === target)?.upgrade_options?.[0]?.slug;
    await loadDefaults(target, suggested);
    setForm((prev) => ({ ...prev, target_plan_slug: target, suggested_plan_slug: suggested || '' }));
    setEditorOpen(true);
  };

  const openEdit = (ad) => {
    setForm({
      id: ad.id,
      target_plan_slug: ad.target_plan_slug,
      suggested_plan_slug: ad.suggested_plan_slug,
      title: ad.title,
      headline: ad.headline || '',
      message: ad.message,
      highlights: ad.highlights || [],
      cta_label: ad.cta_label || 'Explore upgrade',
      cta_url: ad.cta_url || '/school-admin/notifications',
      status: ad.status,
      starts_at: formatDateTimeLocal(ad.starts_at),
      ends_at: formatDateTimeLocal(ad.ends_at),
    });
    setEditorOpen(true);
  };

  const handleFormChange = async (field, value) => {
    setForm((prev) => {
      const next = { ...prev, [field]: value };
      return next;
    });
    if (field === 'target_plan_slug') {
      const plan = advertisePlans.find((p) => p.slug === value);
      const suggested = plan?.upgrade_options?.[0]?.slug;
      if (suggested) await loadDefaults(value, suggested);
    }
    if (field === 'suggested_plan_slug' && form.target_plan_slug) {
      await loadDefaults(form.target_plan_slug, value);
    }
  };

  const handleSave = () => {
    if (!form.target_plan_slug || !form.suggested_plan_slug || !form.title || !form.message) {
      notify.warning('Target plan, suggested plan, title, and message are required.');
      return;
    }
    saveMutation.mutate(form);
  };

  if (plansLoading || isLoading) return <PageSkeleton />;

  const activeAd = ads.find((ad) => ad.status === 'active');

  return (
    <div className="plan-ad-page">
      <PageHeader
        title="Advertise"
        subtitle="Broadcast plan upgrade promotions to school admins based on their current subscription"
        actions={(
          <div className="d-flex gap-2">
            <Link to="/super-admin/notifications" className="btn btn-outline-secondary btn-sm">
              <FiBell size={14} className="me-1" /> Inbox
            </Link>
            <button type="button" className="btn btn-primary btn-sm" onClick={openCreate}>
              <FiPlus size={14} className="me-1" /> New advertisement
            </button>
          </div>
        )}
      />

      <div className="plan-ad-plan-tabs mb-4">
        {advertisePlans.map((plan) => (
          <button
            key={plan.slug}
            type="button"
            className={`plan-ad-plan-tab ${activePlan === plan.slug ? 'is-active' : ''}`}
            onClick={() => setActivePlan(plan.slug)}
          >
            <FiLayers size={15} />
            <span>{plan.name}</span>
            <span className="plan-ad-plan-tab-sub">→ {plan.upgrade_options[0]?.name}</span>
          </button>
        ))}
      </div>

      {activeAd && (
        <motion.div className="apex-card plan-ad-active-banner mb-4" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
            <div>
              <div className="small text-muted mb-1">Currently live for {activeAd.target_plan_name}</div>
              <div className="fw-bold">{activeAd.title}</div>
              <div className="small text-muted">
                Broadcasting upgrade to {activeAd.suggested_plan_name}
                {activeAd.broadcast_count > 0 && ` · ${activeAd.broadcast_count} school admin(s) notified`}
              </div>
            </div>
            <StatusBadge status={activeAd.status} />
          </div>
        </motion.div>
      )}

      <div className="row g-3">
        {ads.length === 0 ? (
          <div className="col-12">
            <div className="apex-card p-5 text-center text-muted">
              <FiLayers size={36} className="mb-3 opacity-50" />
              <h5 className="fw-bold text-body">No advertisements for this plan yet</h5>
              <p className="mb-3">Create a promotion that suggests the next best plan for schools on {advertisePlans.find((p) => p.slug === activePlan)?.name}.</p>
              <button type="button" className="btn btn-primary btn-sm" onClick={openCreate}>
                <FiPlus size={14} className="me-1" /> Create advertisement
              </button>
            </div>
          </div>
        ) : (
          ads.map((ad, index) => {
            const previewItem = {
              title: ad.title,
              message: ad.message,
              metadata: {
                headline: ad.headline,
                highlights: ad.highlights,
                cta_label: ad.cta_label,
                target_plan_name: ad.target_plan_name,
                suggested_plan_slug: ad.suggested_plan_slug,
                suggested_plan_name: ad.suggested_plan_name,
              },
            };

            return (
              <div className="col-lg-6" key={ad.id}>
                <motion.div
                  className="apex-card plan-ad-card h-100"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.04 }}
                >
                  <div className="d-flex justify-content-between align-items-start gap-2 mb-3">
                    <div>
                      <div className="small text-muted mb-1">
                        {ad.target_plan_name} → {ad.suggested_plan_name}
                      </div>
                      <StatusBadge status={ad.status} />
                    </div>
                    <div className="d-flex gap-1">
                      <button type="button" className="btn btn-sm btn-light" onClick={() => openEdit(ad)} title="Edit">
                        <FiEdit2 size={14} />
                      </button>
                      {ad.status !== 'active' ? (
                        <button
                          type="button"
                          className="btn btn-sm btn-primary"
                          onClick={() => broadcastMutation.mutate(ad.id)}
                          disabled={broadcastMutation.isPending}
                          title="Broadcast"
                        >
                          <FiPlay size={14} />
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="btn btn-sm btn-warning"
                          onClick={() => pauseMutation.mutate(ad.id)}
                          disabled={pauseMutation.isPending}
                          title="Pause"
                        >
                          <FiPause size={14} />
                        </button>
                      )}
                      {ad.status === 'active' && (
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-danger"
                          onClick={() => endMutation.mutate(ad.id)}
                          disabled={endMutation.isPending}
                          title="End"
                        >
                          <FiStopCircle size={14} />
                        </button>
                      )}
                      {ad.status === 'draft' && (
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-danger"
                          onClick={() => deleteMutation.mutate(ad.id)}
                          disabled={deleteMutation.isPending}
                          title="Delete"
                        >
                          <FiTrash2 size={14} />
                        </button>
                      )}
                    </div>
                  </div>

                  <PlanAdvertisementPreview item={previewItem} compact />

                  <div className="plan-ad-card-meta small text-muted mt-3">
                    {ad.broadcast_at
                      ? <>Last broadcast {new Date(ad.broadcast_at).toLocaleString()} · {ad.broadcast_count} notified</>
                      : 'Not broadcast yet'}
                  </div>
                </motion.div>
              </div>
            );
          })
        )}
      </div>

      <AnimatePresence>
        {editorOpen && (
          <AdvertiseEditor
            open={editorOpen}
            form={form}
            planOptions={planOptions}
            highlightInput={highlightInput}
            onHighlightInputChange={setHighlightInput}
            onChange={handleFormChange}
            onAddHighlight={() => {
              const value = highlightInput.trim();
              if (!value) return;
              setForm((prev) => ({ ...prev, highlights: [...new Set([...prev.highlights, value])] }));
              setHighlightInput('');
            }}
            onRemoveHighlight={(value) => {
              setForm((prev) => ({ ...prev, highlights: prev.highlights.filter((item) => item !== value) }));
            }}
            onClose={() => setEditorOpen(false)}
            onSave={handleSave}
            saving={saveMutation.isPending}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

export default Advertise;