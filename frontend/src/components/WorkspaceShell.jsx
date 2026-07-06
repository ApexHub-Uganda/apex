import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FiArrowLeft } from 'react-icons/fi';

/**
 * Full-page minimal workspace layout (replaces modal forms for complex flows).
 */
export function WorkspaceShell({
  backTo,
  backLabel = 'Back',
  title,
  subtitle,
  actions,
  children,
  className = '',
}) {
  return (
    <div className={`apex-workspace ${className}`.trim()}>
      <motion.div
        className="apex-workspace-topbar apex-card"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="apex-workspace-topbar-main">
          {backTo && (
            <Link to={backTo} className="apex-workspace-back">
              <FiArrowLeft size={16} />
              {backLabel}
            </Link>
          )}
          <div>
            <h1 className="apex-workspace-title">{title}</h1>
            {subtitle && <p className="apex-workspace-subtitle">{subtitle}</p>}
          </div>
        </div>
        {actions && <div className="apex-workspace-topbar-actions">{actions}</div>}
      </motion.div>

      <motion.div
        className="apex-workspace-body"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
      >
        {children}
      </motion.div>
    </div>
  );
}

export function WorkspaceSection({ title, description, icon: Icon, children, className = '' }) {
  return (
    <section className={`apex-workspace-section apex-card ${className}`.trim()}>
      {(title || description) && (
        <header className="apex-workspace-section-header">
          {Icon && <span className="apex-workspace-section-icon"><Icon size={18} /></span>}
          <div>
            {title && <h2 className="apex-workspace-section-title">{title}</h2>}
            {description && <p className="apex-workspace-section-desc">{description}</p>}
          </div>
        </header>
      )}
      <div className="apex-workspace-section-body">{children}</div>
    </section>
  );
}

export function WorkspaceFieldGrid({ children }) {
  return <div className="row g-3">{children}</div>;
}

export function ReadOnlyField({ label, value, hint }) {
  return (
    <div className="col-md-6">
      <label className="form-label small text-muted mb-1">{label}</label>
      <div className="apex-readonly-field">{value || '—'}</div>
      {hint && <div className="form-text">{hint}</div>}
    </div>
  );
}

export default WorkspaceShell;