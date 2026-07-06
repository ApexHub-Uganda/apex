import {
  notificationFeedService,
  notificationsService,
  platformNotificationsService,
} from '../services/moduleService';

export function canMarkReadNotification(item, { isSuperAdmin = false } = {}) {
  if (!item?.id || item.metadata?.synthetic) return false;
  return isSuperAdmin || !item.metadata?.advertisement;
}

export function canSelectNotification(item) {
  return Boolean(item?.id);
}

export async function markNotificationsRead(items, { isSuperAdmin = false } = {}) {
  const eligible = (items || []).filter(
    (item) => canMarkReadNotification(item, { isSuperAdmin }) && !item.is_read,
  );
  if (!eligible.length) return 0;

  await Promise.all(eligible.map((item) => (
    isSuperAdmin
      ? platformNotificationsService.markRead(item.id)
      : notificationsService.markRead(item.id)
  )));

  return eligible.length;
}

export async function deleteNotificationById(id, { isSuperAdmin = false } = {}) {
  if (isSuperAdmin) {
    return platformNotificationsService.delete(id);
  }
  return notificationFeedService.deleteOne(id);
}

export async function deleteNotifications(items, { isSuperAdmin = false, viaFeed = false } = {}) {
  const eligible = (items || []).filter((item) => canSelectNotification(item));
  if (!eligible.length) return 0;

  await Promise.all(eligible.map((item) => (
    viaFeed
      ? notificationFeedService.deleteOne(item.id)
      : deleteNotificationById(item.id, { isSuperAdmin })
  )));
  return eligible.length;
}