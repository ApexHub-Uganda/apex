import { motion } from 'framer-motion';

export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <motion.div
      className="apex-empty"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      {Icon && <Icon className="apex-empty-icon" />}
      <h5 className="fw-semibold mb-2">{title}</h5>
      {description && <p className="text-muted mb-3">{description}</p>}
      {action}
    </motion.div>
  );
}

export default EmptyState;