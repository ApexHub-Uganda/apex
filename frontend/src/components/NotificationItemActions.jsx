import { FiCheck, FiTrash2 } from 'react-icons/fi';

export function NotificationItemActions({
  itemId,
  isRead = true,
  canMarkRead = false,
  onMarkRead,
  onDelete,
  deleting = false,
  marking = false,
  compact = false,
}) {
  const handleMarkRead = (event) => {
    event.preventDefault();
    event.stopPropagation();
    onMarkRead?.(itemId);
  };

  const handleDelete = (event) => {
    event.preventDefault();
    event.stopPropagation();
    onDelete?.(itemId);
  };

  return (
    <div className={`notification-item-actions ${compact ? 'is-compact' : ''}`}>
      {canMarkRead && !isRead && (
        <button
          type="button"
          className="notification-item-action"
          title="Mark as read"
          aria-label="Mark as read"
          onClick={handleMarkRead}
          disabled={marking}
        >
          <FiCheck size={14} />
        </button>
      )}
      <button
        type="button"
        className="notification-item-action notification-item-action--danger"
        title="Delete notification"
        aria-label="Delete notification"
        onClick={handleDelete}
        disabled={deleting}
      >
        <FiTrash2 size={14} />
      </button>
    </div>
  );
}

export default NotificationItemActions;