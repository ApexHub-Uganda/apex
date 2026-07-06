import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { FiMenu, FiBell, FiSun, FiMoon, FiUser, FiSettings, FiLogOut } from 'react-icons/fi';
import GlobalSearch from './GlobalSearch';
import UserAvatar from './UserAvatar';
import NotificationBatchActions from './NotificationBatchActions';
import NotificationCapacityWarning from './NotificationCapacityWarning';
import NotificationDetailModal from './NotificationDetailModal';
import NotificationMessageList from './NotificationMessageList';
import { useAuth } from '../hooks/useAuth';
import { useNotificationBatchSelection } from '../hooks/useNotificationBatchSelection';
import { useTheme } from '../hooks/useTheme';
import { useTenant } from '../hooks/useTenant';
import {
  notificationFeedService,
  notificationsService,
  platformNotificationsService,
} from '../services/moduleService';
import {
  canMarkReadNotification,
  deleteNotifications,
  markNotificationsRead,
} from '../utils/notificationInbox';
import { alert, extractApiError, notify } from '../utils/notify';
import SchoolNameWithBadge from './SchoolNameWithBadge';

export function Navbar({ onMenuClick, sidebarCollapsed, suspended = false }) {
  const { user, logout, isSchoolAdmin } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { tenant } = useTenant();
  const queryClient = useQueryClient();
  const [showDropdown, setShowDropdown] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
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
  const notificationsRef = useRef(null);
  const userMenuRef = useRef(null);

  const profilePath = user?.role === 'super_admin' ? '/super-admin/profile' : '/school-admin/profile';
  const settingsPath = user?.role === 'super_admin' ? '/super-admin/settings' : '/school-admin/settings';

  const { data: feed } = useQuery({
    queryKey: ['notification-feed', user?.id],
    queryFn: () => notificationFeedService.getFeed(),
    enabled: !!user,
    refetchInterval: 30000,
    staleTime: 15000,
    retry: 1,
  });

  const invalidateNotifications = () => {
    queryClient.invalidateQueries({ queryKey: ['notification-feed'] });
    queryClient.invalidateQueries({ queryKey: ['notifications-page'] });
    queryClient.invalidateQueries({ queryKey: ['platform-notifications'] });
    queryClient.invalidateQueries({ queryKey: ['platform-notifications-summary'] });
  };

  const markReadMutation = useMutation({
    mutationFn: (id) => platformNotificationsService.markRead(id),
    onSuccess: invalidateNotifications,
  });

  const markReadSchoolMutation = useMutation({
    mutationFn: (id) => notificationsService.markRead(id),
    onSuccess: invalidateNotifications,
  });

  const deleteOneMutation = useMutation({
    mutationFn: (itemId) => notificationFeedService.deleteOne(itemId),
    onSuccess: (data) => {
      notify.success(data?.message || 'Notification deleted.');
      invalidateNotifications();
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to delete notification.')),
  });

  const deleteAllMutation = useMutation({
    mutationFn: () => notificationFeedService.deleteAll(),
    onSuccess: (data) => {
      notify.success(data?.message || 'All notifications cleared.');
      invalidateNotifications();
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to clear notifications.')),
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => notificationFeedService.markAllRead(),
    onSuccess: (data) => {
      notify.success(data?.message || 'All notifications marked as read.');
      invalidateNotifications();
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to mark notifications as read.')),
  });

  const batchMarkReadMutation = useMutation({
    mutationFn: () => markNotificationsRead(selectedItems, { isSuperAdmin }),
    onSuccess: (count) => {
      if (count > 0) {
        notify.success(`${count} message${count === 1 ? '' : 's'} marked as read.`);
      }
      clearSelection();
      invalidateNotifications();
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to mark selected messages as read.')),
  });

  const batchDeleteMutation = useMutation({
    mutationFn: () => deleteNotifications(selectedItems, { viaFeed: true }),
    onSuccess: (count) => {
      notify.success(`${count} message${count === 1 ? '' : 's'} deleted.`);
      clearSelection();
      setSelectedNotification(null);
      invalidateNotifications();
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to delete selected messages.')),
  });

  const confirmDeleteAll = async () => {
    const result = await alert.confirm({
      title: 'Clear all notifications?',
      text: 'This will permanently remove all notifications from your feed.',
      confirmText: 'Yes, clear all',
      cancelText: 'Cancel',
      icon: 'warning',
      danger: true,
    });
    if (result.isConfirmed) deleteAllMutation.mutate();
  };

  const unreadCount = feed?.unread_count ?? 0;
  const inbox = feed?.inbox;
  const feedItems = feed?.items ?? [];

  const items = feedItems;
  const pinnedItems = items.filter((item) => item.metadata?.pinned || item.metadata?.advertisement);
  const regularItems = items.filter((item) => !item.metadata?.pinned && !item.metadata?.advertisement);
  const hasItems = pinnedItems.length > 0 || regularItems.length > 0;
  const isSuperAdmin = user?.role === 'super_admin';
  const selectedItems = items.filter((item) => selectedIdList.includes(item.id));
  const canBatchMarkRead = selectedItems.some(
    (item) => canMarkReadNotification(item, { isSuperAdmin }) && !item.is_read,
  );

  const viewAllPath = feed?.view_all_url
    || (user?.role === 'super_admin' ? '/super-admin/notifications' : '/school-admin/notifications');

  useEffect(() => {
    if (!showNotifications) clearSelection();
  }, [showNotifications, clearSelection]);

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

  useEffect(() => {
    if (!showNotifications && !showDropdown) return undefined;

    const handlePointerOutside = (event) => {
      const inNotifications = notificationsRef.current?.contains(event.target);
      const inUserMenu = userMenuRef.current?.contains(event.target);
      if (!inNotifications && !inUserMenu) {
        setShowNotifications(false);
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handlePointerOutside);
    document.addEventListener('touchstart', handlePointerOutside);

    return () => {
      document.removeEventListener('mousedown', handlePointerOutside);
      document.removeEventListener('touchstart', handlePointerOutside);
    };
  }, [showNotifications, showDropdown]);

  const canMarkReadItem = (item) => canMarkReadNotification(item, { isSuperAdmin });

  const handleMarkReadItem = (item) => {
    if (!canMarkReadItem(item)) return;
    if (user?.role === 'super_admin') {
      markReadMutation.mutate(item.id);
    } else {
      markReadSchoolMutation.mutate(item.id);
    }
    setSelectedNotification((current) => (
      current?.id === item.id ? { ...current, is_read: true } : current
    ));
  };

  const handleSelectNotification = (item) => {
    if (selectionMode) return;
    setSelectedNotification(item);
  };

  const handleDeleteNotification = async (item) => {
    const result = await alert.delete('this message');
    if (!result.isConfirmed) return;
    deleteOneMutation.mutate(item.id, {
      onSuccess: () => {
        setSelectedNotification(null);
        clearSelection();
      },
    });
  };

  const toggleNotifications = (event) => {
    event.stopPropagation();
    setShowDropdown(false);
    setShowNotifications((open) => !open);
  };

  const toggleUserMenu = (event) => {
    event.stopPropagation();
    setShowNotifications(false);
    setShowDropdown((open) => !open);
  };

  return (
    <header
      className="apex-navbar"
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        left: 'var(--apex-sidebar-current-width, 280px)',
        height: 64,
        background: 'var(--apex-surface)',
        borderBottom: '1px solid var(--apex-border)',
        zIndex: 1050,
        transition: 'left 0.25s',
        display: 'flex',
        alignItems: 'center',
        padding: '0 1.5rem',
        gap: '1rem',
        overflow: 'visible',
      }}
    >
      <button className="btn btn-link text-muted d-lg-none p-0" onClick={onMenuClick}>
        <FiMenu size={22} />
      </button>

      <div className={`d-none d-md-flex align-items-center flex-grow-1 ${suspended ? 'is-disabled-control' : ''}`} style={{ maxWidth: 480 }}>
        <GlobalSearch disabled={suspended} />
      </div>

      <div className="ms-auto d-flex align-items-center gap-2">
        {tenant && (
          <SchoolNameWithBadge
            name={tenant.name}
            planSlug={tenant.subscription?.plan_slug || user?.tenant_plan_slug}
            size="sm"
            className="d-none d-md-inline-flex text-muted small fw-medium"
          />
        )}

        <motion.button
          className={`btn btn-link text-muted p-2 ${suspended ? 'is-disabled-control' : ''}`}
          onClick={suspended ? undefined : toggleTheme}
          whileTap={suspended ? undefined : { scale: 0.9 }}
          title={suspended ? 'Unavailable while suspended' : 'Toggle theme'}
          disabled={suspended}
        >
          {theme === 'light' ? <FiMoon size={18} /> : <FiSun size={18} />}
        </motion.button>

        <div className={`position-relative ${suspended ? 'is-disabled-control' : ''}`} ref={notificationsRef}>
          <motion.button
            type="button"
            className="btn btn-link text-muted p-2 position-relative"
            onClick={suspended ? undefined : toggleNotifications}
            whileTap={suspended ? undefined : { scale: 0.9 }}
            title={suspended ? 'Notifications unavailable while suspended' : 'Notifications'}
            disabled={suspended}
            aria-expanded={showNotifications}
            aria-haspopup="true"
          >
            <FiBell size={18} />
            {(unreadCount > 0 || (isSchoolAdmin && pinnedItems.length > 0)) && (
              <span
                className="position-absolute top-0 end-0 badge rounded-pill"
                style={{ background: 'var(--apex-secondary)', fontSize: '0.55rem', padding: '2px 5px' }}
              >
                {unreadCount > 0 ? (unreadCount > 99 ? '99+' : unreadCount) : '•'}
              </span>
            )}
          </motion.button>
          {showNotifications && (
            <div className="apex-notifications-panel" role="menu">
              <div className="apex-notifications-panel-header">
                <div className="d-flex align-items-center gap-2">
                  <span className="fw-semibold small">Messages</span>
                  {unreadCount > 0 && (
                    <span className="badge bg-primary">{unreadCount} unread</span>
                  )}
                </div>
                {hasItems && selectedCount > 0 ? (
                  <NotificationBatchActions
                    count={selectedCount}
                    onMarkRead={() => batchMarkReadMutation.mutate()}
                    onDelete={handleBatchDelete}
                    onClear={clearSelection}
                    canMarkRead={canBatchMarkRead}
                    marking={batchMarkReadMutation.isPending}
                    deleting={batchDeleteMutation.isPending}
                    compact
                  />
                ) : hasItems && (
                  <div className="notification-panel-bulk-actions">
                    {unreadCount > 0 && (
                      <button
                        type="button"
                        className="btn btn-link btn-sm p-0 text-decoration-none"
                        onClick={() => markAllReadMutation.mutate()}
                        disabled={markAllReadMutation.isPending}
                      >
                        Mark all read
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn btn-link btn-sm p-0 text-decoration-none text-danger"
                      onClick={confirmDeleteAll}
                      disabled={deleteAllMutation.isPending}
                    >
                      Clear all
                    </button>
                  </div>
                )}
              </div>

              <NotificationCapacityWarning inbox={inbox} compact />

              <NotificationMessageList
                pinnedItems={pinnedItems}
                regularItems={regularItems}
                onSelect={handleSelectNotification}
                selectionMode={selectionMode}
                isSelected={isSelected}
                onToggleSelect={toggleSelection}
                onEnterSelection={enterSelection}
              />

              <div className="apex-notifications-panel-footer">
                <Link to={viewAllPath} className="small" onClick={() => setShowNotifications(false)}>
                  View all messages
                </Link>
              </div>
            </div>
          )}
        </div>

        <div className="position-relative" ref={userMenuRef}>
          <button
            type="button"
            className="apex-navbar-user-chip btn d-flex align-items-center gap-2"
            onClick={toggleUserMenu}
            aria-expanded={showDropdown}
            aria-haspopup="true"
          >
            <UserAvatar user={user} size={32} className="apex-navbar-user-avatar" />
            <span className="apex-navbar-user-name d-none d-md-inline">
              {user?.first_name} {user?.last_name}
            </span>
          </button>
          {showDropdown && (
            <div
              className="dropdown-menu show shadow-lg border-0"
              style={{ position: 'absolute', right: 0, top: '100%', minWidth: 200, borderRadius: 12 }}
            >
              <Link className="dropdown-item d-flex align-items-center gap-2" to={profilePath} onClick={() => setShowDropdown(false)}>
                <FiUser size={14} /> My Profile
              </Link>
              <Link className="dropdown-item d-flex align-items-center gap-2" to={settingsPath} onClick={() => setShowDropdown(false)}>
                <FiSettings size={14} /> Settings
              </Link>
              <hr className="dropdown-divider" />
              <button className="dropdown-item d-flex align-items-center gap-2 text-danger" onClick={async () => { await logout(); notify.info('You have been signed out.'); setShowDropdown(false); }}>
                <FiLogOut size={14} /> Logout
              </button>
            </div>
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
        marking={markReadMutation.isPending || markReadSchoolMutation.isPending}
        deleting={deleteOneMutation.isPending}
      />
    </header>
  );
}

export default Navbar;