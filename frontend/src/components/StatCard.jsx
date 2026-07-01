import { motion } from 'framer-motion';
import { FiTrendingUp, FiTrendingDown } from 'react-icons/fi';

export function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  trendLabel,
  color = 'primary',
  delay = 0,
  suffix = '',
  prefix = '',
}) {
  const colorMap = {
    primary: { bg: 'rgba(15, 118, 110, 0.1)', icon: 'var(--apex-primary)' },
    secondary: { bg: 'rgba(255, 127, 80, 0.1)', icon: 'var(--apex-secondary)' },
    accent: { bg: 'rgba(245, 230, 202, 0.3)', icon: 'var(--apex-primary-dark)' },
    success: { bg: 'rgba(16, 185, 129, 0.1)', icon: '#059669' },
    warning: { bg: 'rgba(245, 158, 11, 0.1)', icon: '#D97706' },
  };

  const colors = colorMap[color] || colorMap.primary;
  const isPositive = trend >= 0;

  return (
    <motion.div
      className="apex-stat-card apex-card p-4 h-100"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      whileHover={{ y: -4 }}
    >
      <div className="d-flex justify-content-between align-items-start mb-3">
        <div
          className="d-flex align-items-center justify-content-center"
          style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            background: colors.bg,
            color: colors.icon,
            fontSize: '1.25rem',
          }}
        >
          {Icon && <Icon />}
        </div>
        {trend !== undefined && (
          <span
            className={`d-flex align-items-center gap-1 small fw-semibold ${isPositive ? 'text-success' : 'text-danger'}`}
          >
            {isPositive ? <FiTrendingUp /> : <FiTrendingDown />}
            {Math.abs(trend)}%
          </span>
        )}
      </div>
      <p className="text-muted small mb-1 fw-medium">{title}</p>
      <h3 className="mb-0 fw-bold" style={{ fontSize: '1.75rem' }}>
        {prefix}
        {typeof value === 'number' ? value.toLocaleString() : value}
        {suffix}
      </h3>
      {trendLabel && <p className="text-muted small mb-0 mt-1">{trendLabel}</p>}
    </motion.div>
  );
}

export default StatCard;