import { motion } from 'framer-motion';

export function Logo({ size = 40, showText = true, className = '' }) {
  return (
    <div className={`d-flex align-items-center gap-2 ${className}`}>
      <motion.div
        className="apex-logo-icon d-flex align-items-center justify-content-center"
        style={{
          width: size,
          height: size,
          borderRadius: size * 0.25,
          background: 'linear-gradient(135deg, var(--apex-primary), var(--apex-primary-light))',
          boxShadow: '0 4px 12px rgba(15, 118, 110, 0.3)',
        }}
        whileHover={{ scale: 1.05, rotate: 5 }}
        transition={{ type: 'spring', stiffness: 400 }}
      >
        <svg width={size * 0.55} height={size * 0.55} viewBox="0 0 24 24" fill="none">
          <path d="M12 2L20 7V17L12 22L4 17V7L12 2Z" stroke="#F5E6CA" strokeWidth="1.5" fill="none" />
          <path d="M12 8L16 10.5V15.5L12 18L8 15.5V10.5L12 8Z" fill="#FF7F50" />
        </svg>
      </motion.div>
      {showText && (
        <div className="apex-logo-text">
          <span
            className="fw-bold d-block lh-1"
            style={{ fontFamily: 'var(--apex-font-display)', fontSize: size * 0.38, color: 'var(--apex-text)' }}
          >
            Apex Hub
          </span>
          <span className="text-muted" style={{ fontSize: size * 0.22 }}>
            The Easy Way
          </span>
        </div>
      )}
    </div>
  );
}

export default Logo;