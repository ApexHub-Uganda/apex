import { useState } from 'react';
import { motion } from 'framer-motion';
import { FiTrash2 } from 'react-icons/fi';
import { alert, extractApiError, notify } from '../utils/notify';

/**
 * Danger zone for removing a student, staff, or parent record.
 * Visible when the user has read access to delete_user; write is required to execute.
 */
export function UserDeleteDangerZone({
  entityLabel = 'record',
  recordName = '',
  description,
  onDelete,
  canRead = false,
  canWrite = false,
  deleting = false,
}) {
  const [busy, setBusy] = useState(false);

  if (!canRead) return null;

  const handleDeleteClick = async () => {
    if (!canWrite) {
      notify.error(
        'Access denied. You need write permission for "Delete User" under Core Management to remove records.',
      );
      return;
    }

    const label = recordName ? `${entityLabel} "${recordName}"` : `this ${entityLabel}`;
    const result = await alert.confirm({
      title: `Delete ${entityLabel}?`,
      text: `This will permanently remove ${label} from your school directory. Linked portal access will be revoked. This cannot be undone.`,
      confirmText: `Delete ${entityLabel}`,
      cancelText: 'Cancel',
      icon: 'warning',
      danger: true,
    });

    if (!result.isConfirmed) return;

    setBusy(true);
    try {
      await onDelete();
    } catch (err) {
      notify.error(extractApiError(err, `Unable to delete ${entityLabel}.`));
    } finally {
      setBusy(false);
    }
  };

  const isBusy = deleting || busy;

  return (
    <motion.div
      className="apex-card p-4 border border-danger border-opacity-25 mt-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <div className="d-flex flex-wrap align-items-start justify-content-between gap-3">
        <div>
          <h5 className="fw-bold text-danger mb-1 d-flex align-items-center gap-2">
            <FiTrash2 /> Danger Zone
          </h5>
          <p className="text-muted small mb-0">
            {description || `Permanently delete this ${entityLabel} from the school directory.`}
            {!canWrite && (
              <span className="d-block mt-1 text-warning-emphasis">
                You can view this section but need Delete User write permission to proceed.
              </span>
            )}
          </p>
        </div>
        <button
          type="button"
          className="btn btn-outline-danger btn-sm"
          onClick={handleDeleteClick}
          disabled={isBusy}
        >
          {isBusy ? 'Deleting…' : `Delete ${entityLabel}…`}
        </button>
      </div>
    </motion.div>
  );
}

export default UserDeleteDangerZone;