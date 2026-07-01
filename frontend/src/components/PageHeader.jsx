import { motion } from 'framer-motion';

export function PageHeader({ title, subtitle, actions, breadcrumbs }) {
  return (
    <motion.div
      className="apex-page-header d-flex flex-wrap justify-content-between align-items-start gap-3"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div>
        {breadcrumbs && (
          <nav className="mb-2">
            <ol className="breadcrumb mb-0 small">
              {breadcrumbs.map((crumb, i) => (
                <li key={i} className={`breadcrumb-item ${i === breadcrumbs.length - 1 ? 'active' : ''}`}>
                  {crumb.href ? <a href={crumb.href}>{crumb.label}</a> : crumb.label}
                </li>
              ))}
            </ol>
          </nav>
        )}
        <h1 className="apex-page-title">{title}</h1>
        {subtitle && <p className="apex-page-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="d-flex gap-2 flex-wrap">{actions}</div>}
    </motion.div>
  );
}

export default PageHeader;