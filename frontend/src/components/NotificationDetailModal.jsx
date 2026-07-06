import { useEffect, useRef } from 'react';
import { FiCheck, FiTrash2 } from 'react-icons/fi';
import Modal from './Modal';
import PlanAdvertisementPreview from './PlanAdvertisementPreview';

const formatTimestamp = (value) => {
  if (!value) return '—';
  return new Date(value).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export function NotificationDetailModal({
  item,
  show,
  onHide,
  onMarkRead,
  onDelete,
  canMarkRead = false,
  marking = false,
  deleting = false,
}) {
  const markedOnOpenRef = useRef(null);

  useEffect(() => {
    if (!show) {
      markedOnOpenRef.current = null;
      return;
    }
    if (!item?.id || item.is_read || !canMarkRead) return;
    if (markedOnOpenRef.current === item.id) return;
    markedOnOpenRef.current = item.id;
    onMarkRead?.(item);
  }, [show, item, canMarkRead, onMarkRead]);

  if (!item) return null;

  const isAd = item.metadata?.advertisement || item.metadata?.pinned;

  return (
    <Modal
      show={show}
      onHide={onHide}
      title="Message"
      size="md"
      footer={(
        <div className="d-flex flex-wrap gap-2 justify-content-between w-100">
          <div className="d-flex flex-wrap gap-2">
            {canMarkRead && !item.is_read && (
              <button
                type="button"
                className="btn btn-outline-primary btn-sm d-inline-flex align-items-center gap-1"
                onClick={() => onMarkRead?.(item)}
                disabled={marking}
              >
                <FiCheck size={14} /> Mark as read
              </button>
            )}
          </div>
          <button
            type="button"
            className="btn btn-outline-danger btn-sm d-inline-flex align-items-center gap-1 ms-auto"
            onClick={() => onDelete?.(item)}
            disabled={deleting}
          >
            <FiTrash2 size={14} /> Delete
          </button>
        </div>
      )}
    >
      <div className="notification-detail">
        <div className="notification-detail-meta text-muted small mb-3">
          {formatTimestamp(item.created_at)}
          {!item.is_read && <span className="badge bg-primary-subtle text-primary ms-2">Unread</span>}
        </div>
        {isAd ? (
          <PlanAdvertisementPreview item={item} />
        ) : (
          <>
            <h6 className="fw-bold mb-2">{item.title}</h6>
            {item.metadata?.school_name && (
              <div className="text-muted small mb-2">{item.metadata.school_name}</div>
            )}
            <p className="notification-detail-body mb-0">{item.message}</p>
          </>
        )}
      </div>
    </Modal>
  );
}

export default NotificationDetailModal;