import { useMemo, useState, useEffect } from 'react';

const getInitials = (user) => {
  const first = user?.first_name?.[0] || '';
  const last = user?.last_name?.[0] || '';
  const combined = `${first}${last}`.trim();
  if (combined) return combined.toUpperCase();
  const email = user?.email || '';
  return email.slice(0, 2).toUpperCase() || '?';
};

/**
 * Normalizes avatar URLs so media files route through the active origin / proxy.
 * If the backend generated an absolute localhost:8000 URL while the client is
 * on a Vite dev port (3000) or an HTTPS tunnel (e.g. ngrok), normalize to /media/...
 * to prevent mixed-content blocking and port mismatch.
 */
function normalizeAvatarUrl(url) {
  if (!url || typeof url !== 'string') return null;
  const match = url.match(/^https?:\/\/(?:localhost|127\.0\.0\.1):8000(\/media\/.*)$/i);
  if (match) {
    return match[1];
  }
  return url;
}

export function UserAvatar({
  user,
  size = 32,
  className = '',
  alt,
}) {
  const rawAvatarUrl = user?.avatar_url || user?.avatar;
  const avatarUrl = useMemo(() => normalizeAvatarUrl(rawAvatarUrl), [rawAvatarUrl]);
  const hasAvatar = user?.has_avatar ?? Boolean(avatarUrl);
  const initials = useMemo(() => getInitials(user), [user]);
  const [imgError, setImgError] = useState(false);

  // Reset error state whenever the avatar URL changes (e.g. after uploading a new image)
  useEffect(() => {
    setImgError(false);
  }, [avatarUrl]);

  const dimension = typeof size === 'number' ? `${size}px` : size;

  if (hasAvatar && avatarUrl && !imgError) {
    return (
      <img
        src={avatarUrl}
        alt={alt || `${user?.first_name || 'User'} profile`}
        className={`apex-user-avatar apex-user-avatar-image ${className}`.trim()}
        style={{ width: dimension, height: dimension }}
        onError={() => setImgError(true)}
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