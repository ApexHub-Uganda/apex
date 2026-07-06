import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FiCalendar, FiCopy, FiEdit2, FiMail, FiMessageCircle, FiPhone,
  FiPlay, FiPlus, FiSend, FiStopCircle, FiTrash2, FiUsers, FiX,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import { PageSkeleton } from '../../components/LoadingSkeleton';
import { broadcastService } from '../../services/moduleService';
import { alert, extractApiError, notify } from '../../utils/notify';

const CHANNEL_OPTIONS = [
  { value: 'email', label: 'Email', icon: FiMail },
  { value: 'sms', label: 'SMS', icon: FiPhone },
  { value: 'whatsapp', label: 'WhatsApp', icon: FiMessageCircle },
];

const AUDIENCE_OPTIONS = [
  { value: 'all', label: 'All Schools' },
  { value: 'trial', label: 'Trial Plans' },
  { value: 'basic', label: 'Basic Plans' },
  { value: 'premium', label: 'Premium Plans' },
  { value: 'premium_plus', label: 'Premium Plus Plans' },
  { value: 'active', label: 'Active Schools Only' },
];

const SEVERITY_OPTIONS = [
  { value: 'info', label: 'Info' },
  { value: 'warning', label: 'Warning' },
  { value: 'critical', label: 'Critical' },
];

const EMPTY_FORM = {
  title: '',
  message: '',
  channels: ['email'],
  audience: 'all',
  severity: 'info',
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

const toIsoOrNull = (value) => (value ? new Date(value).toISOString() : null);

const STATUS_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'draft', label: 'Drafts' },
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'sent', label: 'Sent' },
  { value: 'cancelled', label: 'Cancelled' },
];

const SEVERITY_CLASS = {
  info: 'broadcast-severity--info',
  warning: 'broadcast-severity--warning',
  critical: 'broadcast-severity--critical',
};

const CHANNEL_ICON = {
  email: FiMail,
  sms: FiPhone,
  whatsapp: FiMessageCircle,
};

function ChannelPill({ channel, label }) {
  const Icon = CHANNEL_ICON[channel] || FiSend;
  return (
    <span className={`broadcast-channel-pill broadcast-channel-pill--${channel}`}>
      <Icon size={12} />
      <span>{label || channel}</span>
    </span>
  );
}

function ChannelStatusBar({ status }) {
  if (!status?.channels) return null;
  const items = CHANNEL_OPTIONS.map(({ value, label }) => {
    const channel = status.channels[value] || {};
    const state = !channel.configured
      ? 'unconfigured'
      : channel.ready && status.live_dispatch
        ? 'live'
        : channel.deployment_ready
          ? 'ready'
          : 'incomplete';
    return { value, label, state, provider: channel.provider };
  });

  return (
    <div className="broadcast-gateway-bar mb-4">
      {items.map((item) => (
        <div key={item.value} className={`broadcast-gateway-item broadcast-gateway-item--${item.state}`}>
          <div className="broadcast-gateway-item__label">{item.label}</div>
          <div className="broadcast-gateway-item__state">
            {item.state === 'live' && 'Live'}
            {item.state === 'ready' && 'Ready — awaiting live dispatch'}
            {item.state === 'incomplete' && 'Incomplete config'}
            {item.state === 'unconfigured' && 'Not configured'}
          </div>
          {item.provider && <div className="broadcast-gateway-item__provider">{item.provider}</div>}
        </div>
      ))}
      <div className="broadcast-gateway-note small text-muted">
        Channel deliveries may show as failed until <code>INTEGRATION_LIVE_DISPATCH=true</code> at deployment.
      </div>
    </div>
  );
}

function BroadcastCard({
  item,
  index,
  onEdit,
  onView,
  onSend,
  onSchedule,
  onDelete,
  onCancel,
  onDuplicate,
  onDeliveries,
  pending,
}) {
  const channels = item.channels || [];
  const channelLabels = item.channels_display || channels;
  const severityClass = SEVERITY_CLASS[item.severity] || SEVERITY_CLASS.info;

  const footerText = item.status === 'sent' && item.sent_at
    ? (
      <>
        <span>Sent {new Date(item.sent_at).toLocaleString()}</span>
        <span className="broadcast-card__stat"><strong>{item.recipient_count}</strong> recipients</span>
        <span className="broadcast-card__stat broadcast-card__stat--success"><strong>{item.delivered_count}</strong> delivered</span>
        {item.failed_count > 0 && (
          <span className="broadcast-card__stat broadcast-card__stat--danger"><strong>{item.failed_count}</strong> failed</span>
        )}
        {item.skipped_count > 0 && (
          <span className="broadcast-card__stat"><strong>{item.skipped_count}</strong> skipped</span>
        )}
      </>
    )
    : item.status === 'scheduled' && item.starts_at
      ? <span>Scheduled for {new Date(item.starts_at).toLocaleString()}</span>
      : <span>Draft — not sent yet</span>;

  return (
    <motion.article
      className={`broadcast-card broadcast-card--${item.status}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
    >
      <header className="broadcast-card__header">
        <div className="broadcast-card__title-block">
          <h3 className="broadcast-card__title">{item.title}</h3>
          <div className="broadcast-card__badges">
            <StatusBadge status={item.status} />
            <span className={`broadcast-severity-pill ${severityClass}`}>{item.severity}</span>
          </div>
        </div>
        <div className="broadcast-card__toolbar">
          {item.status === 'draft' && (
            <>
              <button type="button" className="broadcast-card__action" onClick={() => onEdit(item)} title="Edit"><FiEdit2 size={15} /></button>
              <button type="button" className="broadcast-card__action" onClick={() => onSchedule(item)} disabled={pending.schedule} title="Schedule"><FiCalendar size={15} /></button>
              <button type="button" className="broadcast-card__action broadcast-card__action--primary" onClick={() => onSend(item)} disabled={pending.send} title="Send now"><FiPlay size={15} /></button>
            </>
          )}
          {item.status === 'scheduled' && (
            <>
              <button type="button" className="broadcast-card__action" onClick={() => onEdit(item)} title="Edit"><FiEdit2 size={15} /></button>
              <button type="button" className="broadcast-card__action broadcast-card__action--primary" onClick={() => onSend(item)} disabled={pending.send} title="Send now"><FiPlay size={15} /></button>
              <button type="button" className="broadcast-card__action broadcast-card__action--danger" onClick={() => onCancel(item)} disabled={pending.cancel} title="Cancel schedule"><FiStopCircle size={15} /></button>
            </>
          )}
          {item.status === 'sent' && (
            <>
              <button type="button" className="broadcast-card__action" onClick={() => onView(item)} title="View"><FiEdit2 size={15} /></button>
              <button type="button" className="broadcast-card__action" onClick={() => onDeliveries(item)} title="Deliveries"><FiUsers size={15} /></button>
              <button type="button" className="broadcast-card__action" onClick={() => onDuplicate(item)} disabled={pending.duplicate} title="Duplicate"><FiCopy size={15} /></button>
            </>
          )}
          {['cancelled', 'expired'].includes(item.status) && (
            <button type="button" className="broadcast-card__action" onClick={() => onDuplicate(item)} disabled={pending.duplicate} title="Duplicate"><FiCopy size={15} /></button>
          )}
          <button
            type="button"
            className="broadcast-card__action broadcast-card__action--danger"
            onClick={() => onDelete(item)}
            disabled={pending.delete}
            title="Delete"
          >
            <FiTrash2 size={15} />
          </button>
        </div>
      </header>

      <div className="broadcast-card__meta">
        <span className="broadcast-meta-chip">{item.audience_display || item.audience}</span>
        {channelLabels.map((label, idx) => (
          <ChannelPill key={`${item.id}-${label}`} channel={channels[idx] || label.toLowerCase()} label={label} />
        ))}
      </div>

      <div className="broadcast-card__body">
        <p>{item.message}</p>
      </div>

      <footer className="broadcast-card__footer">
        <div className="broadcast-card__footer-stats">{footerText}</div>
      </footer>
    </motion.article>
  );
}

function ChannelToggles({ channels, onChange, disabled = false }) {
  return (
    <div className="broadcast-channel-toggles d-flex flex-wrap gap-2">
      {CHANNEL_OPTIONS.map(({ value, label, icon: Icon }) => {
        const active = channels.includes(value);
        return (
          <button
            key={value}
            type="button"
            className={`broadcast-channel-toggle ${active ? 'is-active' : ''}`}
            onClick={() => {
              if (disabled) return;
              onChange(
                active ? channels.filter((ch) => ch !== value) : [...channels, value],
              );
            }}
            disabled={disabled}
          >
            <Icon size={15} />
            <span>{label}</span>
          </button>
        );
      })}
    </div>
  );
}

function BroadcastEditor({
  open,
  form,
  preview,
  previewLoading,
  onChange,
  onPreview,
  onClose,
  onSave,
  saving,
  readOnly = false,
}) {
  if (!open) return null;

  return (
    <div className="plan-ad-editor-overlay" onClick={onClose} role="presentation">
      <motion.div
        className="plan-ad-editor broadcast-editor"
        initial={{ opacity: 0, y: 16, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 10, scale: 0.98 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="plan-ad-editor-header">
          <div>
            <h5 className="fw-bold mb-1">
              {readOnly ? 'View Broadcast' : form.id ? 'Edit Broadcast' : 'Create Broadcast'}
            </h5>
            <p className="text-muted small mb-0">
              Compose a message and deliver it via email, SMS, or WhatsApp to school admins.
            </p>
          </div>
          <button type="button" className="btn btn-link text-muted p-0" onClick={onClose} aria-label="Close">
            <FiX size={20} />
          </button>
        </div>

        <div className="plan-ad-editor-body">
          <div className="row g-4">
            <div className="col-lg-7">
              <div className="row g-3">
                <div className="col-12">
                  <label className="form-label small fw-semibold">Title</label>
                  <input
                    className="form-control"
                    value={form.title}
                    onChange={(e) => onChange('title', e.target.value)}
                    placeholder="Platform announcement"
                    disabled={readOnly}
                  />
                </div>
                <div className="col-12">
                  <label className="form-label small fw-semibold">Message</label>
                  <textarea
                    className="form-control"
                    rows={5}
                    value={form.message}
                    onChange={(e) => onChange('message', e.target.value)}
                    disabled={readOnly}
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label small fw-semibold">Audience</label>
                  <select
                    className="form-select"
                    value={form.audience}
                    onChange={(e) => onChange('audience', e.target.value)}
                    disabled={readOnly}
                  >
                    {AUDIENCE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div className="col-md-6">
                  <label className="form-label small fw-semibold">Severity</label>
                  <select
                    className="form-select"
                    value={form.severity}
                    onChange={(e) => onChange('severity', e.target.value)}
                    disabled={readOnly}
                  >
                    {SEVERITY_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div className="col-12">
                  <label className="form-label small fw-semibold">Broadcast channels</label>
                  <ChannelToggles
                    channels={form.channels}
                    onChange={(value) => onChange('channels', value)}
                    disabled={readOnly}
                  />
                </div>
                {!readOnly && (
                  <div className="col-md-6">
                    <label className="form-label small fw-semibold">Schedule for later</label>
                    <input
                      type="datetime-local"
                      className="form-control"
                      value={form.starts_at}
                      onChange={(e) => onChange('starts_at', e.target.value)}
                    />
                  </div>
                )}
              </div>
            </div>

            <div className="col-lg-5">
              <div className="plan-ad-editor-preview-wrap broadcast-preview-panel">
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <h6 className="fw-bold mb-0">Audience preview</h6>
                  {!readOnly && (
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-secondary"
                      onClick={onPreview}
                      disabled={previewLoading || !form.channels.length}
                    >
                      <FiUsers size={14} className="me-1" />
                      {previewLoading ? 'Loading…' : 'Refresh'}
                    </button>
                  )}
                </div>

                {preview ? (
                  <div className="small">
                    <div className="broadcast-preview-stat">
                      <span className="text-muted">School admins</span>
                      <strong>{preview.total_recipients}</strong>
                    </div>
                    <div className="broadcast-preview-stat">
                      <span className="text-muted">Schools</span>
                      <strong>{preview.total_schools}</strong>
                    </div>
                    {Object.entries(preview.channel_stats || {}).map(([channel, stats]) => (
                      <div key={channel} className="broadcast-preview-channel mt-2">
                        <div className="fw-semibold">{stats.label}</div>
                        <div className="text-muted">
                          {stats.reachable} reachable · {stats.unreachable} missing contact
                        </div>
                      </div>
                    ))}
                    {preview.sample_recipients?.length > 0 && (
                      <div className="mt-3">
                        <div className="text-muted mb-1">Sample recipients</div>
                        <ul className="list-unstyled mb-0">
                          {preview.sample_recipients.map((item) => (
                            <li key={item.id} className="text-truncate">
                              {item.name} · {item.school}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-muted small mb-0">
                    Select channels and refresh to see how many school admins will receive this broadcast.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        {!readOnly && (
          <div className="plan-ad-editor-footer justify-content-end">
            <button type="button" className="btn btn-primary" onClick={onSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save draft'}
            </button>
          </div>
        )}
      </motion.div>
    </div>
  );
}

function DeliveryDrawer({ broadcast, onClose }) {
  const { data: deliveries = [], isLoading } = useQuery({
    queryKey: ['broadcast-deliveries', broadcast?.id],
    queryFn: () => broadcastService.deliveries(broadcast.id, { page_size: 100 }),
    enabled: Boolean(broadcast?.id),
  });

  if (!broadcast) return null;

  return (
    <div className="plan-ad-editor-overlay" onClick={onClose} role="presentation">
      <motion.div
        className="plan-ad-editor broadcast-delivery-drawer"
        initial={{ opacity: 0, x: 24 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 24 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="plan-ad-editor-header">
          <div>
            <h5 className="fw-bold mb-1">Delivery log</h5>
            <p className="text-muted small mb-0">{broadcast.title}</p>
          </div>
          <button type="button" className="btn btn-link text-muted p-0" onClick={onClose} aria-label="Close">
            <FiX size={20} />
          </button>
        </div>
        <div className="plan-ad-editor-body">
          <div className="d-flex flex-wrap gap-3 mb-3 small">
            <span><strong>{broadcast.recipient_count}</strong> recipients</span>
            <span className="text-success"><strong>{broadcast.delivered_count}</strong> delivered</span>
            <span className="text-danger"><strong>{broadcast.failed_count}</strong> failed</span>
            <span className="text-muted"><strong>{broadcast.skipped_count}</strong> skipped</span>
          </div>
          {isLoading ? (
            <p className="text-muted small">Loading deliveries…</p>
          ) : deliveries.length === 0 ? (
            <p className="text-muted small mb-0">No delivery records yet.</p>
          ) : (
            <div className="table-responsive">
              <table className="table table-sm align-middle mb-0">
                <thead>
                  <tr>
                    <th>Recipient</th>
                    <th>Channel</th>
                    <th>Status</th>
                    <th>Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {deliveries.map((row) => (
                    <tr key={row.id}>
                      <td>
                        <div className="fw-semibold">{row.recipient_name}</div>
                        <div className="text-muted small">{row.school_name}</div>
                      </td>
                      <td className="text-capitalize">{row.channel}</td>
                      <td><StatusBadge status={row.status} /></td>
                      <td className="small text-muted">{row.error_message || row.provider_reference || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

export function Broadcast() {
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [deliveryBroadcast, setDeliveryBroadcast] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [preview, setPreview] = useState(null);
  const [readOnly, setReadOnly] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');

  const { data: broadcasts = [], isLoading } = useQuery({
    queryKey: ['broadcasts'],
    queryFn: () => broadcastService.list({ page_size: 50, ordering: '-starts_at' }),
  });

  const { data: channelStatus } = useQuery({
    queryKey: ['broadcast-channel-status'],
    queryFn: () => broadcastService.getChannelStatus(),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['broadcasts'] });
    queryClient.invalidateQueries({ queryKey: ['broadcast-deliveries'] });
  };

  const saveMutation = useMutation({
    mutationFn: async (payload) => {
      const body = {
        title: payload.title,
        message: payload.message,
        channels: payload.channels,
        audience: payload.audience,
        severity: payload.severity,
        starts_at: toIsoOrNull(payload.starts_at) || new Date().toISOString(),
        ends_at: toIsoOrNull(payload.ends_at),
        status: 'draft',
      };
      if (payload.id) return broadcastService.update(payload.id, body);
      return broadcastService.create(body);
    },
    onSuccess: () => {
      notify.success('Broadcast saved as draft.');
      setEditorOpen(false);
      invalidate();
    },
    onError: (err) => notify.error(extractApiError(err, 'Could not save broadcast.')),
  });

  const previewMutation = useMutation({
    mutationFn: (payload) => broadcastService.preview(payload),
    onSuccess: (data) => setPreview(data),
    onError: (err) => notify.error(extractApiError(err, 'Could not preview audience.')),
  });

  const sendMutation = useMutation({
    mutationFn: (id) => broadcastService.send(id),
    onSuccess: (data) => {
      notify.success(data?.message || 'Broadcast sent.');
      invalidate();
    },
    onError: (err) => notify.error(extractApiError(err, 'Could not send broadcast.')),
  });

  const scheduleMutation = useMutation({
    mutationFn: ({ id, startsAt }) => broadcastService.schedule(id, {
      starts_at: toIsoOrNull(startsAt),
    }),
    onSuccess: (data) => {
      notify.success(data?.message || 'Broadcast scheduled.');
      invalidate();
    },
    onError: (err) => notify.error(extractApiError(err, 'Could not schedule broadcast.')),
  });

  const cancelMutation = useMutation({
    mutationFn: (id) => broadcastService.cancel(id),
    onSuccess: (data) => {
      notify.success(data?.message || 'Broadcast cancelled.');
      invalidate();
    },
    onError: (err) => notify.error(extractApiError(err, 'Could not cancel broadcast.')),
  });

  const duplicateMutation = useMutation({
    mutationFn: (id) => broadcastService.duplicate(id),
    onSuccess: () => {
      notify.success('Broadcast duplicated as draft.');
      invalidate();
    },
    onError: (err) => notify.error(extractApiError(err, 'Could not duplicate broadcast.')),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => broadcastService.delete(id),
    onSuccess: (data) => {
      notify.success(data?.message || 'Broadcast deleted.');
      if (deliveryBroadcast?.id && data?.broadcast_id === deliveryBroadcast.id) {
        setDeliveryBroadcast(null);
      }
      invalidate();
    },
    onError: (err) => notify.error(extractApiError(err, 'Could not delete broadcast.')),
  });

  const sortedBroadcasts = useMemo(() => {
    const sorted = [...broadcasts].sort((a, b) => new Date(b.starts_at) - new Date(a.starts_at));
    if (statusFilter === 'all') return sorted;
    return sorted.filter((item) => item.status === statusFilter);
  }, [broadcasts, statusFilter]);

  const statusCounts = useMemo(() => {
    const counts = { all: broadcasts.length };
    broadcasts.forEach((item) => {
      counts[item.status] = (counts[item.status] || 0) + 1;
    });
    return counts;
  }, [broadcasts]);

  const openCreate = () => {
    setForm({ ...EMPTY_FORM, starts_at: formatDateTimeLocal(new Date(Date.now() + 3600000)) });
    setPreview(null);
    setReadOnly(false);
    setEditorOpen(true);
  };

  const openEdit = (item) => {
    setForm({
      id: item.id,
      title: item.title,
      message: item.message,
      channels: item.channels || [],
      audience: item.audience,
      severity: item.severity,
      starts_at: formatDateTimeLocal(item.starts_at),
      ends_at: formatDateTimeLocal(item.ends_at),
    });
    setPreview(null);
    setReadOnly(false);
    setEditorOpen(true);
    previewMutation.mutate({ audience: item.audience, channels: item.channels || [] });
  };

  const openView = (item) => {
    setForm({
      id: item.id,
      title: item.title,
      message: item.message,
      channels: item.channels || [],
      audience: item.audience,
      severity: item.severity,
      starts_at: formatDateTimeLocal(item.starts_at),
      ends_at: formatDateTimeLocal(item.ends_at),
    });
    setReadOnly(true);
    setEditorOpen(true);
  };

  const handleSave = () => {
    if (!form.title?.trim() || !form.message?.trim()) {
      notify.warning('Title and message are required.');
      return;
    }
    if (!form.channels?.length) {
      notify.warning('Select at least one broadcast channel.');
      return;
    }
    saveMutation.mutate(form);
  };

  const handleSend = async (item) => {
    const result = await alert.confirm({
      title: 'Send broadcast now?',
      text: `Deliver "${item.title}" to ${item.audience_display || item.audience} via ${(item.channels_display || item.channels || []).join(', ') || 'selected channels'}.`,
      confirmText: 'Yes, send now',
      cancelText: 'Cancel',
    });
    if (!result.isConfirmed) return;
    sendMutation.mutate(item.id);
  };

  const handleSchedule = async (item) => {
    const startsAt = item.starts_at || form.starts_at;
    if (!startsAt) {
      notify.warning('Set a schedule date before scheduling.');
      return;
    }
    const result = await alert.confirm({
      title: 'Schedule broadcast?',
      text: `This broadcast will send automatically at ${new Date(startsAt).toLocaleString()}.`,
      confirmText: 'Yes, schedule',
      cancelText: 'Cancel',
    });
    if (!result.isConfirmed) return;
    scheduleMutation.mutate({ id: item.id, startsAt });
  };

  const handleDelete = async (item) => {
    const messages = {
      draft: 'This draft will be permanently removed from the database.',
      scheduled: 'This scheduled broadcast will be permanently removed and will not send.',
      sent: 'This broadcast and its delivery log will be permanently removed from the database.',
      cancelled: 'This cancelled broadcast will be permanently removed from the database.',
      expired: 'This expired broadcast will be permanently removed from the database.',
    };
    const result = await alert.confirm({
      title: 'Delete broadcast?',
      text: messages[item.status] || 'This broadcast will be permanently removed from the database.',
      confirmText: 'Yes, delete',
      cancelText: 'Keep it',
      icon: 'warning',
      danger: true,
    });
    if (!result.isConfirmed) return;
    deleteMutation.mutate(item.id);
  };

  if (isLoading) return <PageSkeleton />;

  return (
    <div className="broadcast-page">
      <PageHeader
        title="Broadcast"
        subtitle="Send announcements to school admins via email, SMS, and WhatsApp"
        actions={(
          <button type="button" className="btn btn-primary btn-sm" onClick={openCreate}>
            <FiPlus size={14} className="me-1" /> New broadcast
          </button>
        )}
      />

      <ChannelStatusBar status={channelStatus} />

      <div className="broadcast-filter-tabs mb-4">
        {STATUS_FILTERS.map((filter) => (
          <button
            key={filter.value}
            type="button"
            className={`broadcast-filter-tab ${statusFilter === filter.value ? 'is-active' : ''}`}
            onClick={() => setStatusFilter(filter.value)}
          >
            <span>{filter.label}</span>
            <span className="broadcast-filter-tab__count">{statusCounts[filter.value] || 0}</span>
          </button>
        ))}
      </div>

      {sortedBroadcasts.length === 0 ? (
        <div className="apex-card broadcast-empty p-5 text-center text-muted">
          <FiSend size={36} className="mb-3 opacity-50" />
          <h5 className="fw-bold text-body">
            {statusFilter === 'all' ? 'No broadcasts yet' : `No ${statusFilter} broadcasts`}
          </h5>
          <p className="mb-3">Create a draft, preview your audience, then send or schedule delivery.</p>
          {statusFilter === 'all' && (
            <button type="button" className="btn btn-primary btn-sm" onClick={openCreate}>
              <FiPlus size={14} className="me-1" /> Create broadcast
            </button>
          )}
        </div>
      ) : (
        <div className="broadcast-card-grid">
          {sortedBroadcasts.map((item, index) => (
            <BroadcastCard
              key={item.id}
              item={item}
              index={index}
              onEdit={openEdit}
              onView={openView}
              onSend={handleSend}
              onSchedule={handleSchedule}
              onDelete={handleDelete}
              onCancel={(row) => cancelMutation.mutate(row.id)}
              onDuplicate={(row) => duplicateMutation.mutate(row.id)}
              onDeliveries={setDeliveryBroadcast}
              pending={{
                send: sendMutation.isPending,
                schedule: scheduleMutation.isPending,
                delete: deleteMutation.isPending,
                cancel: cancelMutation.isPending,
                duplicate: duplicateMutation.isPending,
              }}
            />
          ))}
        </div>
      )}

      <AnimatePresence>
        {editorOpen && (
          <BroadcastEditor
            open={editorOpen}
            form={form}
            preview={preview}
            previewLoading={previewMutation.isPending}
            onChange={(field, value) => {
              setForm((prev) => ({ ...prev, [field]: value }));
              if (field === 'audience' || field === 'channels') setPreview(null);
            }}
            onPreview={() => previewMutation.mutate({
              audience: form.audience,
              channels: form.channels,
            })}
            onClose={() => setEditorOpen(false)}
            onSave={handleSave}
            saving={saveMutation.isPending}
            readOnly={readOnly}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {deliveryBroadcast && (
          <DeliveryDrawer
            broadcast={deliveryBroadcast}
            onClose={() => setDeliveryBroadcast(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

export default Broadcast;