import { useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FiBell } from 'react-icons/fi';
import { useAuth } from '../../hooks/useAuth';
import { useNotificationBatchSelection } from '../../hooks/useNotificationBatchSelection';
import PageHeader from '../../components/PageHeader';
import NotificationBatchActions from '../../components/NotificationBatchActions';
import NotificationCapacityWarning from '../../components/NotificationCapacityWarning';
import NotificationDetailModal from '../../components/NotificationDetailModal';
import NotificationMessageList from '../../components/NotificationMessageList';
import {
  notificationFeedService,
  notificationsService,
  platformNotificationsService,
} from '../../services/moduleService';
import {
  canMarkReadNotification,
  deleteNotifications,
  markNotificationsRead,
} from '../../utils/notificationInbox';
import { alert, extractApiError, notify } from '../../utils/notify';

const INBOX_LIMIT = 20;

export function Notifications() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const isSuperAdmin = user?.role === 'super_admin';
  const [selectedNotification, setSelectedNotification] = useState(null);
  const {
    selectedCount,
    selectionMode,
    isSelected,
    toggleSelection,
    enterSelection,
    clearSelection,
    selectedIdList,
  } = useNotificationBatchSelection();

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['notifications-page'] });
    queryClient.invalidateQueries({ queryKey: ['notification-feed'] });
    queryClient.invalidateQueries({ queryKey: ['platform-notifications'] });
    queryClient.invalidateQueries({ queryKey: ['platform-notifications-summary'] });
  };

  const { data: feed } = useQuery({
    queryKey: ['notification-feed', user?.id],
    queryFn: () => notificationFeedService.getFeed(),
    enabled: !!user,
  });

  const { data: notifications = [], isLoading } = useQuery({
    queryKey: ['notifications-page', isSuperAdmin, user?.id],
    queryFn: async () => {
      if (isSuperAdmin) {
        return platformNotificationsService.list({ ordering: '-created_at', page_size: INBOX_LIMIT });
      }
      return notificationsService.list({ ordering: '-created_at', page_size: INBOX_LIMIT });
    },
    enabled: !!user,
  });

  const markAllRead = useMutation({
    mutationFn: () => notificationFeedService.markAllRead(),
    onSuccess: (data) => {
      notify.success(data?.message || 'All messages marked as read.');
      invalidateAll();
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to mark messages as read.')),
  });

  const deleteAll = useMutation({
    mutationFn: () => (isSuperAdmin
      ? platformNotificationsService.deleteAll()
      : notificationFeedService.deleteAll()),
    onSuccess: (data) => {
      notify.success(data?.message || 'All messages deleted.');
      invalidateAll();
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to delete messages.')),
  });

  const deleteOne = useMutation({
    mutationFn: (itemId) => (isSuperAdmin
      ? platformNotificationsService.delete(itemId)
      : notificationFeedService.deleteOne(itemId)),
    onSuccess: (data) => {
      notify.success(data?.message || 'Message deleted.');
      invalidateAll();
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to delete message.')),
  });

  const markReadOne = useMutation({
    mutationFn: (itemId) => (isSuperAdmin
      ? platformNotificationsService.markRead(itemId)
      : notificationsService.markRead(itemId)),
    onSuccess: () => invalidateAll(),
    // Read-state is personal; avoid alarming toasts if a race/network blip occurs
    onError: () => { /* optimistic UI already updated */ },
  });

  const confirmDeleteAll = async () => {
    const result = await alert.confirm({
      title: 'Delete all messages?',
      text: 'This will permanently remove all messages from your inbox.',
      confirmText: 'Yes, delete all',
      cancelText: 'Cancel',
      icon: 'warning',
      danger: true,
    });
    if (result.isConfirmed) deleteAll.mutate();
  };

  const normalized = useMemo(() => notifications.map((n) => ({
    id: n.id,
    title: n.title,
    message: n.message,
    type: n.notification_type || n.type || 'info',
    is_read: n.is_read ?? n.read ?? false,
    created_at: n.created_at,
    action_url: n.action_url || (isSuperAdmin && n.tenant ? `/super-admin/schools/${n.tenant}` : ''),
    metadata: {
      ...(n.metadata || {}),
      ...(n.school_name ? { school_name: n.school_name } : {}),
    },
  })), [notifications, isSuperAdmin]);

  const feedItems = feed?.items || [];
  const pinnedAds = feedItems.filter((item) => item.metadata?.advertisement || item.metadata?.pinned);
  const feedRegular = normalized.filter(
    (n) => !n.metadata?.advertisement_id
      || !pinnedAds.some((ad) => ad.metadata?.ad_id === n.metadata.advertisement_id),
  );

  const displayItems = isSuperAdmin
    ? normalized.map((n) => ({
      ...n,
      metadata: { ...n.metadata, school_name: n.metadata.school_name },
    }))
    : [...pinnedAds, ...feedRegular];

  const pinnedItems = displayItems.filter((item) => item.metadata?.advertisement || item.metadata?.pinned);
  const regularItems = displayItems.filter((item) => !item.metadata?.advertisement && !item.metadata?.pinned);

  const inbox = feed?.inbox;
  const unread = displayItems.filter((n) => !n.is_read).length;
  const hasContent = displayItems.length > 0;

  const canMarkReadItem = (item) => canMarkReadNotification(item, { isSuperAdmin });

  const selectedItems = useMemo(
    () => displayItems.filter((item) => selectedIdList.includes(item.id)),
    [displayItems, selectedIdList],
  );

  const canBatchMarkRead = selectedItems.some(
    (item) => canMarkReadItem(item) && !item.is_read,
  );

  const batchMarkReadMutation = useMutation({
    mutationFn: () => markNotificationsRead(selectedItems, { isSuperAdmin }),
    onSuccess: (count) => {
      if (count > 0) {
        notify.success(`${count} message${count === 1 ? '' : 's'} marked as read.`);
      }
      clearSelection();
      invalidateAll();
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to mark selected messages as read.')),
  });

  const batchDeleteMutation = useMutation({
    mutationFn: () => deleteNotifications(selectedItems, { isSuperAdmin }),
    onSuccess: (count) => {
      notify.success(`${count} message${count === 1 ? '' : 's'} deleted.`);
      clearSelection();
      setSelectedNotification(null);
      invalidateAll();
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to delete selected messages.')),
  });

  const handleBatchDelete = async () => {
    if (!selectedCount) return;
    const result = await alert.confirm({
      title: `Delete ${selectedCount} message${selectedCount === 1 ? '' : 's'}?`,
      text: 'Selected messages will be permanently removed from your inbox.',
      confirmText: 'Yes, delete',
      cancelText: 'Cancel',
      icon: 'warning',
      danger: true,
    });
    if (result.isConfirmed) batchDeleteMutation.mutate();
  };

  const handleMarkReadItem = (item) => {
    if (!canMarkReadItem(item)) return;
    markReadOne.mutate(item.id);
    setSelectedNotification((current) => (
      current?.id === item.id ? { ...current, is_read: true } : current
    ));
  };

  const handleDeleteNotification = async (item) => {
    const result = await alert.delete('this message');
    if (!result.isConfirmed) return;
    deleteOne.mutate(item.id, {
      onSuccess: () => {
        setSelectedNotification(null);
        clearSelection();
      },
    });
  };

  const handleSelectNotification = (item) => {
    if (selectionMode) return;
    setSelectedNotification(item);
    // Auto mark-as-read on open (detail modal also does this; belt-and-braces)
    if (item && !item.is_read && canMarkReadItem(item)) {
      handleMarkReadItem(item);
    }
  };

  return (
    <div>
      <PageHeader
        title="Messages"
        subtitle={`${unread} unread · up to ${INBOX_LIMIT} messages stored`}
        actions={hasContent && (
          <div className="d-flex gap-2">
            {unread > 0 && (
              <button className="btn btn-outline-primary btn-sm" onClick={() => markAllRead.mutate()}>
                Mark all as read
              </button>
            )}
            <button className="btn btn-outline-danger btn-sm" onClick={confirmDeleteAll}>
              Delete all
            </button>
          </div>
        )}
      />

      <div className="notification-page-inbox">
        <NotificationCapacityWarning inbox={inbox} />

        <div className="apex-card overflow-hidden">
          {selectedCount > 0 && (
            <div className="notification-batch-actions-bar">
              <NotificationBatchActions
                count={selectedCount}
                onMarkRead={() => batchMarkReadMutation.mutate()}
                onDelete={handleBatchDelete}
                onClear={clearSelection}
                canMarkRead={canBatchMarkRead}
                marking={batchMarkReadMutation.isPending}
                deleting={batchDeleteMutation.isPending}
              />
            </div>
          )}
          {isLoading ? (
            <div className="text-center py-5 text-muted">Loading messages…</div>
          ) : !hasContent ? (
            <div className="p-5 text-center text-muted">
              <FiBell size={40} className="mb-3 opacity-50" />
              <p className="mb-0">No messages yet</p>
            </div>
          ) : (
            <NotificationMessageList
              pinnedItems={pinnedItems}
              regularItems={regularItems}
              onSelect={handleSelectNotification}
              selectionMode={selectionMode}
              isSelected={isSelected}
              onToggleSelect={toggleSelection}
              onEnterSelection={enterSelection}
            />
          )}
        </div>
      </div>

      <NotificationDetailModal
        item={selectedNotification}
        show={!!selectedNotification}
        onHide={() => setSelectedNotification(null)}
        onMarkRead={handleMarkReadItem}
        onDelete={handleDeleteNotification}
        canMarkRead={canMarkReadItem(selectedNotification)}
        marking={markReadOne.isPending}
        deleting={deleteOne.isPending}
      />
    </div>
  );
}

export default Notifications;