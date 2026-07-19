import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { FiChevronDown, FiSearch, FiX } from 'react-icons/fi';

/**
 * Professional combobox for large finance/entity pickers (students, fee items, classes, etc.).
 *
 * options: [{ value, label, keywords?, meta? }]
 * - label: primary display
 * - keywords: extra searchable text (admission no, class, phone…)
 * - meta: secondary line under label
 */
export function SearchableSelect({
  options = [],
  value = '',
  onChange,
  placeholder = 'Search and select…',
  emptyLabel = 'No matches',
  disabled = false,
  required = false,
  id,
  className = '',
  allowClear = true,
  maxMenuHeight = 280,
}) {
  const reactId = useId();
  const inputId = id || reactId;
  const rootRef = useRef(null);
  const inputRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [highlight, setHighlight] = useState(0);

  const selected = useMemo(
    () => options.find((o) => String(o.value) === String(value)) || null,
    [options, value],
  );

  const filtered = useMemo(() => {
    const tokens = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (!tokens.length) return options;
    return options.filter((o) => {
      const hay = [
        o.label,
        o.meta,
        o.keywords,
        o.value,
      ].filter(Boolean).join(' ').toLowerCase();
      return tokens.every((t) => hay.includes(t));
    });
  }, [options, query]);

  useEffect(() => {
    if (!open) return undefined;
    setHighlight(0);
    const onDoc = (e) => {
      if (!rootRef.current?.contains(e.target)) {
        setOpen(false);
        setQuery('');
      }
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  useEffect(() => {
    if (open) {
      // Focus search field when menu opens
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const pick = (opt) => {
    onChange?.(opt?.value ?? '');
    setOpen(false);
    setQuery('');
  };

  const onKeyDown = (e) => {
    if (!open) {
      if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        setOpen(true);
      }
      return;
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      setOpen(false);
      setQuery('');
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlight((h) => Math.min(h + 1, Math.max(filtered.length - 1, 0)));
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      const opt = filtered[highlight];
      if (opt) pick(opt);
    }
  };

  return (
    <div
      ref={rootRef}
      className={`apex-searchable-select ${open ? 'is-open' : ''} ${disabled ? 'is-disabled' : ''} ${className}`}
    >
      <button
        type="button"
        id={inputId}
        className="form-select apex-searchable-select-trigger text-start d-flex align-items-center justify-content-between gap-2"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-required={required || undefined}
        onClick={() => !disabled && setOpen((v) => !v)}
        onKeyDown={onKeyDown}
      >
        <span className={`text-truncate ${selected ? '' : 'text-muted'}`}>
          {selected ? selected.label : placeholder}
        </span>
        <span className="d-flex align-items-center gap-1 flex-shrink-0">
          {allowClear && selected && !disabled && (
            <span
              role="button"
              tabIndex={-1}
              className="apex-searchable-select-clear"
              title="Clear"
              onClick={(e) => {
                e.stopPropagation();
                pick(null);
              }}
            >
              <FiX size={14} />
            </span>
          )}
          <FiChevronDown size={16} className="text-muted" />
        </span>
      </button>

      {open && (
        <div className="apex-searchable-select-menu shadow-lg border rounded">
          <div className="p-2 border-bottom">
            <div className="position-relative">
              <FiSearch className="position-absolute text-muted apex-searchable-select-search-icon" />
              <input
                ref={inputRef}
                type="search"
                className="form-control form-control-sm ps-4"
                placeholder="Type to filter…"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setHighlight(0);
                }}
                onKeyDown={onKeyDown}
                autoComplete="off"
              />
            </div>
            <div className="small text-muted mt-1 px-1">
              {filtered.length} of {options.length} option{options.length === 1 ? '' : 's'}
            </div>
          </div>
          <ul
            className="list-unstyled mb-0 apex-searchable-select-list"
            role="listbox"
            style={{ maxHeight: maxMenuHeight }}
          >
            {filtered.length === 0 ? (
              <li className="px-3 py-3 text-muted small">{emptyLabel}</li>
            ) : (
              filtered.map((opt, idx) => (
                <li key={String(opt.value)}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={String(opt.value) === String(value)}
                    className={`apex-searchable-select-option w-100 text-start border-0 bg-transparent ${
                      idx === highlight ? 'is-active' : ''
                    } ${String(opt.value) === String(value) ? 'is-selected' : ''}`}
                    onMouseEnter={() => setHighlight(idx)}
                    onClick={() => pick(opt)}
                  >
                    <span className="d-block fw-medium text-truncate">{opt.label}</span>
                    {opt.meta ? (
                      <span className="d-block small text-muted text-truncate">{opt.meta}</span>
                    ) : null}
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

export default SearchableSelect;
