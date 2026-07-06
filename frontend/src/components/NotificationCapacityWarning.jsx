export function NotificationCapacityWarning({ inbox, compact = false }) {
  if (!inbox?.show_warning) return null;

  const { count = 0, limit = 20, slots_remaining: slotsRemaining = 0 } = inbox;

  return (
    <div className={`notification-inbox-warning${compact ? ' notification-inbox-warning--compact' : ''}`} role="status">
      <div className="notification-inbox-warning-title">Inbox nearly full</div>
      <p className="notification-inbox-warning-text mb-0">
        {count} of {limit} messages stored.
        {slotsRemaining > 0
          ? ` When you reach ${limit}, the oldest messages are removed automatically.`
          : ` Your oldest messages will be removed as new ones arrive.`}
      </p>
    </div>
  );
}

export default NotificationCapacityWarning;