/**
 * Apex brand loader — same orbit + breath + dots used on PDF print.
 * Use for module/data loads instead of Bootstrap spinner-border.
 */
export function ApexLoader({
  size = 'md',
  label = '',
  className = '',
  showDots = true,
}) {
  const sizeClass = size === 'sm' ? 'apex-loader--sm' : size === 'lg' ? 'apex-loader--lg' : '';
  return (
    <div
      className={`apex-loader ${sizeClass} ${className}`.trim()}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="apex-loader-orbit" aria-hidden>
        <span className="apex-loader-orbit-ring" />
        <span className="apex-loader-orbit-core" />
      </div>
      {showDots && (
        <div className="apex-loader-dots" aria-hidden>
          <span />
          <span />
          <span />
        </div>
      )}
      {label ? <p className="apex-loader-caption">{label}</p> : null}
      <span className="visually-hidden">{label || 'Loading'}</span>
    </div>
  );
}

/** Centered page/section loader for lists, workspaces, and module data. */
export function PageLoader({
  label = 'Loading…',
  size = 'md',
  className = '',
  compact = false,
}) {
  return (
    <div
      className={`apex-page-loader ${compact ? 'apex-page-loader--compact' : ''} ${className}`.trim()}
    >
      <ApexLoader size={size} label={label} />
    </div>
  );
}

/** Inline loader for buttons / tight UI slots. */
export function InlineLoader({ className = '', label = 'Loading' }) {
  return (
    <span className={`apex-loader apex-loader--inline ${className}`.trim()} role="status" aria-label={label}>
      <span className="apex-loader-orbit" aria-hidden>
        <span className="apex-loader-orbit-ring" />
        <span className="apex-loader-orbit-core" />
      </span>
      <span className="visually-hidden">{label}</span>
    </span>
  );
}

export default ApexLoader;
