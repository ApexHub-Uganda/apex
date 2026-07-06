import { useMemo } from 'react';

const getInitials = (user) => {
  const first = user?.first_name?.[0] || '';
  const last = user?.last_name?.[0] || '';
  const combined = `${first}${last}`.trim();
  if (combined) return combined.toUpperCase();
  const email = user?.email || '';
  return email.slice(0, 2).toUpperCase() || '?';
};

export function UserAvatar({
  user,
  size = 32,
  className = '',
  alt,
}) {
  const avatarUrl = user?.avatar_url || user?.avatar;
  const hasAvatar = user?.has_avatar ?? Boolean(avatarUrl);
  const initials = useMemo(() => getInitials(user), [user]);

  const dimension = typeof size === 'number' ? `${size}px` : size;

  if (hasAvatar && avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt={alt || `${user?.first_name || 'User'} profile`}
        className={`apex-user-avatar apex-user-avatar-image ${className}`.trim()}
        style={{ width: dimension, height: dimension }}
      />
    );
  }

  return (
    <div
      className={`apex-user-avatar apex-user-avatar-initials ${className}`.trim()}
      style={{ width: dimension, height: dimension, fontSize: `calc(${typeof size === 'number' ? size : 32}px * 0.34)` }}
      aria-hidden={!alt}
      title={alt}
    >
      {initials}
    </div>
  );
}

export default UserAvatar;