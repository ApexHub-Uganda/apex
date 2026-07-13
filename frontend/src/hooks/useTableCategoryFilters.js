import { useMemo, useState, useCallback } from 'react';
import { applyCategoryFilters } from '../utils/categoryFilters';

/**
 * Manages category filter state and returns filtered rows for a directory table.
 */
export function useTableCategoryFilters(rows, filterDefs) {
  const [values, setValues] = useState({});

  const setFilter = useCallback((key, value) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  }, []);

  const clearFilters = useCallback(() => {
    setValues({});
  }, []);

  const filteredRows = useMemo(
    () => applyCategoryFilters(rows, filterDefs, values),
    [rows, filterDefs, values],
  );

  const activeCount = useMemo(
    () => Object.values(values).filter(Boolean).length,
    [values],
  );

  return {
    values,
    setFilter,
    clearFilters,
    filteredRows,
    activeCount,
  };
}

export default useTableCategoryFilters;