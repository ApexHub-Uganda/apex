import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { FiSearch, FiChevronLeft, FiChevronRight, FiFilter } from 'react-icons/fi';
import { TableSkeleton } from './LoadingSkeleton';

export function DataTable({
  columns,
  data = [],
  loading = false,
  searchable = true,
  searchPlaceholder = 'Search...',
  pageSize = 10,
  onRowClick,
  emptyMessage = 'No records found',
  actions,
  filters,
  compact = false,
}) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState('asc');

  const filtered = useMemo(() => {
    let result = [...data];
    if (search) {
      const q = search.toLowerCase();
      result = result.filter((row) =>
        columns.some((col) => {
          const val = col.accessor ? (typeof col.accessor === 'function' ? col.accessor(row) : row[col.accessor]) : '';
          return String(val ?? '').toLowerCase().includes(q);
        })
      );
    }
    if (sortKey) {
      result.sort((a, b) => {
        const aVal = a[sortKey];
        const bVal = b[sortKey];
        const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
        return sortDir === 'asc' ? cmp : -cmp;
      });
    }
    return result;
  }, [data, search, sortKey, sortDir, columns]);

  const totalPages = Math.ceil(filtered.length / pageSize);
  const paginated = filtered.slice(page * pageSize, (page + 1) * pageSize);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  if (loading) return <TableSkeleton rows={pageSize} cols={columns.length} />;

  return (
    <motion.div
      className="apex-card overflow-hidden"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      {(searchable || filters || actions) && (
        <div className="p-3 border-bottom d-flex flex-wrap gap-2 align-items-center justify-content-between">
          <div className="d-flex gap-2 flex-wrap flex-grow-1">
            {searchable && (
              <div className="position-relative" style={{ minWidth: 240 }}>
                <FiSearch className="position-absolute text-muted" style={{ left: 12, top: '50%', transform: 'translateY(-50%)' }} />
                <input
                  type="text"
                  className="form-control ps-5"
                  placeholder={searchPlaceholder}
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                />
              </div>
            )}
            {filters}
          </div>
          {actions && <div className="d-flex gap-2">{actions}</div>}
        </div>
      )}

      <div className={`apex-table-wrapper${compact ? ' apex-table-wrapper--fit' : ''}`}>
        <table className={`table apex-table mb-0${compact ? ' apex-table--compact' : ''}`}>
          {compact && columns.some((col) => col.width) && (
            <colgroup>
              {columns.map((col) => (
                <col key={col.key} style={{ width: col.width }} />
              ))}
            </colgroup>
          )}
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={col.sortable ? () => handleSort(col.key) : undefined}
                  style={{
                    cursor: col.sortable ? 'pointer' : 'default',
                    ...(col.width && !compact ? { width: col.width } : {}),
                  }}
                >
                  <span className="d-flex align-items-center gap-1">
                    {col.label}
                    {col.sortable && sortKey === col.key && (
                      <FiFilter size={12} style={{ transform: sortDir === 'desc' ? 'rotate(180deg)' : 'none' }} />
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="text-center py-5 text-muted">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              paginated.map((row, i) => (
                <motion.tr
                  key={row.id ?? i}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.03 }}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  style={{ cursor: onRowClick ? 'pointer' : 'default' }}
                >
                  {columns.map((col) => (
                    <td key={col.key}>
                      {col.render ? col.render(row) : (typeof col.accessor === 'function' ? col.accessor(row) : row[col.accessor])}
                    </td>
                  ))}
                </motion.tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="p-3 border-top d-flex justify-content-between align-items-center">
          <span className="text-muted small">
            Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, filtered.length)} of {filtered.length}
          </span>
          <div className="d-flex gap-1">
            <button className="btn btn-sm btn-outline-secondary" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              <FiChevronLeft />
            </button>
            <button className="btn btn-sm btn-outline-secondary" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>
              <FiChevronRight />
            </button>
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default DataTable;