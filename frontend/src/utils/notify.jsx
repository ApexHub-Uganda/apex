import toast from 'react-hot-toast';
import Swal from 'sweetalert2';
import { createToastIcon } from '../components/ToastIcon';

const COLORS = {
  success: '#059669',
  info: '#2563eb',
  warning: '#d97706',
  error: '#dc2626',
};

const baseToast = {
  duration: 3800,
  style: {
    borderRadius: '12px',
    padding: '12px 16px',
    fontSize: '0.875rem',
    fontWeight: 500,
    boxShadow: '0 8px 24px rgba(15, 23, 42, 0.12)',
    maxWidth: '420px',
  },
};

const toastOpts = (type) => ({
  ...baseToast,
  icon: createToastIcon(type, COLORS[type]),
  iconTheme: {
    primary: 'transparent',
    secondary: COLORS[type],
  },
  style: {
    ...baseToast.style,
    border: `1px solid ${COLORS[type]}22`,
    background: 'var(--apex-surface, #fff)',
    color: 'var(--apex-text, #1e293b)',
  },
});

export function extractApiError(error, fallback = 'Something went wrong. Please try again.') {
  if (!error) return fallback;
  if (!error.response) {
    return 'Cannot reach the server. Check your connection and try again.';
  }
  const { data, headers } = error.response;
  const contentType = String(headers?.['content-type'] || '');
  if (
    (typeof data === 'string' && /^\s*</.test(data))
    || contentType.includes('text/html')
  ) {
    if (error.response.status >= 500) {
      return 'The server encountered an error while processing your request. Please try again shortly.';
    }
    return 'Received an unexpected response from the server. Ensure the API is running and reachable.';
  }
  const message =
    data?.error?.message ||
    data?.message ||
    data?.detail ||
    data?.non_field_errors?.[0] ||
    data?.error?.details?.non_field_errors?.[0] ||
    data?.admin_email?.[0] ||
    data?.email?.[0] ||
    data?.name?.[0] ||
    (typeof data === 'string' ? data : null);
  if (message) return String(message);
  if (data?.error?.details && typeof data.error.details === 'object') {
    const parts = Object.entries(data.error.details).flatMap(([k, v]) => {
      if (k === 'non_field_errors' && Array.isArray(v)) return v.map(String);
      if (Array.isArray(v)) return v.map((item) => `${k}: ${item}`);
      return [`${k}: ${v}`];
    });
    if (parts.length) return parts.join(' ');
  }
  return fallback;
}

export const notify = {
  success(message, options = {}) {
    return toast(message, { ...toastOpts('success'), ...options });
  },

  error(message, options = {}) {
    return toast(message, { ...toastOpts('error'), duration: 5000, ...options });
  },

  warning(message, options = {}) {
    return toast(message, { ...toastOpts('warning'), ...options });
  },

  info(message, options = {}) {
    return toast(message, { ...toastOpts('info'), ...options });
  },

  loading(message = 'Please wait...') {
    return toast.loading(message, {
      ...toastOpts('loading'),
      icon: createToastIcon('loading', COLORS.info),
      style: baseToast.style,
    });
  },

  dismiss(id) {
    toast.dismiss(id);
  },

  promise(promise, messages) {
    return toast.promise(promise, {
      loading: messages.loading || 'Working...',
      success: messages.success || 'Done',
      error: messages.error || 'Failed',
    }, {
      loading: {
        ...toastOpts('loading'),
        icon: createToastIcon('loading', COLORS.info),
      },
      success: toastOpts('success'),
      error: { ...toastOpts('error'), duration: 5000 },
    });
  },

  apiError(error, fallback) {
    return notify.error(extractApiError(error, fallback));
  },
};

const swalBase = Swal.mixin({
  customClass: {
    popup: 'apex-swal-popup',
    title: 'apex-swal-title',
    htmlContainer: 'apex-swal-text',
    confirmButton: 'apex-swal-btn apex-swal-confirm',
    cancelButton: 'apex-swal-btn apex-swal-cancel',
    denyButton: 'apex-swal-btn apex-swal-deny',
  },
  buttonsStyling: false,
  heightAuto: false,
  backdrop: 'rgba(15, 23, 42, 0.45)',
  showCloseButton: false,
});

export const alert = {
  /**
   * Non-blocking modal loader (SweetAlert2). Call alert.close() when done.
   * Does not await — fire-and-forget so the real work can start immediately.
   * Uses a light CSS animation (no extra JS timers).
   */
  loading({
    title = 'Please wait…',
    text = '',
  } = {}) {
    // Close any previous modal first so we never stack loaders
    if (Swal.isVisible()) {
      Swal.close();
    }
    const safeText = String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
    return swalBase.fire({
      title,
      html: `
        <div class="apex-loader" aria-hidden="true">
          <div class="apex-loader-orbit">
            <span class="apex-loader-orbit-ring"></span>
            <span class="apex-loader-orbit-core"></span>
          </div>
          <div class="apex-loader-dots">
            <span></span><span></span><span></span>
          </div>
        </div>
        ${safeText ? `<p class="apex-loader-caption">${safeText}</p>` : ''}
      `,
      allowOutsideClick: false,
      allowEscapeKey: false,
      showConfirmButton: false,
      showCancelButton: false,
      showDenyButton: false,
      focusConfirm: false,
      customClass: {
        popup: 'apex-swal-popup apex-swal-loading',
        title: 'apex-swal-title',
        htmlContainer: 'apex-swal-text apex-swal-loading-body',
      },
    });
  },

  /** Dismiss the current SweetAlert (loading or otherwise). Safe if none open. */
  close() {
    try {
      if (Swal.isVisible()) Swal.close();
    } catch {
      /* ignore */
    }
  },

  success(title, text = '') {
    return swalBase.fire({
      icon: 'success',
      iconColor: COLORS.success,
      title,
      text,
      confirmButtonText: 'OK',
      confirmButtonColor: COLORS.success,
    });
  },

  error(title, text = '') {
    return swalBase.fire({
      icon: 'error',
      iconColor: COLORS.error,
      title,
      text,
      confirmButtonText: 'OK',
      confirmButtonColor: COLORS.error,
    });
  },

  warning(title, text = '') {
    return swalBase.fire({
      icon: 'warning',
      iconColor: COLORS.warning,
      title,
      text,
      confirmButtonText: 'OK',
      confirmButtonColor: COLORS.warning,
    });
  },

  info(title, text = '') {
    return swalBase.fire({
      icon: 'info',
      iconColor: COLORS.info,
      title,
      text,
      confirmButtonText: 'OK',
      confirmButtonColor: COLORS.info,
    });
  },

  confirm({
    title = 'Are you sure?',
    text = '',
    confirmText = 'Yes, continue',
    cancelText = 'Cancel',
    icon = 'question',
    danger = false,
  } = {}) {
    return swalBase.fire({
      title,
      text,
      icon,
      iconColor: danger ? COLORS.error : COLORS.info,
      showCancelButton: true,
      confirmButtonText: confirmText,
      cancelButtonText: cancelText,
      reverseButtons: true,
      focusCancel: true,
      customClass: {
        popup: 'apex-swal-popup',
        title: 'apex-swal-title',
        htmlContainer: 'apex-swal-text',
        confirmButton: danger ? 'apex-swal-btn apex-swal-deny' : 'apex-swal-btn apex-swal-confirm',
        cancelButton: 'apex-swal-btn apex-swal-cancel',
      },
    });
  },

  delete(itemName = 'this record') {
    return alert.confirm({
      title: 'Delete confirmation',
      text: `Are you sure you want to delete ${itemName}? This action cannot be undone.`,
      confirmText: 'Yes, delete',
      cancelText: 'Keep it',
      icon: 'warning',
      danger: true,
    });
  },

  deletePlan({
    planName,
    subscriptionCount = 0,
    reassignOptions = [],
    suggestedReassignPlanId = null,
  } = {}) {
    if (!subscriptionCount) {
      return alert.delete(`plan "${planName}"`);
    }

    if (!reassignOptions.length) {
      return swalBase.fire({
        icon: 'error',
        iconColor: COLORS.error,
        title: 'Cannot delete plan',
        text: `"${planName}" is used by ${subscriptionCount} subscription(s). Create another active plan first, then try again.`,
        confirmButtonText: 'OK',
        confirmButtonColor: COLORS.error,
      });
    }

    const inputOptions = Object.fromEntries(
      reassignOptions.map((opt) => [opt.id, `${opt.name} (${opt.subscriber_count} schools)`]),
    );

    return swalBase.fire({
      title: 'Delete plan & move schools',
      html: `
        <p class="mb-2 text-start">
          <strong>${planName}</strong> is used by
          <strong>${subscriptionCount}</strong> subscription(s).
          Those schools must be moved to another plan before deletion.
        </p>
        <p class="mb-0 text-start small text-muted">
          Schools keep their subscription status. School admins are notified of the plan change.
        </p>
      `,
      icon: 'warning',
      iconColor: COLORS.warning,
      input: 'select',
      inputOptions,
      inputValue: suggestedReassignPlanId || reassignOptions[0]?.id || '',
      inputPlaceholder: 'Select replacement plan',
      inputValidator: (value) => (value ? undefined : 'Choose a replacement plan'),
      showCancelButton: true,
      confirmButtonText: 'Delete & move schools',
      cancelButtonText: 'Cancel',
      reverseButtons: true,
      focusCancel: true,
      customClass: {
        popup: 'apex-swal-popup',
        title: 'apex-swal-title',
        htmlContainer: 'apex-swal-text',
        confirmButton: 'apex-swal-btn apex-swal-deny',
        cancelButton: 'apex-swal-btn apex-swal-cancel',
      },
    });
  },
};

export default notify;