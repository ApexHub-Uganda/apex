import { motion } from 'framer-motion';

export function Skeleton({ width, height = 16, className = '', rounded = 8 }) {
  return (
    <motion.div
      className={`skeleton-pulse ${className}`}
      style={{
        width: width || '100%',
        height,
        borderRadius: rounded,
        background: 'linear-gradient(90deg, var(--apex-border) 25%, var(--apex-bg) 50%, var(--apex-border) 75%)',
        backgroundSize: '200% 100%',
      }}
      animate={{ backgroundPosition: ['200% 0', '-200% 0'] }}
      transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
    />
  );
}

export function StatCardSkeleton() {
  return (
    <div className="apex-stat-card p-4">
      <Skeleton width={40} height={40} rounded={10} className="mb-3" />
      <Skeleton width="60%" height={12} className="mb-2" />
      <Skeleton width="40%" height={28} />
    </div>
  );
}

export function TableSkeleton({ rows = 5, cols = 5 }) {
  return (
    <div className="apex-card p-0 overflow-hidden">
      <div className="p-3 border-bottom">
        <Skeleton width="30%" height={20} />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="d-flex gap-3 p-3 border-bottom">
          {Array.from({ length: cols }).map((_, j) => (
            <Skeleton key={j} width={`${100 / cols}%`} height={14} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div>
      <Skeleton width="250px" height={32} className="mb-2" />
      <Skeleton width="400px" height={16} className="mb-4" />
      <div className="row g-3 mb-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="col-md-3">
            <StatCardSkeleton />
          </div>
        ))}
      </div>
      <TableSkeleton />
    </div>
  );
}

export function CardSkeleton({ lines = 3 }) {
  return (
    <div className="apex-card p-4">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} width={i === lines - 1 ? '60%' : '100%'} height={14} className="mb-2" />
      ))}
    </div>
  );
}

const LoadingSkeleton = { Skeleton, StatCardSkeleton, TableSkeleton, PageSkeleton, CardSkeleton };
export default LoadingSkeleton;