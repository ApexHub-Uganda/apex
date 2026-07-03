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
  const { data } = error.response;
  const message =
    data?.error?.message ||
    data?.message ||
    data?.detail ||
    data?.non_field_errors?.[0] ||
    data?.error?.details?.non_field_errors?.[0] ||
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
});

export const alert = {
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
};

export default notify;