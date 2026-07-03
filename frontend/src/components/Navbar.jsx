import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  FiMenu, FiBell, FiSun, FiMoon, FiUser, FiSettings, FiLogOut, FiSearch,
  FiUserPlus, FiMail, FiCreditCard, FiInfo, FiAlertCircle, FiCheck, FiLayers,
} from 'react-icons/fi';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../hooks/useTheme';
import { useTenant } from '../hooks/useTenant';
import { notificationFeedService, platformNotificationsService } from '../services/moduleService';
import { notify } from '../utils/notify';
import PlanAdvertisementPreview from './PlanAdvertisementPreview';
import NotificationItemActions from './NotificationItemActions';
import SchoolNameWithBadge from './SchoolNameWithBadge';
import { extractApiError } from '../utils/notify';

const TYPE_ICONS = {
  school_registration: FiUserPlus,
  trial_request: FiMail,
  payment_attempt: FiCreditCard,
  account_activation: FiCheck,
  info: FiInfo,
  warning: FiAlertCircle,
  success: FiCheck,
  error: FiAlertCircle,
  subscription: FiLayers,
};

const formatRelativeTime = (value) => {
  if (!value) return '';
  const date = new Date(value);
  const diffMs = Date.now() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
};

export function Navbar({ onMenuClick, sidebarCollapsed, suspended = false }) {
  const { user, logout, isSchoolAdmin } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { tenant } = useTenant();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showDropdown, setShowDropdown] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const notificationsRef = useRef(null);

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

  const unreadCount = feed?.unread_count ?? 0;
  const feedItems = feed?.items ?? [];

  const items = feedItems;
  const pinnedItems = items.filter((item) => item.metadata?.pinned || item.metadata?.advertisement);
  const regularItems = items.filter((item) => !item.metadata?.pinned && !item.metadata?.advertisement);
  const hasItems = pinnedItems.length > 0 || regularItems.length > 0;

  const viewAllPath = feed?.view_all_url
    || (user?.role === 'super_admin' ? '/super-admin/notifications' : '/school-admin/notifications');

  useEffect(() => {
    if (!showNotifications) return undefined;

    const handleClickOutside = (event) => {
      if (notificationsRef.current?.contains(event.target)) return;
      setShowNotifications(false);
    };

    const timer = window.setTimeout(() => {
      document.addEventListener('click', handleClickOutside);
    }, 0);

    return () => {
      window.clearTimeout(timer);
      document.removeEventListener('click', handleClickOutside);
    };
  }, [showNotifications]);

  const handleNotificationClick = (item) => {
    if (user?.role === 'super_admin' && item.id && !item.metadata?.synthetic) {
      markReadMutation.mutate(item.id);
    }
    setShowNotifications(false);
    if (item.action_url) {
      navigate(item.action_url);
      return;
    }
    navigate(viewAllPath);
  };

  const toggleNotifications = (event) => {
    event.stopPropagation();
    setShowDropdown(false);
    setShowNotifications((open) => !open);
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

      <div className={`d-none d-md-flex align-items-center flex-grow-1 ${suspended ? 'is-disabled-control' : ''}`} style={{ maxWidth: 400 }}>
        <div className="position-relative w-100">
          <FiSearch className="position-absolute text-muted" style={{ left: 12, top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            className="form-control form-control-sm ps-5"
            placeholder={suspended ? 'Search unavailable while suspended' : 'Search...'}
            disabled={suspended}
            style={{ background: 'var(--apex-bg)', border: 'none', borderRadius: 10 }}
          />
        </div>
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
                  <span className="fw-semibold small">Notifications</span>
                  {unreadCount > 0 && (
                    <span className="badge bg-primary">{unreadCount} unread</span>
                  )}
                </div>
                {hasItems && (
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
                      onClick={() => deleteAllMutation.mutate()}
                      disabled={deleteAllMutation.isPending}
                    >
                      Clear all
                    </button>
                  </div>
                )}
              </div>

              {pinnedItems.map((item) => (
                <div key={item.id} className="apex-notifications-pinned-wrap">
                  <button
                    type="button"
                    className="apex-notifications-pinned"
                    onClick={() => handleNotificationClick(item)}
                  >
                    <PlanAdvertisementPreview item={item} compact />
                  </button>
                  <NotificationItemActions
                    itemId={item.id}
                    isRead={item.is_read}
                    onDelete={(id) => deleteOneMutation.mutate(id)}
                    deleting={deleteOneMutation.isPending}
                    compact
                  />
                </div>
              ))}

              {!hasItems ? (
                <div className="apex-notifications-empty">No notifications yet</div>
              ) : (
                regularItems.map((item) => {
                  const Icon = TYPE_ICONS[item.type] || FiInfo;
                  const isSuperAdminItem = user?.role === 'super_admin' && !item.metadata?.synthetic;
                  return (
                    <div
                      key={item.id}
                      className={`apex-notifications-item-wrap ${!item.is_read ? 'is-unread' : ''}`}
                    >
                      <button
                        type="button"
                        className="apex-notifications-item"
                        onClick={() => handleNotificationClick(item)}
                      >
                        <div className="d-flex gap-2 align-items-start">
                          <Icon size={14} className="mt-1 flex-shrink-0" style={{ color: 'var(--apex-primary)' }} />
                          <div className="flex-grow-1 min-w-0 text-start">
                            <div className="d-flex justify-content-between gap-2">
                              <span className="fw-semibold small">{item.title}</span>
                              <span className="text-muted flex-shrink-0" style={{ fontSize: '0.65rem' }}>
                                {formatRelativeTime(item.created_at)}
                              </span>
                            </div>
                            <div className="apex-notifications-message text-muted">{item.message}</div>
                          </div>
                        </div>
                      </button>
                      <NotificationItemActions
                        itemId={item.id}
                        isRead={item.is_read}
                        canMarkRead={isSuperAdminItem}
                        onMarkRead={(id) => markReadMutation.mutate(id)}
                        onDelete={(id) => deleteOneMutation.mutate(id)}
                        deleting={deleteOneMutation.isPending}
                        marking={markReadMutation.isPending}
                        compact
                      />
                    </div>
                  );
                })
              )}

              <div className="apex-notifications-panel-footer">
                <Link to={viewAllPath} className="small" onClick={() => setShowNotifications(false)}>
                  View all notifications
                </Link>
              </div>
            </div>
          )}
        </div>

        <div className="position-relative">
          <button
            type="button"
            className="apex-navbar-user-chip btn d-flex align-items-center gap-2"
            onClick={() => setShowDropdown(!showDropdown)}
            aria-expanded={showDropdown}
            aria-haspopup="true"
          >
            <div className="apex-navbar-user-avatar">
              {user?.first_name?.[0]}{user?.last_name?.[0]}
            </div>
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
                <FiUser size={14} /> Profile
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
    </header>
  );
}

export default Navbar;