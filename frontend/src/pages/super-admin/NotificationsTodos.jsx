import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FiBell, FiCheck, FiX, FiAlertTriangle, FiChevronRight, FiMail, FiCreditCard, FiUserPlus,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import StatusBadge from '../../components/StatusBadge';
import { PageSkeleton } from '../../components/LoadingSkeleton';
import { platformNotificationsService } from '../../services/moduleService';
import { extractApiError, notify } from '../../utils/notify';

const TYPE_ICONS = {
  school_registration: FiUserPlus,
  trial_request: FiMail,
  payment_attempt: FiCreditCard,
  account_activation: FiCheck,
};

const formatDate = (value) => {
  if (!value) return '—';
  return new Date(value).toLocaleString();
};

export function NotificationsTodos() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState('pending');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['platform-notifications', filter],
    queryFn: () => platformNotificationsService.list({
      status: filter === 'all' ? undefined : filter,
      ordering: '-created_at',
      page_size: 50,
    }),
  });

  const approveMutation = useMutation({
    mutationFn: (id) => platformNotificationsService.approve(id),
    onSuccess: (data) => {
      notify.success(data?.message || 'School approved successfully.');
      queryClient.invalidateQueries({ queryKey: ['platform-notifications'] });
      queryClient.invalidateQueries({ queryKey: ['platform-notifications-summary'] });
      queryClient.invalidateQueries({ queryKey: ['notification-feed'] });
      queryClient.invalidateQueries({ queryKey: ['schools'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to approve.')),
  });

  const dismissMutation = useMutation({
    mutationFn: (id) => platformNotificationsService.dismiss(id),
    onSuccess: () => {
      notify.info('Notification dismissed.');
      queryClient.invalidateQueries({ queryKey: ['platform-notifications'] });
      queryClient.invalidateQueries({ queryKey: ['platform-notifications-summary'] });
      queryClient.invalidateQueries({ queryKey: ['notification-feed'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to dismiss notification.')),
  });

  const notifications = data || [];
  const busyId = approveMutation.isPending
    ? approveMutation.variables
    : dismissMutation.isPending
      ? dismissMutation.variables
      : null;

  if (isLoading) return <PageSkeleton />;

  if (isError) {
    return (
      <div className="apex-card p-5 text-center">
        <FiAlertTriangle size={32} className="text-warning mb-3" />
        <h5 className="fw-bold">Unable to load notifications</h5>
        <button className="btn btn-primary btn-sm mt-2" onClick={() => refetch()}>Retry</button>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Notifications & To-do"
        subtitle="Review new school registrations and approve accounts"
      />

      <div className="d-flex flex-wrap gap-2 mb-4">
        {[
          { key: 'pending', label: 'Pending' },
          { key: 'approved', label: 'Approved' },
          { key: 'dismissed', label: 'Dismissed' },
          { key: 'all', label: 'All' },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={`btn btn-sm ${filter === tab.key ? 'btn-primary' : 'btn-outline-secondary'}`}
            onClick={() => setFilter(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {notifications.length === 0 ? (
        <div className="apex-card p-5 text-center text-muted">
          <FiBell size={32} className="mb-3 opacity-50" />
          <p className="mb-0">No notifications in this category.</p>
        </div>
      ) : (
        <div className="d-flex flex-column gap-3">
          {notifications.map((item, index) => {
            const Icon = TYPE_ICONS[item.notification_type] || FiBell;
            const planName = item.metadata?.plan_name;
            const regType = item.registration_type || item.metadata?.registration_type;

            return (
              <motion.div
                key={item.id}
                className="apex-card p-4"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.03 }}
              >
                <div className="d-flex flex-column flex-lg-row align-items-lg-start justify-content-between gap-3">
                  <div className="d-flex gap-3 flex-grow-1">
                    <div
                      className="rounded-3 d-flex align-items-center justify-content-center flex-shrink-0"
                      style={{
                        width: 44,
                        height: 44,
                        background: item.priority === 'high' ? 'rgba(255, 127, 80, 0.12)' : 'rgba(15, 118, 110, 0.1)',
                        color: item.priority === 'high' ? 'var(--apex-secondary)' : 'var(--apex-primary)',
                      }}
                    >
                      <Icon size={20} />
                    </div>
                    <div className="flex-grow-1">
                      <div className="d-flex flex-wrap align-items-center gap-2 mb-1">
                        <h6 className="fw-bold mb-0">{item.title}</h6>
                        <StatusBadge status={item.status} />
                        {!item.is_read && <span className="badge bg-primary">New</span>}
                      </div>
                      <p className="text-muted small mb-2">{item.message}</p>
                      <div className="d-flex flex-wrap gap-3 small text-muted">
                        <span>{item.school_name}</span>
                        {planName && <span>Plan: {planName}</span>}
                        {regType && <span>Type: {regType.replace('_', ' ')}</span>}
                        <span>{formatDate(item.created_at)}</span>
                      </div>
                    </div>
                  </div>

                  <div className="d-flex flex-wrap gap-2">
                    {item.status === 'pending' && (
                      <>
                        <button
                          type="button"
                          className="btn btn-sm btn-success d-flex align-items-center gap-1"
                          disabled={busyId === item.id}
                          onClick={() => approveMutation.mutate(item.id)}
                        >
                          <FiCheck size={14} />
                          {busyId === item.id ? 'Approving...' : 'Approve'}
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1"
                          disabled={busyId === item.id}
                          onClick={() => dismissMutation.mutate(item.id)}
                        >
                          <FiX size={14} />
                          Dismiss
                        </button>
                      </>
                    )}
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-primary d-flex align-items-center gap-1"
                      onClick={() => navigate(`/super-admin/schools/${item.school_id || item.tenant}`)}
                    >
                      View School <FiChevronRight size={14} />
                    </button>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default NotificationsTodos;