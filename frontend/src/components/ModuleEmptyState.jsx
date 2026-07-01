import { Link } from 'react-router-dom';
import { FiInbox, FiPlus } from 'react-icons/fi';

export function ModuleEmptyState({
  title = 'Nothing here yet',
  message = 'No records have been created for this module. Add your first entry to get started.',
  actionLabel = 'Create first record',
  onAction,
  actionHref,
  icon: Icon = FiInbox,
}) {
  return (
    <div className="module-empty-state text-center py-5 px-4">
      <div className="module-empty-state-icon mx-auto mb-3">
        <Icon size={28} />
      </div>
      <h5 className="fw-bold mb-2">{title}</h5>
      <p className="text-muted small mb-4 mx-auto" style={{ maxWidth: 420 }}>{message}</p>
      {onAction && (
        <button type="button" className="btn btn-primary btn-sm d-inline-flex align-items-center gap-2" onClick={onAction}>
          <FiPlus size={14} /> {actionLabel}
        </button>
      )}
      {actionHref && !onAction && (
        <Link to={actionHref} className="btn btn-primary btn-sm d-inline-flex align-items-center gap-2">
          <FiPlus size={14} /> {actionLabel}
        </Link>
      )}
    </div>
  );
}

export default ModuleEmptyState;