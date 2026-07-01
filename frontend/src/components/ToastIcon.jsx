import {
  FiAlertCircle, FiAlertTriangle, FiCheckCircle, FiInfo, FiLoader,
} from 'react-icons/fi';

const ICONS = {
  success: FiCheckCircle,
  error: FiAlertCircle,
  warning: FiAlertTriangle,
  info: FiInfo,
  loading: FiLoader,
};

export function ToastIcon({ type = 'info', color }) {
  const Icon = ICONS[type] || FiInfo;
  return (
    <Icon
      size={20}
      color={color}
      className={type === 'loading' ? 'apex-toast-spin' : undefined}
      style={{ flexShrink: 0 }}
      aria-hidden
    />
  );
}

export function createToastIcon(type, color) {
  return <ToastIcon type={type} color={color} />;
}

export default ToastIcon;