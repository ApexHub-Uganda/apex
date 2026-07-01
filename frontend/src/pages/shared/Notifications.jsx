import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { FiBell, FiCheck, FiInfo, FiAlertCircle } from 'react-icons/fi';
import { useAuth } from '../../hooks/useAuth';
import PageHeader from '../../components/PageHeader';
import { notificationFeedService, notificationsService, platformNotificationsService } from '../../services/moduleService';
import { extractApiError, notify } from '../../utils/notify';

const iconMap = {
  info: FiInfo,
  success: FiCheck,
  warning: FiAlertCircle,
  error: FiAlertCircle,
  school_registration: FiInfo,
  trial_request: FiInfo,
  payment_attempt: FiAlertCircle,
};

const formatDate = (value) => {
  if (!value) return '—';
  return new Date(value).toLocaleString();
};

export function Notifications() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const isSuperAdmin = user?.role === 'super_admin';

  const { data: notifications = [], isLoading } = useQuery({
    queryKey: ['notifications-page', isSuperAdmin],
    queryFn: async () => {
      if (isSuperAdmin) {
        return platformNotificationsService.list({ status: 'pending', ordering: '-created_at', page_size: 50 });
      }
      return notificationsService.list({ ordering: '-created_at', page_size: 50 });
    },
  });

  const markAllRead = useMutation({
    mutationFn: () => notificationFeedService.markAllRead(),
    onSuccess: (data) => {
      notify.success(data?.message || 'All notifications marked as read.');
      queryClient.invalidateQueries({ queryKey: ['notifications-page'] });
      queryClient.invalidateQueries({ queryKey: ['notification-feed'] });
      queryClient.invalidateQueries({ queryKey: ['platform-notifications-summary'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to mark notifications as read.')),
  });

  const normalized = notifications.map((n) => ({
    id: n.id,
    title: n.title,
    message: n.message,
    type: n.notification_type || n.type || 'info',
    is_read: n.is_read ?? n.read ?? false,
    created_at: n.created_at,
    school_name: n.school_name,
  }));

  const unread = normalized.filter((n) => !n.is_read).length;

  return (
    <div>
      <PageHeader
        title="Notifications"
        subtitle={`${unread} unread notification${unread !== 1 ? 's' : ''}`}
        actions={
          unread > 0 && (
            <button className="btn btn-outline-primary btn-sm" onClick={() => markAllRead.mutate()}>
              Mark all as read
            </button>
          )
        }
      />

      <div className="d-flex flex-column gap-2">
        {isLoading ? (
          <div className="text-center py-5 text-muted">Loading...</div>
        ) : normalized.length === 0 ? (
          <div className="apex-card p-5 text-center text-muted">
            <FiBell size={40} className="mb-3 opacity-50" />
            <p>No notifications yet</p>
          </div>
        ) : (
          normalized.map((notif, i) => {
            const Icon = iconMap[notif.type] || FiInfo;
            return (
              <motion.div
                key={notif.id}
                className={`apex-card p-3 d-flex gap-3 align-items-start ${!notif.is_read ? 'border-start border-3 border-primary' : ''}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <div
                  className="d-flex align-items-center justify-content-center flex-shrink-0"
                  style={{
                    width: 40, height: 40, borderRadius: 10,
                    background: 'rgba(15, 118, 110, 0.1)', color: 'var(--apex-primary)',
                  }}
                >
                  <Icon size={18} />
                </div>
                <div className="flex-grow-1">
                  <div className="d-flex justify-content-between">
                    <h6 className="fw-semibold mb-1">{notif.title}</h6>
                    <span className="text-muted small">{formatDate(notif.created_at)}</span>
                  </div>
                  {notif.school_name && (
                    <div className="text-muted small mb-1">{notif.school_name}</div>
                  )}
                  <p className="text-muted small mb-0">{notif.message}</p>
                </div>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}

export default Notifications;