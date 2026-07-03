import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { FiBell, FiCheck, FiInfo, FiAlertCircle } from 'react-icons/fi';
import { buildUpgradePath } from '../../utils/upgradePaths';
import { useAuth } from '../../hooks/useAuth';
import PageHeader from '../../components/PageHeader';
import PlanAdvertisementPreview from '../../components/PlanAdvertisementPreview';
import NotificationItemActions from '../../components/NotificationItemActions';
import {
  notificationFeedService,
  notificationsService,
  platformNotificationsService,
} from '../../services/moduleService';
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

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['notifications-page'] });
    queryClient.invalidateQueries({ queryKey: ['notification-feed'] });
    queryClient.invalidateQueries({ queryKey: ['platform-notifications'] });
    queryClient.invalidateQueries({ queryKey: ['platform-notifications-summary'] });
  };

  const { data: feed } = useQuery({
    queryKey: ['notification-feed', user?.id],
    queryFn: () => notificationFeedService.getFeed(),
    enabled: !!user && !isSuperAdmin,
  });

  const { data: notifications = [], isLoading } = useQuery({
    queryKey: ['notifications-page', isSuperAdmin],
    queryFn: async () => {
      if (isSuperAdmin) {
        return platformNotificationsService.list({ ordering: '-created_at', page_size: 50 });
      }
      return notificationsService.list({ ordering: '-created_at', page_size: 50 });
    },
  });

  const markAllRead = useMutation({
    mutationFn: () => notificationFeedService.markAllRead(),
    onSuccess: (data) => {
      notify.success(data?.message || 'All notifications marked as read.');
      invalidateAll();
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to mark notifications as read.')),
  });

  const deleteAll = useMutation({
    mutationFn: () => (isSuperAdmin
      ? platformNotificationsService.deleteAll()
      : notificationFeedService.deleteAll()),
    onSuccess: (data) => {
      notify.success(data?.message || 'All notifications deleted.');
      invalidateAll();
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to delete notifications.')),
  });

  const deleteOne = useMutation({
    mutationFn: (itemId) => (isSuperAdmin
      ? platformNotificationsService.delete(itemId)
      : notificationFeedService.deleteOne(itemId)),
    onSuccess: (data) => {
      notify.success(data?.message || 'Notification deleted.');
      invalidateAll();
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to delete notification.')),
  });

  const markReadOne = useMutation({
    mutationFn: (itemId) => platformNotificationsService.markRead(itemId),
    onSuccess: () => invalidateAll(),
    onError: (err) => notify.error(extractApiError(err, 'Unable to mark notification as read.')),
  });

  const pinnedAds = (feed?.items || []).filter(
    (item) => item.metadata?.advertisement || item.metadata?.pinned,
  );

  const normalized = notifications.map((n) => ({
    id: n.id,
    title: n.title,
    message: n.message,
    type: n.notification_type || n.type || 'info',
    is_read: n.is_read ?? n.read ?? false,
    created_at: n.created_at,
    school_name: n.school_name,
    metadata: n.metadata || {},
  }));

  const unread = normalized.filter((n) => !n.is_read).length;
  const hasContent = pinnedAds.length > 0 || normalized.length > 0;

  return (
    <div>
      <PageHeader
        title="Notifications"
        subtitle={`${unread} unread notification${unread !== 1 ? 's' : ''}`}
        actions={hasContent && (
          <div className="d-flex gap-2">
            {unread > 0 && (
              <button className="btn btn-outline-primary btn-sm" onClick={() => markAllRead.mutate()}>
                Mark all as read
              </button>
            )}
            <button className="btn btn-outline-danger btn-sm" onClick={() => deleteAll.mutate()}>
              Delete all
            </button>
          </div>
        )}
      />

      <div className="d-flex flex-column gap-2">
        {pinnedAds.map((item) => (
          <motion.div
            key={item.id}
            className="apex-card notification-page-card p-4 border-start border-3 border-primary"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="d-flex justify-content-between align-items-start gap-3">
              <div className="flex-grow-1">
                <Link
                  to={buildUpgradePath(item.metadata?.suggested_plan_slug)}
                  className="text-decoration-none text-body d-block"
                >
                  <PlanAdvertisementPreview item={item} />
                </Link>
              </div>
              <NotificationItemActions
                itemId={item.id}
                isRead={item.is_read}
                onDelete={(id) => deleteOne.mutate(id)}
                deleting={deleteOne.isPending}
              />
            </div>
          </motion.div>
        ))}

        {isLoading ? (
          <div className="text-center py-5 text-muted">Loading...</div>
        ) : normalized.length === 0 ? (
          pinnedAds.length === 0 && (
            <div className="apex-card p-5 text-center text-muted">
              <FiBell size={40} className="mb-3 opacity-50" />
              <p>No notifications yet</p>
            </div>
          )
        ) : (
          normalized.map((notif, i) => {
            const Icon = iconMap[notif.type] || FiInfo;
            const isAd = notif.metadata?.advertisement_id;
            if (isAd && pinnedAds.some((ad) => ad.metadata?.ad_id === notif.metadata.advertisement_id)) {
              return null;
            }
            return (
              <motion.div
                key={notif.id}
                className={`apex-card notification-page-card p-3 d-flex gap-3 align-items-start ${!notif.is_read ? 'border-start border-3 border-primary' : ''}`}
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
                <div className="flex-grow-1 min-w-0">
                  <div className="d-flex justify-content-between align-items-start gap-2">
                    <div className="flex-grow-1 min-w-0">
                      <div className="d-flex justify-content-between gap-2">
                        <h6 className="fw-semibold mb-1">{notif.title}</h6>
                        <span className="text-muted small flex-shrink-0">{formatDate(notif.created_at)}</span>
                      </div>
                      {notif.school_name && (
                        <div className="text-muted small mb-1">{notif.school_name}</div>
                      )}
                      {isAd ? (
                        <PlanAdvertisementPreview
                          item={{
                            title: notif.title,
                            message: notif.message,
                            metadata: {
                              headline: notif.metadata.headline,
                              highlights: notif.metadata.highlights,
                              cta_label: notif.metadata.cta_label,
                              suggested_plan_slug: notif.metadata.suggested_plan_slug,
                            },
                          }}
                          compact
                        />
                      ) : (
                        <p className="text-muted small mb-0">{notif.message}</p>
                      )}
                    </div>
                    <NotificationItemActions
                      itemId={notif.id}
                      isRead={notif.is_read}
                      canMarkRead={isSuperAdmin}
                      onMarkRead={(id) => markReadOne.mutate(id)}
                      onDelete={(id) => deleteOne.mutate(id)}
                      deleting={deleteOne.isPending}
                      marking={markReadOne.isPending}
                    />
                  </div>
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