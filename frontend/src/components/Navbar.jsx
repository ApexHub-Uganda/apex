import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import { FiBell, FiSun, FiMoon, FiUser, FiSettings, FiLogOut } from 'react-icons/fi';
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

/** Smooth professional popover enter/exit (top-right origin). */
const popoverTransition = {
  type: 'spring',
  stiffness: 420,
  damping: 32,
  mass: 0.75,
};

const popoverVariants = {
  hidden: {
    opacity: 0,
    y: -10,
    scale: 0.96,
    pointerEvents: 'none',
  },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    pointerEvents: 'auto',
    transition: popoverTransition,
  },
  exit: {
    opacity: 0,
    y: -8,
    scale: 0.97,
    pointerEvents: 'none',
    transition: { duration: 0.14, ease: [0.4, 0, 1, 1] },
  },
};

const menuListVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.035, delayChildren: 0.04 },
  },
};

const menuItemVariants = {
  hidden: { opacity: 0, x: 8 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.18, ease: [0.16, 1, 0.3, 1] },
  },
};

export function Navbar({
  onMenuClick,
  sidebarCollapsed,
  mobileMenuOpen = false,
  suspended = false,
}) {
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
  // School Settings is a school-admin-only surface (never for teachers/parents/etc.)
  const settingsPath = user?.role === 'super_admin'
    ? '/super-admin/settings'
    : '/school-admin/settings';
  const canOpenSettings = user?.role === 'super_admin' || isSchoolAdmin;

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
    // Opening a message is personal inbox state — never surface as a "write" failure
    onError: () => { /* silent; UI already shows as read optimistically */ },
  });

  const markReadSchoolMutation = useMutation({
    mutationFn: (id) => notificationsService.markRead(id),
    onSuccess: invalidateNotifications,
    onError: () => { /* silent; UI already shows as read optimistically */ },
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
    // Auto mark-as-read when opening from the bell (not a create/write operation)
    if (item && !item.is_read && canMarkReadItem(item)) {
      handleMarkReadItem(item);
    }
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
        overflow: 'visible',
      }}
    >
      <motion.button
        type="button"
        className={`btn btn-link text-muted d-lg-none p-0 apex-menu-toggle ${mobileMenuOpen ? 'is-open' : ''}`}
        onClick={onMenuClick}
        aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
        aria-expanded={mobileMenuOpen}
        whileTap={{ scale: 0.92 }}
        transition={{ type: 'spring', stiffness: 500, damping: 28 }}
      >
        <span className="apex-menu-toggle-bars" aria-hidden>
          <span />
          <span />
          <span />
        </span>
      </motion.button>

      <div className={`apex-navbar-search flex-grow-1 ${suspended ? 'is-disabled-control' : ''}`}>
        <GlobalSearch disabled={suspended} />
      </div>

      <div className="ms-auto d-flex align-items-center gap-1 gap-md-2 apex-navbar-actions">
        {tenant && (
          <SchoolNameWithBadge
            name={tenant.name}
            planSlug={tenant.subscription?.plan_slug || user?.tenant_plan_slug}
            size="sm"
            className="d-none d-lg-inline-flex text-muted small fw-medium"
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
          <AnimatePresence>
            {showNotifications && (
              <motion.div
                className="apex-notifications-panel"
                role="menu"
                variants={popoverVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                style={{ transformOrigin: 'top right' }}
              >
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
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="position-relative" ref={userMenuRef}>
          <motion.button
            type="button"
            className="apex-navbar-user-chip btn d-flex align-items-center gap-2"
            onClick={toggleUserMenu}
            aria-expanded={showDropdown}
            aria-haspopup="true"
            whileTap={{ scale: 0.97 }}
            transition={{ type: 'spring', stiffness: 500, damping: 30 }}
          >
            <UserAvatar user={user} size={32} className="apex-navbar-user-avatar" />
            <span className="apex-navbar-user-name d-none d-md-inline">
              {user?.first_name} {user?.last_name}
            </span>
          </motion.button>
          <AnimatePresence>
            {showDropdown && (
              <motion.div
                className="dropdown-menu show shadow-lg border-0 apex-user-menu"
                role="menu"
                variants={popoverVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                style={{
                  position: 'absolute',
                  right: 0,
                  top: 'calc(100% + 8px)',
                  minWidth: 200,
                  borderRadius: 12,
                  transformOrigin: 'top right',
                }}
              >
                <motion.div
                  variants={menuListVariants}
                  initial="hidden"
                  animate="visible"
                >
                  <motion.div variants={menuItemVariants}>
                    <Link
                      className="dropdown-item d-flex align-items-center gap-2"
                      to={profilePath}
                      onClick={() => setShowDropdown(false)}
                      role="menuitem"
                    >
                      <FiUser size={14} /> My Profile
                    </Link>
                  </motion.div>
                  {canOpenSettings && (
                    <motion.div variants={menuItemVariants}>
                      <Link
                        className="dropdown-item d-flex align-items-center gap-2"
                        to={settingsPath}
                        onClick={() => setShowDropdown(false)}
                        role="menuitem"
                      >
                        <FiSettings size={14} /> Settings
                      </Link>
                    </motion.div>
                  )}
                  <motion.div variants={menuItemVariants}>
                    <hr className="dropdown-divider" />
                  </motion.div>
                  <motion.div variants={menuItemVariants}>
                    <button
                      type="button"
                      className="dropdown-item d-flex align-items-center gap-2 text-danger"
                      role="menuitem"
                      onClick={async () => {
                        await logout();
                        notify.info('You have been signed out.');
                        setShowDropdown(false);
                      }}
                    >
                      <FiLogOut size={14} /> Logout
                    </button>
                  </motion.div>
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
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