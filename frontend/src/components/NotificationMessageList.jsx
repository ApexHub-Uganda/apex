import { useRef } from 'react';
import { FiInfo, FiAlertCircle, FiCheck, FiUserPlus, FiMail, FiCreditCard, FiLayers } from 'react-icons/fi';
import PlanAdvertisementPreview from './PlanAdvertisementPreview';
import { canSelectNotification } from '../utils/notificationInbox';

const TYPE_ICONS = {
  school_registration: FiUserPlus,
  trial_request: FiMail,
  payment_attempt: FiCreditCard,
  account_activation: FiCheck,
  info: FiInfo,
  warning: FiAlertCircle,
  success: FiCheck,
  error: FiAlertCircle,
  subscription: FiLayers,
};

const LONG_PRESS_MS = 500;

const formatRelativeTime = (value) => {
  if (!value) return '';
  const date = new Date(value);
  const diffMs = Date.now() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Now';
  if (diffMins < 60) return `${diffMins}m`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
};

const previewText = (message, max = 72) => {
  if (!message) return 'No message preview';
  const text = String(message).replace(/\s+/g, ' ').trim();
  return text.length > max ? `${text.slice(0, max)}…` : text;
};

export function NotificationMessageList({
  pinnedItems = [],
  regularItems = [],
  onSelect,
  emptyMessage = 'No messages yet',
  selectionMode = false,
  isSelected,
  onToggleSelect,
  onEnterSelection,
  enableSelection = true,
}) {
  const hasItems = pinnedItems.length > 0 || regularItems.length > 0;

  if (!hasItems) {
    return <div className="notification-message-empty">{emptyMessage}</div>;
  }

  const renderRow = (item, { pinned = false } = {}) => (
    <NotificationMessageRow
      key={item.id}
      item={item}
      pinned={pinned}
      onSelect={onSelect}
      selectionMode={selectionMode}
      isSelected={isSelected?.(item.id)}
      onToggleSelect={onToggleSelect}
      onEnterSelection={onEnterSelection}
      enableSelection={enableSelection && canSelectNotification(item)}
    />
  );

  return (
    <div className="notification-message-list">
      {pinnedItems.map((item) => renderRow(item, { pinned: true }))}
      {regularItems.map((item) => renderRow(item))}
    </div>
  );
}

function NotificationMessageRow({
  item,
  pinned = false,
  onSelect,
  selectionMode = false,
  isSelected = false,
  onToggleSelect,
  onEnterSelection,
  enableSelection = true,
}) {
  const Icon = TYPE_ICONS[item.type] || FiInfo;
  const isAd = item.metadata?.advertisement || item.metadata?.pinned;
  const longPressTimerRef = useRef(null);
  const longPressTriggeredRef = useRef(false);

  const clearLongPress = () => {
    if (longPressTimerRef.current) {
      clearTimeout(longPressTimerRef.current);
      longPressTimerRef.current = null;
    }
  };

  const handlePointerDown = (event) => {
    if (!enableSelection || event.button > 0) return;
    longPressTriggeredRef.current = false;
    clearLongPress();
    longPressTimerRef.current = setTimeout(() => {
      longPressTriggeredRef.current = true;
      onEnterSelection?.(item.id);
      if (typeof navigator !== 'undefined' && navigator.vibrate) {
        navigator.vibrate(12);
      }
    }, LONG_PRESS_MS);
  };

  const handlePointerUp = () => {
    clearLongPress();
  };

  const handlePointerLeave = () => {
    clearLongPress();
  };

  const handleOpen = () => {
    if (longPressTriggeredRef.current) {
      longPressTriggeredRef.current = false;
      return;
    }
    if (selectionMode && enableSelection) {
      onToggleSelect?.(item.id);
      return;
    }
    onSelect?.(item);
  };

  const handleCheckboxChange = (event) => {
    event.stopPropagation();
    onToggleSelect?.(item.id);
  };

  const handleCheckboxClick = (event) => {
    event.stopPropagation();
  };

  return (
    <div
      className={`notification-message-row-wrap${isSelected ? ' is-selected' : ''}${selectionMode ? ' is-selection-mode' : ''}`}
    >
      {enableSelection && (
        <label
          className="notification-message-checkbox"
          onClick={handleCheckboxClick}
          aria-label={isSelected ? 'Deselect message' : 'Select message'}
        >
          <input
            type="checkbox"
            className="form-check-input"
            checked={isSelected}
            onChange={handleCheckboxChange}
          />
        </label>
      )}
      <button
        type="button"
        className={`notification-message-row${!item.is_read ? ' is-unread' : ''}${pinned ? ' is-pinned' : ''}${isSelected ? ' is-selected' : ''}`}
        onClick={handleOpen}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerLeave}
        onPointerCancel={handlePointerLeave}
        onContextMenu={(event) => {
          if (!enableSelection) return;
          event.preventDefault();
          onEnterSelection?.(item.id);
        }}
      >
        <span className="notification-message-avatar" aria-hidden>
          <Icon size={16} />
        </span>
        <span className="notification-message-content">
          {isAd ? (
            <span className="notification-message-ad">
              <PlanAdvertisementPreview item={item} compact />
            </span>
          ) : (
            <>
              <span className="notification-message-top">
                <span className="notification-message-title">{item.title}</span>
                <span className="notification-message-time">{formatRelativeTime(item.created_at)}</span>
              </span>
              <span className="notification-message-preview">{previewText(item.message)}</span>
            </>
          )}
        </span>
        {!item.is_read && <span className="notification-message-unread-dot" aria-label="Unread" />}
      </button>
    </div>
  );
}

export default NotificationMessageList;