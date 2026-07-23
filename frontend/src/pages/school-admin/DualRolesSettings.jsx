import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FiArrowLeft, FiCheck, FiSearch, FiShield, FiUserCheck } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import { dualRolesService } from '../../services/authService';
import { getRoleLabel } from '../../config/schoolRoles';
import { alert, extractApiError, notify } from '../../utils/notify';
import { ApexLoader } from '../../components/ApexLoader';
import { useAuth } from '../../hooks/useAuth';

/**
 * School admin: grant dual portal roles to a single user (e.g. teacher + parent).
 * Already-held roles are shown disabled. Same login credentials are reused.
 */
export function DualRolesSettings() {
  const { isSchoolAdmin, isSuperAdmin } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedUserCache, setSelectedUserCache] = useState(null);
  const [selectedRoles, setSelectedRoles] = useState([]);

  const canManage = Boolean(isSchoolAdmin || isSuperAdmin);

  // Live search: debounce typing so results update without a Search button
  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedSearch(search.trim());
    }, 280);
    return () => window.clearTimeout(handle);
  }, [search]);

  const { data: roleOptions = [], isLoading: rolesLoading } = useQuery({
    queryKey: ['dual-roles', 'options'],
    queryFn: () => dualRolesService.options(),
    enabled: canManage,
    staleTime: 5 * 60 * 1000,
  });

  const { data: candidatesPayload, isLoading: candidatesLoading, isFetching } = useQuery({
    queryKey: ['dual-roles', 'candidates', debouncedSearch],
    queryFn: () => dualRolesService.candidates({ q: debouncedSearch || undefined }),
    enabled: canManage,
    staleTime: 10_000,
    placeholderData: (prev) => prev,
  });

  const candidates = candidatesPayload?.results || [];
  const selected = useMemo(() => {
    const fromList = candidates.find((u) => String(u.id) === String(selectedUserId));
    if (fromList) return fromList;
    if (selectedUserCache && String(selectedUserCache.id) === String(selectedUserId)) {
      return selectedUserCache;
    }
    return null;
  }, [candidates, selectedUserId, selectedUserCache]);

  const heldRoles = useMemo(
    () => new Set(selected?.available_roles || []),
    [selected],
  );

  const grantMutation = useMutation({
    mutationFn: () => {
      const payload = { roles: selectedRoles };
      if (selectedUserCache?.user_id) {
        payload.user_id = selectedUserCache.user_id;
      } else if (selectedUserCache?.source === 'parent' && selectedUserCache?.parent_id) {
        payload.parent_id = selectedUserCache.parent_id;
      } else if (selectedUserCache?.source === 'staff' && selectedUserCache?.staff_id) {
        payload.staff_id = selectedUserCache.staff_id;
      } else if (selectedUserId) {
        // Fallback for composite ids or plain user UUIDs
        payload.id = selectedUserId;
        if (!String(selectedUserId).includes(':')) {
          payload.user_id = selectedUserId;
        }
      }
      return dualRolesService.grant(payload);
    },
    onSuccess: (data) => {
      const msg = data?.message || 'Dual roles updated.';
      if (data?.temporary_password) {
        notify.success(msg);
        notify.info(`Temporary password: ${data.temporary_password}`);
      } else {
        notify.success(msg || 'Dual roles updated. Same login credentials apply.');
      }
      setSelectedRoles([]);
      if (data?.dual_role) {
        const nextId = data.user_id || data.dual_role?.user_id || selectedUserCache?.user_id;
        setSelectedUserCache({
          ...(selectedUserCache || {}),
          id: nextId || selectedUserCache?.id,
          user_id: nextId || selectedUserCache?.user_id,
          source: 'user',
          needs_portal_account: false,
          available_roles: data.dual_role.available_roles,
          active_role: data.dual_role.active_role,
          primary_role: data.dual_role.primary_role,
          role_labels: data.dual_role.role_labels,
          has_staff_profile: data.user ? Boolean(data.user.staff_profile) : selectedUserCache?.has_staff_profile,
          has_parent_profile: data.user ? Boolean(data.user.parent_profile) : selectedUserCache?.has_parent_profile,
        });
        if (nextId) setSelectedUserId(nextId);
      }
      queryClient.invalidateQueries({ queryKey: ['dual-roles', 'candidates'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to grant dual roles.')),
  });

  const revokeMutation = useMutation({
    mutationFn: (role) => dualRolesService.revoke({
      user_id: selectedUserCache?.user_id || selectedUserId,
      role,
    }),
    onSuccess: (data) => {
      notify.success(data?.message || 'Role removed.');
      if (data?.dual_role && selectedUserCache) {
        setSelectedUserCache({
          ...selectedUserCache,
          available_roles: data.dual_role.available_roles,
          active_role: data.dual_role.active_role,
          primary_role: data.dual_role.primary_role,
          role_labels: data.dual_role.role_labels,
        });
      }
      queryClient.invalidateQueries({ queryKey: ['dual-roles', 'candidates'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to remove role.')),
  });

  const toggleRole = (role) => {
    if (heldRoles.has(role)) return;
    setSelectedRoles((prev) => (
      prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role]
    ));
  };

  const selectUser = (u) => {
    setSelectedUserId(u.id);
    setSelectedUserCache(u);
    setSelectedRoles([]);
  };

  if (!canManage) {
    return (
      <div className="apex-card p-5">
        <h5 className="fw-bold">Dual roles</h5>
        <p className="text-muted mb-0">Only the school admin can configure dual portal roles.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3">
        <Link to="/school-admin/settings" className="small text-decoration-none text-muted">
          <FiArrowLeft className="me-1" /> School settings
        </Link>
      </div>

      <PageHeader
        title="Dual roles"
        subtitle="Let one person use the same login as both a staff member and a parent (or other portal roles). They switch roles from the avatar menu."
      />

      <div className="row g-4">
        <div className="col-lg-5">
          <div className="apex-card p-4 h-100">
            <h6 className="fw-semibold mb-1 d-flex align-items-center gap-2">
              <FiSearch size={16} /> Find school user
            </h6>
            <p className="text-muted small mb-3">
              Results update as you type. Search by name, email, or phone.
            </p>
            <div className="position-relative mb-3">
              <FiSearch
                size={14}
                className="text-muted position-absolute top-50 translate-middle-y"
                style={{ left: 12, pointerEvents: 'none' }}
              />
              <input
                className="form-control form-control-sm"
                style={{ paddingLeft: 34 }}
                placeholder="Start typing a name or email…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                autoComplete="off"
                autoFocus
              />
              {isFetching && !candidatesLoading && (
                <span
                  className="position-absolute top-50 translate-middle-y text-muted small"
                  style={{ right: 12 }}
                >
                  …
                </span>
              )}
            </div>

            {candidatesLoading && candidates.length === 0 ? (
              <div className="py-4 text-center"><ApexLoader label="Loading users…" /></div>
            ) : candidates.length === 0 ? (
              <p className="text-muted small mb-0">
                {debouncedSearch
                  ? `No users match “${debouncedSearch}”.`
                  : 'No users found for this school.'}
              </p>
            ) : (
              <div className="list-group list-group-flush border rounded dual-role-user-list" style={{ maxHeight: 420, overflowY: 'auto' }}>
                {candidates.map((u) => {
                  const isSelected = String(selectedUserId) === String(u.id);
                  return (
                    <button
                      key={u.id}
                      type="button"
                      className={`list-group-item list-group-item-action text-start dual-role-user-item ${isSelected ? 'is-selected' : ''}`}
                      onClick={() => selectUser(u)}
                    >
                      <div className="d-flex flex-wrap align-items-center gap-2">
                        <div className="fw-semibold dual-role-user-name">{u.full_name}</div>
                        {u.directory === 'parent' && (
                          <span className="dual-role-dir-tag dual-role-dir-tag--parent">Parent</span>
                        )}
                        {u.directory === 'staff' && (
                          <span className="dual-role-dir-tag dual-role-dir-tag--staff">Staff</span>
                        )}
                        {u.needs_portal_account && (
                          <span className="dual-role-dir-tag dual-role-dir-tag--pending">No login yet</span>
                        )}
                      </div>
                      <div className="small dual-role-user-meta">
                        {u.email || 'No email'}
                        {u.phone ? ` · ${u.phone}` : ''}
                      </div>
                      <div className="mt-1 d-flex flex-wrap gap-1">
                        {(u.available_roles || []).map((r) => (
                          <span key={r} className="dual-role-chip">
                            {u.role_labels?.[r] || getRoleLabel(r)}
                          </span>
                        ))}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
            {!debouncedSearch && candidates.length > 0 && (
              <p className="form-text mb-0 mt-2">Showing recent school users. Type to filter the list.</p>
            )}
          </div>
        </div>

        <div className="col-lg-7">
          <div className="apex-card p-4">
            <h6 className="fw-semibold mb-1 d-flex align-items-center gap-2">
              <FiUserCheck size={16} /> Configure dual roles
            </h6>
            {!selected ? (
              <p className="text-muted small mb-0 mt-2">
                Select a user from the search results to add or remove portal roles.
              </p>
            ) : (
              <>
                <div className="border rounded p-3 mb-3 bg-light-subtle">
                  <div className="fw-semibold">{selected.full_name}</div>
                  <div className="small text-muted">{selected.email || 'No email on record'}</div>
                  <div className="small mt-1">
                    Active role: <strong>{getRoleLabel(selected.active_role)}</strong>
                    {(selected.available_roles?.length || 0) > 1 && (
                      <span className="text-muted"> · can switch between {selected.available_roles.length} roles</span>
                    )}
                  </div>
                  <div className="small text-muted mt-1">
                    {selected.needs_portal_account
                      ? 'No portal login yet — granting a role will create one (temporary password shown once).'
                      : 'Same email & password — no new credentials when dual roles are added to an existing login.'}
                  </div>
                </div>

                <h6 className="small fw-semibold text-uppercase text-muted mb-2">Current roles</h6>
                <div className="d-flex flex-wrap gap-2 mb-4">
                  {(selected.available_roles || []).map((r) => (
                    <span key={r} className="dual-role-chip dual-role-chip--current d-inline-flex align-items-center gap-1">
                      {selected.role_labels?.[r] || getRoleLabel(r)}
                      {(selected.available_roles || []).length > 1 && (
                        <button
                          type="button"
                          className="dual-role-chip-remove"
                          title="Remove role"
                          disabled={revokeMutation.isPending}
                          onClick={async () => {
                            const ok = await alert.confirm({
                              title: 'Remove this role?',
                              text: `Remove “${selected.role_labels?.[r] || getRoleLabel(r)}” from ${selected.full_name}?`,
                              confirmText: 'Yes, remove',
                              cancelText: 'Keep',
                              icon: 'warning',
                              danger: true,
                            });
                            if (ok.isConfirmed) revokeMutation.mutate(r);
                          }}
                        >
                          ×
                        </button>
                      )}
                    </span>
                  ))}
                </div>

                <h6 className="small fw-semibold text-uppercase text-muted mb-2">
                  Add roles (already granted are greyed out)
                </h6>
                {rolesLoading ? (
                  <ApexLoader label="Loading roles…" />
                ) : (
                  <div className="row g-2 mb-3">
                    {(roleOptions || []).map((opt) => {
                      const held = heldRoles.has(opt.role);
                      const checked = held || selectedRoles.includes(opt.role);
                      return (
                        <div key={opt.role} className="col-sm-6">
                          <label
                            className={`d-flex align-items-center gap-2 border rounded px-3 py-2 mb-0 ${held ? 'bg-light text-muted' : 'bg-white'}`}
                            style={{ cursor: held ? 'not-allowed' : 'pointer', opacity: held ? 0.65 : 1 }}
                          >
                            <input
                              type="checkbox"
                              className="form-check-input mt-0"
                              disabled={held}
                              checked={checked}
                              onChange={() => toggleRole(opt.role)}
                            />
                            <span className="small fw-medium">{opt.label || getRoleLabel(opt.role)}</span>
                            {held && <span className="badge text-bg-secondary ms-auto">Assigned</span>}
                          </label>
                        </div>
                      );
                    })}
                  </div>
                )}

                <button
                  type="button"
                  className="btn btn-primary d-inline-flex align-items-center gap-2"
                  disabled={!selectedRoles.length || grantMutation.isPending}
                  onClick={() => grantMutation.mutate()}
                >
                  <FiCheck size={16} />
                  {grantMutation.isPending ? 'Saving…' : `Grant ${selectedRoles.length || ''} role(s)`}
                </button>
              </>
            )}
          </div>

          <div className="apex-card p-4 mt-3">
            <h6 className="fw-semibold mb-2 d-flex align-items-center gap-2">
              <FiShield size={16} /> How dual roles work
            </h6>
            <ul className="small text-muted mb-0 ps-3">
              <li className="mb-1">One account, one email, one password — never create a second login.</li>
              <li className="mb-1">Users with more than one role see <strong>Switch role</strong> under the avatar menu (above Logout).</li>
              <li className="mb-1">Dashboard menus and permissions follow the <strong>active</strong> role and your Permission Settings for that role.</li>
              <li>Granting <strong>Parent</strong> creates a linked parent profile if needed so the family portal can open.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DualRolesSettings;
