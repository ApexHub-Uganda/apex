export function StatusBadge({ status, label: customLabel }) {
  const config = {
    active: { class: 'apex-badge-success', label: 'Active' },
    inactive: { class: 'apex-badge-danger', label: 'Inactive' },
    trial: { class: 'apex-badge-info', label: 'Trial' },
    grace_period: { class: 'apex-badge-warning', label: 'Grace Period' },
    suspended: { class: 'apex-badge-warning', label: 'Suspended' },
    pending: { class: 'apex-badge-warning', label: 'Pending' },
    approved: { class: 'apex-badge-success', label: 'Approved' },
    dismissed: { class: 'apex-badge-danger', label: 'Dismissed' },
    expired: { class: 'apex-badge-danger', label: 'Expired' },
    none: { class: 'apex-badge-info', label: 'None' },
    paid: { class: 'apex-badge-success', label: 'Paid' },
    overdue: { class: 'apex-badge-danger', label: 'Overdue' },
    healthy: { class: 'apex-badge-success', label: 'Healthy' },
    connected: { class: 'apex-badge-success', label: 'Connected' },
  };

  const { class: badgeClass, label } = config[status?.toLowerCase()] || {
    class: 'apex-badge-info',
    label: status || 'Unknown',
  };

  return <span className={`apex-badge ${badgeClass}`}>{customLabel || label}</span>;
}

export default StatusBadge;