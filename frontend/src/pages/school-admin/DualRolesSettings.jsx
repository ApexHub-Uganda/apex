import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  /** Bumps after each successful grant/revoke so we never show stale list roles. */
  const roleStateEpoch = useRef(0);

  const canManage = Boolean(isSchoolAdmin || isSuperAdmin);

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
    staleTime: 0,
    // Do not keep previous list forever — stale roles caused "revoke twice" UX
    gcTime: 30_000,
  });

  const candidates = candidatesPayload?.results || [];

  const matchesSelected = useCallback((row, id) => {
    if (!row || id == null || id === '') return false;
    const sid = String(id);
    return String(row.id) === sid
      || (row.user_id != null && String(row.user_id) === sid);
  }, []);

  /**
   * selectedUserCache is authoritative for roles after grant/revoke.
   * Never fall back to stale candidates list for available_roles.
   */
  const selected = useMemo(() => {
    const fromList = candidates.find((u) => matchesSelected(u, selectedUserId));
    const cacheMatches = selectedUserCache && matchesSelected(selectedUserCache, selectedUserId);
    if (cacheMatches) {
      return {
        ...(fromList || {}),
        ...selectedUserCache,
        available_roles: Array.isArray(selectedUserCache.available_roles)
          ? selectedUserCache.available_roles
          : (fromList?.available_roles || []),
        active_role: selectedUserCache.active_role ?? fromList?.active_role,
        primary_role: selectedUserCache.primary_role ?? fromList?.primary_role,
        role_labels: selectedUserCache.role_labels ?? fromList?.role_labels ?? {},
        has_staff_profile: selectedUserCache.has_staff_profile ?? fromList?.has_staff_profile,
        has_parent_profile: selectedUserCache.has_parent_profile ?? fromList?.has_parent_profile,
        full_name: selectedUserCache.full_name || fromList?.full_name,
        email: selectedUserCache.email || fromList?.email,
      };
    }
    return fromList || null;
  }, [candidates, selectedUserId, selectedUserCache, matchesSelected]);

  const heldRoles = useMemo(
    () => new Set(selected?.available_roles || []),
    [selected],
  );

  const patchCandidatesWithRoleState = useCallback((patch) => {
    const targetIds = new Set(
      [patch.id, patch.user_id, selectedUserId, selectedUserCache?.id, selectedUserCache?.user_id]
        .filter((v) => v != null && v !== '')
        .map(String),
    );
    queryClient.setQueriesData({ queryKey: ['dual-roles', 'candidates'] }, (old) => {
      if (!old?.results) return old;
      let changed = false;
      const results = old.results.map((row) => {
        const hit = targetIds.has(String(row.id))
          || (row.user_id != null && targetIds.has(String(row.user_id)));
        if (!hit) return row;
        changed = true;
        return {
          ...row,
          available_roles: patch.available_roles ?? row.available_roles,
          active_role: patch.active_role ?? row.active_role,
          primary_role: patch.primary_role ?? row.primary_role,
          role_labels: patch.role_labels ?? row.role_labels,
          has_staff_profile: patch.has_staff_profile ?? row.has_staff_profile,
          has_parent_profile: patch.has_parent_profile ?? row.has_parent_profile,
          user_id: patch.user_id || row.user_id,
          source: patch.source || row.source,
          needs_portal_account: patch.needs_portal_account ?? row.needs_portal_account,
        };
      });
      return changed ? { ...old, results, count: results.length } : old;
    });
  }, [queryClient, selectedUserId, selectedUserCache?.id, selectedUserCache?.user_id]);

  const applyRoleStateUpdate = useCallback((data, { revokedRole = null } = {}) => {
    roleStateEpoch.current += 1;
    const dual = data?.dual_role;
    const nextId = data?.user_id || dual?.user_id || selectedUserCache?.user_id || selectedUserId;

    let available = dual?.available_roles ?? data?.available_roles;
    if (!Array.isArray(available)) {
      available = selectedUserCache?.available_roles || [];
    }
    // Always strip revoked role client-side (idempotent)
    if (revokedRole) {
      available = available.filter((r) => r !== revokedRole);
    }
    available = [...new Set(available.filter(Boolean))];

    const next = {
      ...(selectedUserCache || {}),
      id: nextId || selectedUserCache?.id,
      user_id: nextId || selectedUserCache?.user_id,
      source: 'user',
      needs_portal_account: false,
      available_roles: available,
      active_role: dual?.active_role ?? data?.active_role ?? selectedUserCache?.active_role,
      primary_role: dual?.primary_role ?? data?.primary_role ?? selectedUserCache?.primary_role,
      role_labels: dual?.role_labels || data?.role_labels || selectedUserCache?.role_labels || {},
      has_staff_profile: data?.identity?.has_staff_profile
        ?? (data?.user ? Boolean(data.user.staff_profile) : selectedUserCache?.has_staff_profile),
      has_parent_profile: data?.identity?.has_parent_profile
        ?? (data?.user ? Boolean(data.user.parent_profile) : selectedUserCache?.has_parent_profile),
      full_name: selectedUserCache?.full_name || data?.user?.full_name,
      email: selectedUserCache?.email || data?.user?.email,
      _epoch: roleStateEpoch.current,
    };

    setSelectedUserCache(next);
    if (nextId) setSelectedUserId(String(nextId));
    patchCandidatesWithRoleState(next);
    return next;
  }, [selectedUserCache, selectedUserId, patchCandidatesWithRoleState]);

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
        payload.id = selectedUserId;
        if (!String(selectedUserId).includes(':')) {
          payload.user_id = selectedUserId;
        }
      }
      return dualRolesService.grant(payload);
    },
    onSuccess: async (data) => {
      const msg = data?.message || 'Dual roles updated.';
      if (data?.temporary_password) {
        notify.success(msg);
        notify.info(`Temporary password: ${data.temporary_password}`);
      } else {
        notify.success(msg || 'Dual roles updated. Same login credentials apply.');
      }
      setSelectedRoles([]);
      applyRoleStateUpdate(data);
      await queryClient.invalidateQueries({ queryKey: ['dual-roles', 'candidates'] });
      queryClient.invalidateQueries({ queryKey: ['parents'] });
      queryClient.invalidateQueries({ queryKey: ['staff'] });
      queryClient.invalidateQueries({ queryKey: ['hr-staffs'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to grant dual roles.')),
  });

  const revokeMutation = useMutation({
    mutationFn: (role) => dualRolesService.revoke({
      user_id: selectedUserCache?.user_id || selectedUserId,
      role,
    }),
    onSuccess: async (data, role) => {
      notify.success(data?.message || 'Role removed.');
      // Immediate UI update — do not wait for list refetch
      applyRoleStateUpdate(data, { revokedRole: role });
      // Refetch server truth after paint
      await queryClient.invalidateQueries({ queryKey: ['dual-roles', 'candidates'] });
      queryClient.invalidateQueries({ queryKey: ['parents'] });
      queryClient.invalidateQueries({ queryKey: ['staff'] });
      queryClient.invalidateQueries({ queryKey: ['hr-staffs'] });
    },
    onError: (err) => notify.error(extractApiError(err, 'Unable to remove role.')),
  });

  const confirmRevokeRole = async (role) => {
    const userId = selectedUserCache?.user_id || selectedUserId;
    if (!userId || String(userId).includes(':')) {
      notify.error('Select a portal user before removing a role.');
      return;
    }
    const roleLabel = selected?.role_labels?.[role] || getRoleLabel(role);
    let impact = null;
    try {
      impact = await dualRolesService.revokePreview({ user_id: userId, role });
    } catch (err) {
      notify.error(extractApiError(err, 'Unable to preview role removal.'));
      return;
    }
    const cleanupLines = (impact?.cleanup || []).map((line) => `• ${line}`).join('\n');
    const warningLines = (impact?.warnings || []).map((line) => `• ${line}`).join('\n');
    const learnerHint = impact?.linked_students_count
      ? `\n\nLinked learners that will be unlinked (${impact.linked_students_count}):\n`
        + (impact.linked_students || []).slice(0, 8).map((s) => `• ${s.full_name} (${s.admission_number || '—'})`).join('\n')
        + (impact.linked_students_count > 8 ? `\n• +${impact.linked_students_count - 8} more` : '')
      : '';
    const ok = await alert.confirm({
      title: `Remove “${roleLabel}”?`,
      text: [
        `This person stays one account (${selected?.full_name || 'user'}). Only the “${roleLabel}” portal role is removed.`,
        cleanupLines ? `\nWhat will be cleaned up:\n${cleanupLines}` : '',
        warningLines ? `\nWarnings:\n${warningLines}` : '',
        learnerHint,
        '\n\nThis cannot be undone without re-granting the role.',
      ].filter(Boolean).join(''),
      confirmText: 'Yes, remove role',
      cancelText: 'Keep role',
      icon: 'warning',
      danger: true,
    });
    // SweetAlert2 returns { isConfirmed, isDenied, isDismissed }
    if (ok?.isConfirmed) {
      revokeMutation.mutate(role);
    }
  };

  const toggleRole = (role) => {
    if (heldRoles.has(role)) return;
    setSelectedRoles((prev) => (
      prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role]
    ));
  };

  const selectUser = (u) => {
    setSelectedUserId(u.id);
    setSelectedUserCache({
      ...u,
      available_roles: [...(u.available_roles || [])],
      role_labels: { ...(u.role_labels || {}) },
    });
    setSelectedRoles([]);
  };

  // When candidates refetch, merge server roles into cache only if same user
  // and we are not mid-stale (prefer server after invalidate).
  useEffect(() => {
    if (!selectedUserCache || !selectedUserId) return;
    const fromList = candidates.find((u) => matchesSelected(u, selectedUserId));
    if (!fromList?.available_roles) return;
    // If cache epoch was just set by mutation, still accept server if it agrees
    // on revoked roles (server is shorter or equal).
    const cacheRoles = selectedUserCache.available_roles || [];
    const listRoles = fromList.available_roles || [];
    const same = cacheRoles.length === listRoles.length
      && cacheRoles.every((r) => listRoles.includes(r));
    if (same) return;
    // Prefer fewer roles from server (successful revoke) over stale longer cache
    // only when server is a subset or equal length and matches selection.
    if (listRoles.length <= cacheRoles.length) {
      setSelectedUserCache((prev) => {
        if (!prev || !matchesSelected(prev, selectedUserId)) return prev;
        return {
          ...prev,
          ...fromList,
          available_roles: listRoles,
          active_role: fromList.active_role ?? prev.active_role,
          primary_role: fromList.primary_role ?? prev.primary_role,
          role_labels: fromList.role_labels ?? prev.role_labels,
          has_staff_profile: fromList.has_staff_profile ?? prev.has_staff_profile,
          has_parent_profile: fromList.has_parent_profile ?? prev.has_parent_profile,
        };
      });
    }
  }, [candidates, selectedUserId, selectedUserCache, matchesSelected]);

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
                  const isSelected = matchesSelected(u, selectedUserId);
                  // Prefer live cache chips when this row is selected
                  const roles = isSelected && selectedUserCache?.available_roles
                    ? selectedUserCache.available_roles
                    : (u.available_roles || []);
                  const labels = isSelected && selectedUserCache?.role_labels
                    ? selectedUserCache.role_labels
                    : (u.role_labels || {});
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
                        {roles.map((r) => (
                          <span key={r} className="dual-role-chip">
                            {labels?.[r] || getRoleLabel(r)}
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
                          title="Remove role and clean up directory links"
                          disabled={revokeMutation.isPending}
                          onClick={() => confirmRevokeRole(r)}
                        >
                          ×
                        </button>
                      )}
                    </span>
                  ))}
                  {(selected.available_roles || []).length === 0 && (
                    <span className="text-muted small">No roles assigned.</span>
                  )}
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
              <li className="mb-1">The same person appears in <strong>Staff</strong> and/or <strong>Parents</strong> lists for every role they hold (still one person in the database).</li>
              <li className="mb-1">Users with more than one role see <strong>Switch role</strong> under the avatar menu (above Logout).</li>
              <li className="mb-1">My Profile spans <strong>all</strong> roles (employment + parent contact) so they can complete every required section.</li>
              <li className="mb-1">Dashboard menus and permissions follow the <strong>active</strong> role and your Permission Settings for that role.</li>
              <li>Removing a role is a single step — it cleans up that role&apos;s directory record and links (with a clear warning first).</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DualRolesSettings;
