import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  FiMenu, FiBell, FiSun, FiMoon, FiUser, FiSettings, FiLogOut, FiSearch,
  FiUserPlus, FiMail, FiCreditCard, FiInfo, FiAlertCircle, FiCheck,
} from 'react-icons/fi';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../hooks/useTheme';
import { useTenant } from '../hooks/useTenant';
import { notificationFeedService, platformNotificationsService } from '../services/moduleService';
import { notify } from '../utils/notify';

const TYPE_ICONS = {
  school_registration: FiUserPlus,
  trial_request: FiMail,
  payment_attempt: FiCreditCard,
  account_activation: FiCheck,
  info: FiInfo,
  warning: FiAlertCircle,
  success: FiCheck,
  error: FiAlertCircle,
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

export function Navbar({ onMenuClick, sidebarCollapsed }) {
  const { user, logout } = useAuth();
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
    queryKey: ['notification-feed'],
    queryFn: () => notificationFeedService.getFeed(),
    enabled: !!user,
    refetchInterval: 30000,
    staleTime: 15000,
  });

  const markReadMutation = useMutation({
    mutationFn: (id) => platformNotificationsService.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-feed'] });
      queryClient.invalidateQueries({ queryKey: ['platform-notifications-summary'] });
    },
  });

  const unreadCount = feed?.unread_count ?? 0;
  const items = feed?.items ?? [];
  const viewAllPath = feed?.view_all_url
    || (user?.role === 'super_admin' ? '/super-admin/notifications' : '/school-admin/notifications');

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (notificationsRef.current && !notificationsRef.current.contains(event.target)) {
        setShowNotifications(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleNotificationClick = (item) => {
    if (user?.role === 'super_admin' && item.id && !item.metadata?.synthetic) {
      markReadMutation.mutate(item.id);
    }
    setShowNotifications(false);
    if (item.action_url) {
      navigate(item.action_url);
    } else {
      navigate(viewAllPath);
    }
  };

  return (
    <header
      className="apex-navbar"
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        left: sidebarCollapsed ? 72 : 280,
        height: 64,
        background: 'var(--apex-surface)',
        borderBottom: '1px solid var(--apex-border)',
        zIndex: 1030,
        transition: 'left 0.25s',
        display: 'flex',
        alignItems: 'center',
        padding: '0 1.5rem',
        gap: '1rem',
      }}
    >
      <button className="btn btn-link text-muted d-lg-none p-0" onClick={onMenuClick}>
        <FiMenu size={22} />
      </button>

      <div className="d-none d-md-flex align-items-center flex-grow-1" style={{ maxWidth: 400 }}>
        <div className="position-relative w-100">
          <FiSearch className="position-absolute text-muted" style={{ left: 12, top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            className="form-control form-control-sm ps-5"
            placeholder="Search..."
            style={{ background: 'var(--apex-bg)', border: 'none', borderRadius: 10 }}
          />
        </div>
      </div>

      <div className="ms-auto d-flex align-items-center gap-2">
        {tenant && (
          <span className="d-none d-md-inline text-muted small fw-medium">
            {tenant.name}
          </span>
        )}

        <motion.button
          className="btn btn-link text-muted p-2"
          onClick={toggleTheme}
          whileTap={{ scale: 0.9 }}
          title="Toggle theme"
        >
          {theme === 'light' ? <FiMoon size={18} /> : <FiSun size={18} />}
        </motion.button>

        <div className="position-relative" ref={notificationsRef}>
          <motion.button
            className="btn btn-link text-muted p-2 position-relative"
            onClick={() => setShowNotifications(!showNotifications)}
            whileTap={{ scale: 0.9 }}
            title="Notifications"
          >
            <FiBell size={18} />
            {unreadCount > 0 && (
              <span
                className="position-absolute top-0 end-0 badge rounded-pill"
                style={{ background: 'var(--apex-secondary)', fontSize: '0.55rem', padding: '2px 5px' }}
              >
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </motion.button>
          {showNotifications && (
            <div
              className="dropdown-menu show shadow-lg border-0"
              style={{ position: 'absolute', right: 0, top: '100%', minWidth: 320, borderRadius: 12, maxHeight: 400, overflowY: 'auto' }}
            >
              <div className="px-3 py-2 border-bottom d-flex justify-content-between align-items-center">
                <span className="fw-semibold small">Notifications</span>
                {unreadCount > 0 && (
                  <span className="badge bg-primary">{unreadCount} unread</span>
                )}
              </div>
              {items.length === 0 ? (
                <div className="px-3 py-4 text-center text-muted small">No notifications</div>
              ) : (
                items.map((item) => {
                  const Icon = TYPE_ICONS[item.type] || FiInfo;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      className={`dropdown-item text-start py-2 px-3 border-0 ${!item.is_read ? 'bg-light' : ''}`}
                      onClick={() => handleNotificationClick(item)}
                    >
                      <div className="d-flex gap-2 align-items-start">
                        <Icon size={14} className="mt-1 flex-shrink-0" style={{ color: 'var(--apex-primary)' }} />
                        <div className="flex-grow-1 min-w-0">
                          <div className="d-flex justify-content-between gap-2">
                            <span className="fw-semibold small text-truncate">{item.title}</span>
                            <span className="text-muted flex-shrink-0" style={{ fontSize: '0.65rem' }}>
                              {formatRelativeTime(item.created_at)}
                            </span>
                          </div>
                          <div className="text-muted text-truncate" style={{ fontSize: '0.75rem' }}>
                            {item.message}
                          </div>
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
              <div className="px-3 py-2 border-top">
                <Link to={viewAllPath} className="small" onClick={() => setShowNotifications(false)}>
                  View all notifications
                </Link>
              </div>
            </div>
          )}
        </div>

        <div className="position-relative">
          <button
            className="btn d-flex align-items-center gap-2 p-1"
            onClick={() => setShowDropdown(!showDropdown)}
            style={{ borderRadius: 10 }}
          >
            <div
              className="d-flex align-items-center justify-content-center fw-bold text-white"
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: 'linear-gradient(135deg, var(--apex-primary), var(--apex-secondary))',
                fontSize: '0.8rem',
              }}
            >
              {user?.first_name?.[0]}{user?.last_name?.[0]}
            </div>
            <span className="d-none d-md-inline small fw-medium">
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