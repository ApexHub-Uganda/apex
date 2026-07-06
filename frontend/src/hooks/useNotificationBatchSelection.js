import { useCallback, useMemo, useState } from 'react';

export function useNotificationBatchSelection() {
  const [selectedIds, setSelectedIds] = useState(() => new Set());

  const selectionMode = selectedIds.size > 0;

  const isSelected = useCallback((id) => selectedIds.has(id), [selectedIds]);

  const toggleSelection = useCallback((id) => {
    if (!id) return;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const enterSelection = useCallback((id) => {
    if (!id) return;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.add(id);
      return next;
    });
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const selectedCount = selectedIds.size;

  const selectedIdList = useMemo(() => [...selectedIds], [selectedIds]);

  return {
    selectedIds,
    selectedIdList,
    selectedCount,
    selectionMode,
    isSelected,
    toggleSelection,
    enterSelection,
    clearSelection,
  };
}

export default useNotificationBatchSelection;