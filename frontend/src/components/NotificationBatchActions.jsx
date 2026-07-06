import { FiCheck, FiTrash2, FiX } from 'react-icons/fi';

export function NotificationBatchActions({
  count = 0,
  onMarkRead,
  onDelete,
  onClear,
  canMarkRead = false,
  marking = false,
  deleting = false,
  compact = false,
}) {
  if (!count) return null;

  return (
    <div className={`notification-batch-actions${compact ? ' notification-batch-actions--compact' : ''}`}>
      <span className="notification-batch-actions-count">
        {count} selected
      </span>
      <div className="notification-batch-actions-buttons">
        {canMarkRead && (
          <button
            type="button"
            className="btn btn-link btn-sm p-0 text-decoration-none"
            onClick={onMarkRead}
            disabled={marking || deleting}
          >
            <FiCheck size={14} className="me-1" />
            Mark read
          </button>
        )}
        <button
          type="button"
          className="btn btn-link btn-sm p-0 text-decoration-none text-danger"
          onClick={onDelete}
          disabled={marking || deleting}
        >
          <FiTrash2 size={14} className="me-1" />
          Delete
        </button>
        <button
          type="button"
          className="btn btn-link btn-sm p-0 text-decoration-none text-muted"
          onClick={onClear}
          disabled={marking || deleting}
          aria-label="Clear selection"
        >
          <FiX size={14} />
        </button>
      </div>
    </div>
  );
}

export default NotificationBatchActions;