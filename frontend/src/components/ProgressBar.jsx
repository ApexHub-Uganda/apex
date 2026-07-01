import { motion } from 'framer-motion';

export function ProgressBar({ value, max = 100, label, showValue = true, color, height = 8 }) {
  const percent = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div>
      {(label || showValue) && (
        <div className="d-flex justify-content-between mb-1">
          {label && <span className="small fw-medium">{label}</span>}
          {showValue && <span className="small text-muted">{percent.toFixed(0)}%</span>}
        </div>
      )}
      <div className="apex-progress" style={{ height }}>
        <motion.div
          className="apex-progress-bar"
          style={color ? { background: color } : undefined}
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

export default ProgressBar;