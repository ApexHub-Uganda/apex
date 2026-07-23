import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { FiSearch, FiChevronLeft, FiChevronRight, FiChevronRight as FiRowOpen, FiFilter } from 'react-icons/fi';
import { PageLoader } from './ApexLoader';
import { isNameColumn, isShortColumn, ROW_NUMBER_COLUMN } from '../utils/tableDisplay';

/**
 * Prefer horizontal scroll only when content is wider than the viewport.
 * Column widths are derived from the longest value in each column.
 */
const WIDE_TABLE_COLUMN_THRESHOLD = 8;

/** Approximate rendered text width (compact table font) + cell padding. */
function approxTextWidthPx(text, { header = false } = {}) {
  const s = String(text ?? '').replace(/\s+/g, ' ').trim();
  if (!s) return header ? 48 : 32;
  // ~0.8125rem body / ~0.6875rem header uppercase tracking
  const perChar = header ? 6.4 : 7.1;
  return Math.ceil(s.length * perChar) + (header ? 20 : 16);
}

function readColumnDisplayValue(col, row) {
  if (!row) return '';
  if (typeof col.searchValue === 'function') {
    const v = col.searchValue(row);
    if (v != null && v !== '') return String(v);
  }
  if (typeof col.accessor === 'function') {
    const v = col.accessor(row);
    if (v != null && typeof v !== 'object') return String(v);
  } else if (col.accessor) {
    const v = row[col.accessor];
    if (v != null && typeof v !== 'object') return String(v);
  }
  const direct = row[col.key];
  if (direct != null && typeof direct !== 'object') return String(direct);
  return '';
}

/**
 * Min-width per column from header label + longest data value (or explicit col.minWidth).
 * Caps only absurd free-text so layout stays usable; no clipping that causes overlaps.
 */
function computeContentColumnWidths(columns, rows) {
  const map = {};
  columns.forEach((col) => {
    if (col.key === '_rowNum') {
      map[col.key] = 28;
      return;
    }
    if (col.key === '_open') {
      map[col.key] = 30;
      return;
    }
    if (col.key === 'actions') {
      map[col.key] = 76;
      return;
    }
    if (col.minWidth && String(col.minWidth).endsWith('rem')) {
      const parsed = parseFloat(String(col.minWidth));
      if (Number.isFinite(parsed)) {
        map[col.key] = Math.ceil(parsed * 16);
        return;
      }
    }
    if (col.width && String(col.width).endsWith('rem') && !col.render) {
      const parsed = parseFloat(String(col.width));
      if (Number.isFinite(parsed)) {
        map[col.key] = Math.ceil(parsed * 16);
        return;
      }
    }

    let maxPx = approxTextWidthPx(col.label || '', { header: true }) + (col.sortable ? 12 : 0);
    // Custom-rendered columns: still size from label + any plain accessor text
    const sampleLimit = Math.min(rows.length, 200);
    for (let i = 0; i < sampleLimit; i += 1) {
      const text = readColumnDisplayValue(col, rows[i]);
      if (text) maxPx = Math.max(maxPx, approxTextWidthPx(text));
    }
    // Soft cap only for extreme free-text; table scrolls instead of clipping neighbours
    const softCap = isNameColumn(col) ? 420 : (col.render ? 280 : 400);
    map[col.key] = Math.min(Math.max(maxPx, 36), softCap);
  });
  return map;
}

/** Flatten row values used for multi-token client search. */
function rowSearchBlob(row, columns, searchKeys) {
  const parts = [];
  if (Array.isArray(searchKeys) && searchKeys.length) {
    searchKeys.forEach((key) => {
      const val = row?.[key];
      if (val != null && val !== '') parts.push(String(val));
    });
  }
  columns.forEach((col) => {
    if (col.key === 'actions' || col.key === '_open' || col.key === '_rowNum') return;
    if (col.searchValue) {
      parts.push(String(col.searchValue(row) ?? ''));
      return;
    }
    if (col.accessor) {
      const val = typeof col.accessor === 'function' ? col.accessor(row) : row[col.accessor];
      if (val != null && typeof val !== 'object') parts.push(String(val));
    }
  });
  // Always index common id/code fields even if not in columns
  ['id', 'code', 'reference', 'receipt_number', 'invoice_number', 'admission_number',
    'student_name', 'student_admission', 'email', 'phone', 'full_name'].forEach((k) => {
    if (row?.[k] != null && row[k] !== '') parts.push(String(row[k]));
  });
  return parts.join(' ').toLowerCase();
}

export function DataTable({
  columns,
  data = [],
  loading = false,
  searchable = true,
  searchPlaceholder = 'Search records…',
  /** Extra object keys always included in client search (beyond columns). */
  searchKeys = null,
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
      // Multi-token AND search: "ada g5" matches name Ada in class G5
      const tokens = search.trim().toLowerCase().split(/\s+/).filter(Boolean);
      if (tokens.length) {
        result = result.filter((row) => {
          const hay = rowSearchBlob(row, columns, searchKeys);
          return tokens.every((t) => hay.includes(t));
        });
      }
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
  }, [data, search, sortKey, sortDir, columns, searchKeys]);

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

  // Size each column from the longest value in the current dataset (+ header).
  const contentWidths = useMemo(
    () => computeContentColumnWidths(displayColumns, filtered),
    [displayColumns, filtered],
  );

  const tableMinWidth = useMemo(() => {
    const total = displayColumns.reduce(
      (sum, col) => sum + (contentWidths[col.key] || 48),
      0,
    );
    return Math.max(total, 240);
  }, [displayColumns, contentWidths]);

  const wrapperClassName = [
    'apex-table-wrapper',
    'apex-table-wrapper--scrollable',
    'apex-table-wrapper--content-sized',
    isWideTable || isAlwaysScrollable ? 'apex-table-wrapper--wide' : '',
    'apex-table-wrapper--mobile-scroll',
  ].filter(Boolean).join(' ');

  const tableClassName = [
    'table',
    'apex-table',
    'apex-table--content-sized',
    'mb-0',
    compact ? 'apex-table--compact' : '',
    'apex-table--scrollable',
    isWideTable ? 'apex-table--wide' : '',
    hasNameColumns ? 'apex-table--has-names' : '',
  ].filter(Boolean).join(' ');

  const wrapperStyle = { '--apex-table-min-width': `${tableMinWidth}px` };

  const getCellClass = (col) => {
    if (col.key === '_rowNum') return 'apex-table-cell--rownum';
    if (col.key === '_open') return 'apex-table-cell--open';
    if (col.key === 'actions') return 'apex-table-cell--actions';
    if (isNameColumn(col)) return 'apex-table-cell--name';
    if (isShortColumn(col)) return 'apex-table-cell--short';
    if (col.truncate === false || col.render) return 'apex-table-cell--fit';
    // Content-sized: no truncate wrapper that fights natural width
    return 'apex-table-cell--fit';
  };

  const wrapCellContent = (col, content, title) => {
    // Show full value; title still helps for custom/long content
    if (title && typeof content === 'string') {
      return <span title={title}>{content}</span>;
    }
    return content;
  };

  const colMinStyle = (col) => {
    const px = contentWidths[col.key];
    if (!px) return undefined;
    return { minWidth: px, width: 'auto' };
  };

  const getHeaderClass = (col) => {
    if (col.key === '_rowNum') return 'apex-table-cell--rownum';
    if (col.key === '_open') return 'apex-table-cell--open';
    if (col.key === 'actions') return 'apex-table-cell--actions';
    if (isNameColumn(col)) return 'apex-table-cell--name';
    if (isShortColumn(col)) return 'apex-table-cell--short';
    return 'apex-table-cell--fit';
  };

  const getCellValue = (col, row) => {
    if (typeof col.accessor === 'function') return col.accessor(row);
    if (col.accessor) return row[col.accessor];
    return row[col.key];
  };

  if (loading) {
    return embedded
      ? (
        <div className="apex-table-panel apex-table-panel--embedded">
          <PageLoader label="Loading records…" compact />
        </div>
      )
      : (
        <div className="apex-card apex-table-panel">
          <PageLoader label="Loading records…" />
        </div>
      );
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
                  type="search"
                  className="form-control form-control-sm ps-5 apex-table-search-input"
                  placeholder={searchPlaceholder}
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                  aria-label={searchPlaceholder}
                  autoComplete="off"
                />
                {search ? (
                  <button
                    type="button"
                    className="btn btn-link btn-sm position-absolute apex-table-search-clear p-0"
                    title="Clear search"
                    onClick={() => { setSearch(''); setPage(0); }}
                  >
                    ×
                  </button>
                ) : null}
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
          style={{ minWidth: tableMinWidth }}
        >
          <colgroup>
            {displayColumns.map((col) => (
              <col
                key={col.key}
                style={{
                  minWidth: contentWidths[col.key] || undefined,
                  width: 'auto',
                }}
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
                    ...colMinStyle(col),
                  }}
                >
                  <span className="d-flex align-items-center gap-1 text-nowrap">
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
                        <td key={col.key} className={getCellClass(col)} style={colMinStyle(col)}>
                          {serial}
                        </td>
                      );
                    }
                    if (col.key === '_open') {
                      return (
                        <td key={col.key} className={getCellClass(col)} style={colMinStyle(col)}>
                          <FiRowOpen size={14} className="apex-table-row-open-icon text-muted" aria-hidden />
                        </td>
                      );
                    }
                    const rawVal = getCellValue(col, row);
                    const title = rawVal != null && rawVal !== '' ? String(rawVal) : undefined;
                    const rendered = col.render
                      ? col.render(row, { serial, rowIndex: i })
                      : (rawVal ?? '—');
                    return (
                      <td
                        key={col.key}
                        className={getCellClass(col)}
                        style={colMinStyle(col)}
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