import { useCallback, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { FiRefreshCw, FiSave, FiShield } from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import { tenantService } from '../../services/tenantService';
import { notify } from '../../utils/notify';
import { resolveFeatureIcon } from '../../utils/featureIcons';

function PermissionCell({ value, onChange, disabled, type }) {
  return (
    <label className={`permission-matrix-cell permission-matrix-cell--${type}`}>
      <input
        type="checkbox"
        className="form-check-input"
        checked={Boolean(value)}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
    </label>
  );
}

export function PermissionSettings() {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState(null);
  const [activeRole, setActiveRole] = useState(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['tenant', 'role-permissions'],
    queryFn: () => tenantService.getRolePermissionMatrix(),
  });

  const matrix = draft || data?.matrix || {};
  const roles = data?.roles || [];
  const modules = data?.modules || [];

  const selectedRole = activeRole || roles[0]?.key || null;

  const { mutate: saveMatrix, isPending: saving } = useMutation({
    mutationFn: (permissions) => tenantService.saveRolePermissions(permissions),
    onSuccess: (result) => {
      setDraft(null);
      queryClient.setQueryData(['tenant', 'role-permissions'], result);
      queryClient.invalidateQueries({ queryKey: ['tenant', 'context'] });
      notify.success('Permission settings saved.');
    },
    onError: (err) => {
      notify.error(err?.response?.data?.error?.message || 'Failed to save permissions.');
    },
  });

  const { mutate: resetRole, isPending: resetting } = useMutation({
    mutationFn: (role) => tenantService.resetRolePermissions(role),
    onSuccess: (result) => {
      setDraft(null);
      queryClient.setQueryData(['tenant', 'role-permissions'], result);
      queryClient.invalidateQueries({ queryKey: ['tenant', 'context'] });
      notify.success('Role permissions reset to defaults.');
    },
    onError: () => notify.error('Failed to reset permissions.'),
  });

  const updateCell = useCallback((role, moduleKey, field, value) => {
    setDraft((prev) => {
      const base = prev || data?.matrix || {};
      const roleRow = { ...(base[role] || {}) };
      const cell = { ...(roleRow[moduleKey] || {}) };
      if (field === 'can_write' && value) {
        cell.can_read = true;
        cell.can_write = true;
      } else if (field === 'can_read' && !value) {
        cell.can_read = false;
        cell.can_write = false;
      } else {
        cell[field] = value;
      }
      cell.is_custom = true;
      roleRow[moduleKey] = cell;
      return { ...base, [role]: roleRow };
    });
  }, [data?.matrix]);

  const dirtyPermissions = useMemo(() => {
    if (!draft) return [];
    const entries = [];
    Object.entries(draft).forEach(([role, modulesMap]) => {
      Object.entries(modulesMap).forEach(([moduleKey, perms]) => {
        entries.push({
          role,
          module_key: moduleKey,
          can_read: Boolean(perms.can_read),
          can_write: Boolean(perms.can_write),
        });
      });
    });
    return entries;
  }, [draft]);

  const handleSave = () => {
    if (!dirtyPermissions.length) {
      notify.info('No changes to save.');
      return;
    }
    saveMatrix(dirtyPermissions);
  };

  if (isLoading) {
    return (
      <div className="py-5 text-center">
        <div className="spinner-border text-primary" role="status" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="alert alert-danger">
        Unable to load permission settings. Ensure your plan includes modules to configure.
      </div>
    );
  }

  const roleModules = modules.filter((mod) => matrix[selectedRole]?.[mod.key]);

  return (
    <div>
      <PageHeader
        title="Permission Settings"
        subtitle="Configure read and write access per role for each module on your plan"
        actions={(
          <div className="d-flex gap-2">
            <button
              type="button"
              className="btn btn-outline-secondary btn-sm"
              disabled={resetting || !selectedRole}
              onClick={() => resetRole(selectedRole)}
            >
              <FiRefreshCw className="me-1" /> Reset role
            </button>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={saving || !dirtyPermissions.length}
              onClick={handleSave}
            >
              <FiSave className="me-1" /> Save changes
            </button>
          </div>
        )}
      />

      <motion.div
        className="apex-card p-3 p-md-4 mb-4"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="d-flex align-items-center gap-2 mb-3">
          <FiShield className="text-primary" />
          <p className="small text-muted mb-0">
            Effective access = subscription plan modules ∩ role permissions.
            School admins always have full access. No role can exceed school admin privileges.
          </p>
        </div>

        <div className="permission-role-tabs d-flex flex-wrap gap-2 mb-4">
          {roles.map((role) => (
            <button
              key={role.key}
              type="button"
              className={`btn btn-sm ${selectedRole === role.key ? 'btn-primary' : 'btn-outline-secondary'}`}
              onClick={() => setActiveRole(role.key)}
            >
              {role.label}
            </button>
          ))}
        </div>

        <div className="table-responsive">
          <table className="table table-hover permission-matrix-table align-middle mb-0">
            <thead>
              <tr>
                <th>Module</th>
                <th className="text-center">Read</th>
                <th className="text-center">Write</th>
              </tr>
            </thead>
            <tbody>
              {roleModules.map((mod) => {
                const cell = matrix[selectedRole]?.[mod.key] || {};
                const Icon = resolveFeatureIcon(mod.icon);
                return (
                  <tr key={mod.key}>
                    <td>
                      <div className="d-flex align-items-center gap-2">
                        <span className="school-module-icon"><Icon size={16} /></span>
                        <div>
                          <div className="fw-semibold small">{mod.label}</div>
                          {cell.is_custom && (
                            <span className="badge text-bg-light border small">Customized</span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="text-center">
                      <PermissionCell
                        type="read"
                        value={cell.can_read}
                        onChange={(v) => updateCell(selectedRole, mod.key, 'can_read', v)}
                      />
                    </td>
                    <td className="text-center">
                      <PermissionCell
                        type="write"
                        value={cell.can_write}
                        disabled={!cell.can_read}
                        onChange={(v) => updateCell(selectedRole, mod.key, 'can_write', v)}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {!roleModules.length && (
          <p className="text-muted small mb-0 mt-3">
            No modules on your current plan are available for this role.
          </p>
        )}
      </motion.div>
    </div>
  );
}

export default PermissionSettings;