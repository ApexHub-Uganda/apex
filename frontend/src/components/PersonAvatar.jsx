import UserAvatar from './UserAvatar';

/** Avatar for student, staff, or parent list rows — uses photo/avatar URL or initials fallback. */
export function PersonAvatar({ person, size = 36, className = '' }) {
  if (!person) return null;

  const avatarUrl = person.avatar_url || person.photo_url || person.photo;
  const user = {
    first_name: person.first_name,
    last_name: person.last_name,
    email: person.email,
    avatar_url: avatarUrl,
    has_avatar: person.has_avatar ?? Boolean(avatarUrl),
  };

  return <UserAvatar user={user} size={size} className={className} />;
}

export function PersonNameCell({ row, nameField = 'full_name', compact = false }) {
  const name = row[nameField] || `${row.first_name || ''} ${row.last_name || ''}`.trim() || '—';
  return (
    <div className={`d-flex align-items-center apex-list-person-cell${compact ? ' apex-list-person-cell--compact' : ''}`}>
      <PersonAvatar person={row} size={compact ? 24 : 32} />
      <span className="fw-medium apex-list-person-name" title={name}>{name}</span>
    </div>
  );
}

export default PersonAvatar;