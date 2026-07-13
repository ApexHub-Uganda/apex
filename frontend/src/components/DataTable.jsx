import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { FiSearch, FiChevronLeft, FiChevronRight, FiChevronRight as FiRowOpen, FiFilter } from 'react-icons/fi';
import { TableSkeleton } from './LoadingSkeleton';
import { isNameColumn, isShortColumn, ROW_NUMBER_COLUMN } from '../utils/tableDisplay';

/** Horizontal scroll only when the table has many columns. */
const WIDE_TABLE_COLUMN_THRESHOLD = 8;

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
  compact = true,
  showRowNumbers = true,
  embedded = false,
  scrollable = false,
  showRowOpenHint = true,
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
      const sortCol = columns.find((col) => col.key === sortKey);
      const readSortVal = (row) => {
        if (sortCol?.sortValue) return sortCol.sortValue(row);
        if (sortCol?.accessor && typeof sortCol.accessor === 'string') return row[sortCol.accessor];
        if (typeof sortCol?.accessor === 'function') return sortCol.accessor(row);
        return row[sortKey];
      };
      result.sort((a, b) => {
        const aVal = readSortVal(a);
        const bVal = readSortVal(b);
        const aEmpty = aVal == null || aVal === '';
        const bEmpty = bVal == null || bVal === '';
        if (aEmpty && bEmpty) return 0;
        if (aEmpty) return 1;
        if (bEmpty) return -1;
        const cmp = String(aVal).localeCompare(String(bVal), undefined, { numeric: true, sensitivity: 'base' });
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
    const hasActions = base.some((col) => col.key === 'actions');
    const withHint = onRowClick && showRowOpenHint && !hasActions
      ? [...base, { key: '_open', label: '', width: '2rem', truncate: false, sortable: false }]
      : base;
    if (!showRowNumbers) return withHint;
    return [{ ...ROW_NUMBER_COLUMN }, ...withHint];
  }, [columns, showRowNumbers, onRowClick, showRowOpenHint]);

  const hasNameColumns = useMemo(
    () => displayColumns.some((col) => isNameColumn(col)),
    [displayColumns],
  );

  const isAlwaysScrollable = scrollable;
  const isWideTable = displayColumns.length >= WIDE_TABLE_COLUMN_THRESHOLD;
  const useExpandedLayout = isAlwaysScrollable || isWideTable;

  const tableMinWidth = useMemo(() => {
    if (!useExpandedLayout) return undefined;
    const total = displayColumns.reduce((sum, col) => {
      if (col.key === '_rowNum') return sum + 22;
      if (col.key === '_open') return sum + 32;
      if (col.key === 'actions') return sum + 44;
      if (isNameColumn(col)) return sum + 112;
      if (col.width && String(col.width).endsWith('rem')) {
        const parsed = parseFloat(String(col.width));
        return sum + (Number.isFinite(parsed) ? parsed * 16 : 72);
      }
      if (col.minWidth && String(col.minWidth).endsWith('rem')) {
        const parsed = parseFloat(String(col.minWidth));
        return sum + (Number.isFinite(parsed) ? parsed * 16 : 72);
      }
      return sum + 72;
    }, 0);
    return Math.max(total, 640);
  }, [displayColumns, useExpandedLayout]);

  const wrapperClassName = [
    'apex-table-wrapper',
    useExpandedLayout ? 'apex-table-wrapper--scrollable' : 'apex-table-wrapper--fit',
    isWideTable ? 'apex-table-wrapper--wide' : '',
  ].filter(Boolean).join(' ');

  const tableClassName = [
    'table',
    'apex-table',
    'mb-0',
    compact ? 'apex-table--compact' : '',
    useExpandedLayout ? 'apex-table--scrollable' : '',
    isWideTable ? 'apex-table--wide' : '',
    hasNameColumns ? 'apex-table--has-names' : '',
  ].filter(Boolean).join(' ');

  const wrapperStyle = isWideTable && !isAlwaysScrollable && tableMinWidth
    ? { '--apex-table-min-width': `${tableMinWidth}px` }
    : undefined;

  const getCellClass = (col) => {
    if (col.key === '_rowNum') return 'apex-table-cell--rownum';
    if (col.key === '_open') return 'apex-table-cell--open';
    if (col.key === 'actions') return 'apex-table-cell--actions';
    if (isNameColumn(col)) return 'apex-table-cell--name';
    if (isShortColumn(col)) return 'apex-table-cell--short';
    if (col.truncate === false || col.render) return 'apex-table-cell--fit';
    return 'apex-table-cell--truncate';
  };

  const wrapCellContent = (col, content, title) => {
    if (
      col.key === '_rowNum'
      || col.key === '_open'
      || col.key === 'actions'
      || isNameColumn(col)
      || col.render
      || col.truncate === false
    ) {
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
    if (col.key === '_open') return 'apex-table-cell--open';
    if (col.key === 'actions') return 'apex-table-cell--actions';
    if (isNameColumn(col)) return 'apex-table-cell--name';
    if (isShortColumn(col)) return 'apex-table-cell--short';
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
        <div className="apex-table-toolbar p-2 px-3 border-bottom d-flex flex-wrap gap-2 align-items-center justify-content-between">
          <div className="d-flex gap-2 flex-wrap flex-grow-1" style={{ minWidth: 0 }}>
            {searchable && (
              <div className="position-relative apex-table-search">
                <FiSearch className="position-absolute text-muted apex-table-search-icon" />
                <input
                  type="text"
                  className="form-control form-control-sm ps-5 apex-table-search-input"
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

      <div className={wrapperClassName} style={wrapperStyle}>
        <table
          className={tableClassName}
          style={useExpandedLayout && tableMinWidth ? { minWidth: tableMinWidth } : undefined}
        >
          <colgroup>
            {displayColumns.map((col) => (
              <col
                key={col.key}
                style={
                  isNameColumn(col)
                    ? {
                        width: '1%',
                        minWidth: col.minWidth || '7rem',
                        maxWidth: col.maxWidth || '14rem',
                      }
                    : col.key === '_rowNum'
                      ? { width: '1.35rem' }
                      : { width: col.width || col.minWidth || undefined }
                }
              />
            ))}
          </colgroup>
          <thead>
            <tr>
              {displayColumns.map((col) => (
                <th
                  key={col.key}
                  className={getHeaderClass(col)}
                  onClick={col.sortable ? () => handleSort(col.key) : undefined}
                  style={{
                    cursor: col.sortable ? 'pointer' : 'default',
                    ...(isAlwaysScrollable
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
                  className={onRowClick ? 'apex-table-row--clickable' : undefined}
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
                    if (col.key === '_open') {
                      return (
                        <td key={col.key} className={getCellClass(col)}>
                          <FiRowOpen size={14} className="apex-table-row-open-icon text-muted" aria-hidden />
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
                        style={isAlwaysScrollable && col.minWidth ? { minWidth: col.minWidth } : undefined}
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
        <div className="apex-table-footer p-2 px-3 border-top d-flex justify-content-between align-items-center">
          <span className="text-muted apex-table-footer-meta">
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