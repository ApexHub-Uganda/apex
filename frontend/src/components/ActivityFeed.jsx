import { motion } from 'framer-motion';
import { FiActivity, FiLogIn, FiUserPlus, FiSettings, FiAlertCircle } from 'react-icons/fi';

const ACTION_ICONS = {
  login: FiLogIn,
  create: FiUserPlus,
  update: FiSettings,
  delete: FiAlertCircle,
};

function formatRelativeTime(isoString) {
  if (!isoString) return '';
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function ActivityFeed({ items = [], emptyMessage = 'No recent activity' }) {
  if (!items.length) {
    return <p className="text-muted small mb-0">{emptyMessage}</p>;
  }

  return (
    <div className="d-flex flex-column gap-3">
      {items.map((item, index) => {
        const Icon = ACTION_ICONS[item.action] || FiActivity;
        return (
          <motion.div
            key={item.id || index}
            className="d-flex gap-3 align-items-start"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
          >
            <div
              className="d-flex align-items-center justify-content-center flex-shrink-0"
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: 'rgba(15, 118, 110, 0.1)',
                color: 'var(--apex-primary)',
              }}
            >
              <Icon size={16} />
            </div>
            <div className="flex-grow-1 min-w-0">
              <p className="mb-0 small fw-medium text-truncate">{item.description}</p>
              <p className="mb-0 text-muted" style={{ fontSize: '0.75rem' }}>
                {item.user} · {item.tenant} · {formatRelativeTime(item.time)}
              </p>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

export default ActivityFeed;