import { useCallback, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FiChevronDown, FiChevronRight, FiLayers, FiRefreshCw, FiSave, FiShield, FiSliders,
} from 'react-icons/fi';
import PageHeader from '../../components/PageHeader';
import ResetPermissionsModal from '../../components/ResetPermissionsModal';
import { tenantService } from '../../services/tenantService';
import { extractApiError, notify } from '../../utils/notify';
import { resolveFeatureIcon } from '../../utils/featureIcons';

function PermissionToggle({ checked, onChange, disabled, label, variant = 'read' }) {
  return (
    <label
      className={`permission-matrix-cell permission-matrix-cell--${variant}`}
      title={label}
    >
      <input
        type="checkbox"
        className="form-check-input"
        checked={Boolean(checked)}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        aria-label={label}
      />
    </label>
  );
}

function mergeCell(base = {}, patch = {}) {
  return { ...base, ...patch, is_custom: true };
}

export function PermissionSettings() {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState(null);
  const [activeRole, setActiveRole] = useState(null);
  const [expandedModules, setExpandedModules] = useState({});
  const [showResetModal, setShowResetModal] = useState(false);

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
    mutationFn: (payload) => tenantService.resetRolePermissions({
      role: selectedRole,
      ...payload,
    }),
    onSuccess: (result) => {
      setDraft(null);
      setExpandedModules({});
      setShowResetModal(false);
      queryClient.setQueryData(['tenant', 'role-permissions'], result);
      queryClient.invalidateQueries({ queryKey: ['tenant', 'context'] });
      notify.success('Role permissions reset to defaults.');
    },
    onError: (err) => {
      notify.error(extractApiError(err, 'Failed to reset permissions.'));
    },
  });

  const updateModuleCell = useCallback((role, moduleKey, field, value) => {
    setDraft((prev) => {
      const base = prev || data?.matrix || {};
      const roleRow = { ...(base[role] || {}) };
      const cell = { ...(roleRow[moduleKey] || {}) };
      const features = { ...(cell.features || {}) };

      if (field === 'can_write' && value) {
        cell.can_read = true;
        cell.can_write = true;
      } else if (field === 'can_read' && !value) {
        cell.can_read = false;
        cell.can_write = false;
        cell.granular = false;
        Object.keys(features).forEach((featureKey) => {
          features[featureKey] = mergeCell(features[featureKey], {
            can_read: false,
            can_write: false,
          });
        });
      } else {
        cell[field] = value;
      }

      if (!cell.granular && cell.can_read) {
        Object.keys(features).forEach((featureKey) => {
          features[featureKey] = mergeCell(features[featureKey], {
            can_read: cell.can_read,
            can_write: cell.can_write,
          });
        });
      }

      cell.features = features;
      cell.is_custom = true;
      if (!cell.can_read) {
        cell.clear_granular = true;
      }
      roleRow[moduleKey] = cell;
      return { ...base, [role]: roleRow };
    });
  }, [data?.matrix]);

  const updateFeatureCell = useCallback((role, moduleKey, featureKey, field, value) => {
    setDraft((prev) => {
      const base = prev || data?.matrix || {};
      const roleRow = { ...(base[role] || {}) };
      const cell = { ...(roleRow[moduleKey] || {}) };
      const features = { ...(cell.features || {}) };
      const feat = { ...(features[featureKey] || {}) };

      if (field === 'can_write' && value) {
        feat.can_read = true;
        feat.can_write = true;
      } else if (field === 'can_read' && !value) {
        feat.can_read = false;
        feat.can_write = false;
      } else {
        feat[field] = value;
      }

      features[featureKey] = mergeCell(feat);
      cell.features = features;
      cell.granular = true;
      cell.is_custom = true;
      cell.can_read = Object.values(features).some((f) => f.can_read);
      cell.can_write = Object.values(features).some((f) => f.can_write);
      roleRow[moduleKey] = cell;
      return { ...base, [role]: roleRow };
    });
  }, [data?.matrix]);

  const enableGranularMode = useCallback((role, moduleKey) => {
    setDraft((prev) => {
      const base = prev || data?.matrix || {};
      const roleRow = { ...(base[role] || {}) };
      const cell = { ...(roleRow[moduleKey] || {}) };
      if (cell.granular) return base;
      const features = { ...(cell.features || {}) };
      Object.keys(features).forEach((featureKey) => {
        const feat = features[featureKey] || {};
        features[featureKey] = mergeCell(feat, {
          can_read: Boolean(cell.can_read),
          can_write: Boolean(cell.can_write),
        });
      });
      roleRow[moduleKey] = {
        ...cell,
        granular: true,
        features,
        is_custom: true,
      };
      return { ...base, [role]: roleRow };
    });
    setExpandedModules((prev) => ({ ...prev, [moduleKey]: true }));
  }, [data?.matrix]);

  const applyModuleToAllFeatures = useCallback((role, moduleKey) => {
    setDraft((prev) => {
      const base = prev || data?.matrix || {};
      const roleRow = { ...(base[role] || {}) };
      const cell = { ...(roleRow[moduleKey] || {}) };
      const features = { ...(cell.features || {}) };
      Object.keys(features).forEach((featureKey) => {
        features[featureKey] = mergeCell(features[featureKey], {
          can_read: Boolean(cell.can_read),
          can_write: Boolean(cell.can_write),
        });
      });
      roleRow[moduleKey] = {
        ...cell,
        granular: false,
        clear_granular: true,
        features,
        is_custom: true,
      };
      return { ...base, [role]: roleRow };
    });
  }, [data?.matrix]);

  const dirtyPermissions = useMemo(() => {
    if (!draft || !data?.matrix) return [];
    const baseline = data.matrix;
    const entries = [];

    Object.entries(draft).forEach(([role, modulesMap]) => {
      Object.entries(modulesMap).forEach(([moduleKey, perms]) => {
        const baseCell = baseline[role]?.[moduleKey] || {};
        const moduleChanged = (
          Boolean(perms.can_read) !== Boolean(baseCell.can_read)
          || Boolean(perms.can_write) !== Boolean(baseCell.can_write)
          || Boolean(perms.granular) !== Boolean(baseCell.granular)
          || Boolean(perms.clear_granular)
        );

        if (moduleChanged) {
          entries.push({
            role,
            module_key: moduleKey,
            can_read: Boolean(perms.can_read),
            can_write: Boolean(perms.can_write),
            clear_granular: Boolean(perms.clear_granular),
          });
        }

        if (perms.granular && perms.features) {
          Object.entries(perms.features).forEach(([featureKey, feat]) => {
            const baseFeat = baseCell.features?.[featureKey] || {};
            const featureChanged = (
              Boolean(feat.can_read) !== Boolean(baseFeat.can_read)
              || Boolean(feat.can_write) !== Boolean(baseFeat.can_write)
              || Boolean(perms.granular) !== Boolean(baseCell.granular)
            );
            if (featureChanged || moduleChanged) {
              entries.push({
                role,
                feature_key: featureKey,
                can_read: Boolean(feat.can_read),
                can_write: Boolean(feat.can_write),
              });
            }
          });
        }
      });
    });
    return entries;
  }, [draft, data?.matrix]);

  const toggleExpanded = (moduleKey) => {
    setExpandedModules((prev) => ({ ...prev, [moduleKey]: !prev[moduleKey] }));
  };

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
  const selectedRoleLabel = roles.find((role) => role.key === selectedRole)?.label || selectedRole;

  const handleConfirmReset = (payload) => {
    resetRole(payload);
  };

  return (
    <div>
      <PageHeader
        title="Permission Settings"
        subtitle="Control module and sub-module access per role — ungranted items are hidden from dashboards"
        actions={(
          <div className="d-flex gap-2">
            <button
              type="button"
              className="btn btn-outline-danger btn-sm"
              disabled={resetting || !selectedRole}
              onClick={() => setShowResetModal(true)}
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
        <div className="permission-settings-intro d-flex align-items-start gap-3 mb-4">
          <span className="permission-settings-intro-icon">
            <FiShield size={18} />
          </span>
          <div>
            <p className="small text-muted mb-1">
              Effective access = subscription plan ∩ role permissions.
              Grant a whole module at once, or expand it to pick individual sub-modules
              (Terms, Classes, Payments, etc.).
            </p>
            <p className="small text-muted mb-0">
              School admins always have full access. Users only see modules and sub-modules
              they are allowed to read.
            </p>
          </div>
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

        <div className="permission-matrix-shell">
          <div className="permission-matrix-head d-none d-md-grid">
            <span>Module / Sub-module</span>
            <span className="text-center">Read</span>
            <span className="text-center">Write</span>
            <span className="text-end">Actions</span>
          </div>

          <div className="permission-matrix-body">
            {roleModules.map((mod) => {
              const cell = matrix[selectedRole]?.[mod.key] || {};
              const Icon = resolveFeatureIcon(mod.icon);
              const featureEntries = Object.entries(cell.features || {});
              const isExpanded = expandedModules[mod.key];
              const hasFeatures = featureEntries.length > 0;

              return (
                <div key={mod.key} className="permission-module-block">
                  <div className="permission-module-row">
                    <button
                      type="button"
                      className={`permission-module-label ${hasFeatures ? 'is-expandable' : ''}`}
                      onClick={() => hasFeatures && toggleExpanded(mod.key)}
                      disabled={!hasFeatures}
                      aria-expanded={hasFeatures ? isExpanded : undefined}
                    >
                      <span className="permission-module-expand" aria-hidden>
                        {hasFeatures ? (
                          isExpanded ? <FiChevronDown size={16} /> : <FiChevronRight size={16} />
                        ) : (
                          <span className="permission-module-expand-placeholder" />
                        )}
                      </span>
                      <span className="school-module-icon"><Icon size={16} /></span>
                      <div className="permission-module-label-text">
                        <div className="fw-semibold small">{mod.label}</div>
                        <div className="permission-module-meta">
                          {cell.granular ? (
                            <span className="permission-badge permission-badge--granular">
                              Custom sub-modules
                            </span>
                          ) : (
                            <span className="text-muted">All sub-modules</span>
                          )}
                          {cell.is_custom && (
                            <span className="permission-badge permission-badge--custom">Customized</span>
                          )}
                        </div>
                      </div>
                    </button>
                    <div className="permission-module-read text-center">
                      <PermissionToggle
                        variant="read"
                        label={`Read ${mod.label}`}
                        checked={cell.can_read}
                        onChange={(v) => updateModuleCell(selectedRole, mod.key, 'can_read', v)}
                      />
                    </div>
                    <div className="permission-module-write text-center">
                      <PermissionToggle
                        variant="write"
                        label={`Write ${mod.label}`}
                        checked={cell.can_write}
                        disabled={!cell.can_read}
                        onChange={(v) => updateModuleCell(selectedRole, mod.key, 'can_write', v)}
                      />
                    </div>
                    <div className="permission-module-actions text-end">
                      {hasFeatures && (
                        <div className="btn-group btn-group-sm">
                          <button
                            type="button"
                            className="btn btn-outline-secondary"
                            disabled={!cell.can_read}
                            onClick={() => enableGranularMode(selectedRole, mod.key)}
                            title="Pick individual sub-modules"
                          >
                            <FiSliders size={13} />
                          </button>
                          {cell.granular && (
                            <button
                              type="button"
                              className="btn btn-outline-secondary"
                              onClick={() => applyModuleToAllFeatures(selectedRole, mod.key)}
                              title="Apply module access to all sub-modules"
                            >
                              <FiLayers size={13} />
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  <AnimatePresence initial={false}>
                    {isExpanded && hasFeatures && (
                      <motion.div
                        className="permission-feature-list"
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                      >
                        {featureEntries.map(([featureKey, feat]) => {
                          const FeatureIcon = resolveFeatureIcon(feat.icon || mod.icon);
                          return (
                            <div key={featureKey} className="permission-feature-row">
                              <div className="permission-feature-label">
                                <span className="permission-feature-tree" aria-hidden />
                                <span className="school-module-icon school-module-icon--sm">
                                  <FeatureIcon size={14} />
                                </span>
                                <div>
                                  <div className="small fw-medium">{feat.label}</div>
                                  {feat.is_custom && (
                                    <span className="permission-badge permission-badge--custom">Custom</span>
                                  )}
                                </div>
                              </div>
                              <div className="text-center">
                                <PermissionToggle
                                  variant="read"
                                  label={`Read ${feat.label}`}
                                  checked={feat.can_read}
                                  disabled={!cell.can_read}
                                  onChange={(v) => {
                                    if (!cell.granular) enableGranularMode(selectedRole, mod.key);
                                    updateFeatureCell(selectedRole, mod.key, featureKey, 'can_read', v);
                                  }}
                                />
                              </div>
                              <div className="text-center">
                                <PermissionToggle
                                  variant="write"
                                  label={`Write ${feat.label}`}
                                  checked={feat.can_write}
                                  disabled={!cell.can_read || !feat.can_read}
                                  onChange={(v) => {
                                    if (!cell.granular) enableGranularMode(selectedRole, mod.key);
                                    updateFeatureCell(selectedRole, mod.key, featureKey, 'can_write', v);
                                  }}
                                />
                              </div>
                              <div />
                            </div>
                          );
                        })}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        </div>

        {!roleModules.length && (
          <p className="text-muted small mb-0 mt-3">
            No modules on your current plan are available for this role.
          </p>
        )}
      </motion.div>

      <ResetPermissionsModal
        show={showResetModal}
        onHide={() => !resetting && setShowResetModal(false)}
        roleLabel={selectedRoleLabel}
        onConfirm={handleConfirmReset}
        resetting={resetting}
      />
    </div>
  );
}

export default PermissionSettings;