import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { FiSearch, FiChevronLeft, FiChevronRight, FiFilter } from 'react-icons/fi';
import { TableSkeleton } from './LoadingSkeleton';
import { ROW_NUMBER_COLUMN } from '../utils/tableDisplay';

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
  showRowNumbers = true,
  embedded = false,
  scrollable = false,
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

  const displayColumns = useMemo(() => {
    const base = columns.filter((col) => col.key !== 'id' && col.accessor !== 'id');
    if (!showRowNumbers) return base;
    return [{ ...ROW_NUMBER_COLUMN }, ...base];
  }, [columns, showRowNumbers]);

  const isScrollable = scrollable || displayColumns.length > 8;

  const tableMinWidth = useMemo(() => {
    if (!isScrollable) return undefined;
    const total = displayColumns.reduce((sum, col) => {
      if (col.key === '_rowNum') return sum + 44;
      if (col.key === 'actions') return sum + 120;
      if (col.minWidth) {
        const parsed = parseInt(String(col.minWidth), 10);
        return sum + (Number.isFinite(parsed) ? parsed : 120);
      }
      return sum + 120;
    }, 0);
    return Math.max(total, 720);
  }, [displayColumns, isScrollable]);

  const getCellClass = (col) => {
    if (col.key === '_rowNum') return 'apex-table-cell--rownum';
    if (col.key === 'actions') return 'apex-table-cell--actions';
    if (col.truncate === false || col.render) return 'apex-table-cell--fit';
    return 'apex-table-cell--truncate';
  };

  const wrapCellContent = (col, content, title) => {
    if (col.key === '_rowNum' || col.key === 'actions' || col.render || col.truncate === false) {
      return content;
    }
    return (
      <span className="apex-cell-truncate" title={title}>
        {content}
      </span>
    );
  };

  const getHeaderClass = (col) => {
    if (col.key === '_rowNum') return 'apex-table-cell--rownum';
    if (col.key === 'actions') return 'apex-table-cell--actions';
    return undefined;
  };

  const getCellValue = (col, row) => {
    if (typeof col.accessor === 'function') return col.accessor(row);
    if (col.accessor) return row[col.accessor];
    return row[col.key];
  };

  if (loading) {
    return embedded
      ? <div className="apex-table-panel apex-table-panel--embedded"><TableSkeleton rows={pageSize} cols={displayColumns.length} /></div>
      : <TableSkeleton rows={pageSize} cols={displayColumns.length} />;
  }

  const Wrapper = embedded ? 'div' : motion.div;
  const wrapperProps = embedded
    ? { className: 'apex-table-panel apex-table-panel--embedded' }
    : {
        className: 'apex-card apex-table-panel',
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        style: { maxWidth: '100%' },
      };

  return (
    <Wrapper {...wrapperProps}>
      {(searchable || filters || actions) && (
        <div className="p-3 border-bottom d-flex flex-wrap gap-2 align-items-center justify-content-between">
          <div className="d-flex gap-2 flex-wrap flex-grow-1" style={{ minWidth: 0 }}>
            {searchable && (
              <div className="position-relative apex-table-search">
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

      <div className={`apex-table-wrapper${isScrollable ? ' apex-table-wrapper--scrollable' : ' apex-table-wrapper--fit'}`}>
        <table
          className={`table apex-table mb-0${compact ? ' apex-table--compact' : ''}${isScrollable ? ' apex-table--scrollable' : ''}`}
          style={isScrollable ? { minWidth: tableMinWidth } : undefined}
        >
          {(isScrollable
            ? displayColumns.some((col) => col.minWidth)
            : displayColumns.some((col) => col.width)) && (
            <colgroup>
              {displayColumns.map((col) => (
                <col
                  key={col.key}
                  style={
                    isScrollable
                      ? { minWidth: col.minWidth || (col.key === '_rowNum' ? '2.75rem' : col.key === 'actions' ? '7rem' : undefined) }
                      : col.width ? { width: col.width } : undefined
                  }
                />
              ))}
            </colgroup>
          )}
          <thead>
            <tr>
              {displayColumns.map((col) => (
                <th
                  key={col.key}
                  className={getHeaderClass(col)}
                  onClick={col.sortable ? () => handleSort(col.key) : undefined}
                  style={{
                    cursor: col.sortable ? 'pointer' : 'default',
                    ...(isScrollable
                      ? { minWidth: col.minWidth || (col.key === '_rowNum' ? '2.75rem' : col.key === 'actions' ? '7rem' : undefined) }
                      : col.width ? { width: col.width } : {}),
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
                <td colSpan={displayColumns.length} className="text-center py-5 text-muted">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              paginated.map((row, i) => {
                const serial = page * pageSize + i + 1;
                return (
                <motion.tr
                  key={row.id ?? i}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.03 }}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  style={{ cursor: onRowClick ? 'pointer' : 'default' }}
                >
                  {displayColumns.map((col) => {
                    if (col.key === '_rowNum') {
                      return (
                        <td key={col.key} className={getCellClass(col)}>
                          {serial}
                        </td>
                      );
                    }
                    const rawVal = getCellValue(col, row);
                    const title = col.truncate !== false && col.key !== 'actions' && rawVal != null && rawVal !== ''
                      ? String(rawVal)
                      : undefined;
                    const rendered = col.render
                      ? col.render(row, { serial, rowIndex: i })
                      : (rawVal ?? '—');
                    return (
                      <td
                        key={col.key}
                        className={getCellClass(col)}
                        style={isScrollable && col.minWidth ? { minWidth: col.minWidth } : undefined}
                      >
                        {wrapCellContent(col, rendered, title)}
                      </td>
                    );
                  })}
                </motion.tr>
              );
              })
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
    </Wrapper>
  );
}

export default DataTable;