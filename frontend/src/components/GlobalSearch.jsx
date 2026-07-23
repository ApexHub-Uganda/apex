import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FiSearch, FiZap } from 'react-icons/fi';
import { searchService } from '../services/searchService';
import { resolveFeatureIcon } from '../utils/featureIcons';

const TYPE_LABELS = {
  module: 'Module',
  feature: 'Feature',
  action: 'Action',
  page: 'Page',
  staff: 'Staff',
  student: 'Student',
  parent: 'Parent',
};

function groupResults(results = []) {
  const groups = new Map();
  results.forEach((item) => {
    const key = item.category || TYPE_LABELS[item.type] || 'Results';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  });
  return [...groups.entries()];
}

export function GlobalSearch({
  disabled = false,
  placeholder,
  compactPlaceholder = 'Search…',
  fullPlaceholder = 'Search modules, people, actions…',
}) {
  const navigate = useNavigate();
  const containerRef = useRef(null);
  const inputRef = useRef(null);
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [isCompact, setIsCompact] = useState(
    () => typeof window !== 'undefined' && window.innerWidth < 768,
  );

  useEffect(() => {
    const onResize = () => setIsCompact(window.innerWidth < 768);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const resolvedPlaceholder = placeholder
    || (isCompact ? compactPlaceholder : fullPlaceholder);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  const { data, isFetching } = useQuery({
    queryKey: ['portal-search', debouncedQuery],
    queryFn: () => searchService.search(debouncedQuery),
    enabled: debouncedQuery.length >= 2 && !disabled,
    staleTime: 30000,
    retry: 1,
  });

  const results = data?.results || [];
  const flatResults = useMemo(() => results, [results]);
  const grouped = useMemo(() => groupResults(results), [results]);

  useEffect(() => {
    setActiveIndex(-1);
  }, [debouncedQuery, results.length]);

  useEffect(() => {
    if (!open) return undefined;
    const handleClickOutside = (event) => {
      if (containerRef.current?.contains(event.target)) return;
      setOpen(false);
    };
    const timer = window.setTimeout(() => {
      document.addEventListener('click', handleClickOutside);
    }, 0);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener('click', handleClickOutside);
    };
  }, [open]);

  const navigateToResult = useCallback((item) => {
    if (!item?.path) return;
    setOpen(false);
    setQuery('');
    navigate(item.path);
  }, [navigate]);

  const handleKeyDown = (event) => {
    if (!open && (event.key === 'ArrowDown' || event.key === 'Enter') && query.trim().length >= 2) {
      setOpen(true);
      return;
    }
    if (!flatResults.length) return;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((prev) => (prev + 1) % flatResults.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((prev) => (prev <= 0 ? flatResults.length - 1 : prev - 1));
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault();
      navigateToResult(flatResults[activeIndex]);
    } else if (event.key === 'Escape') {
      setOpen(false);
      inputRef.current?.blur();
    }
  };

  let runningIndex = -1;

  return (
    <div className="apex-global-search position-relative w-100" ref={containerRef}>
      <FiSearch className="position-absolute text-muted apex-global-search-icon" />
      <input
        ref={inputRef}
        type="search"
        className="form-control form-control-sm apex-global-search-input"
        placeholder={disabled ? 'Search unavailable' : resolvedPlaceholder}
        value={query}
        disabled={disabled}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onFocus={() => {
          if (query.trim().length >= 2) setOpen(true);
        }}
        onKeyDown={handleKeyDown}
        aria-label="Search portal"
        aria-expanded={open}
        aria-autocomplete="list"
        role="combobox"
      />

      {open && debouncedQuery.length >= 2 && (
        <div className="apex-global-search-panel shadow-lg" role="listbox">
          {isFetching && (
            <div className="apex-global-search-status">Searching…</div>
          )}
          {!isFetching && results.length === 0 && (
            <div className="apex-global-search-status">No results for “{debouncedQuery}”</div>
          )}
          {!isFetching && grouped.map(([category, items]) => (
            <div key={category} className="apex-global-search-group">
              <div className="apex-global-search-group-title">{category}</div>
              {items.map((item) => {
                runningIndex += 1;
                const currentIndex = runningIndex;
                const Icon = item.type === 'action'
                  ? FiZap
                  : resolveFeatureIcon(item.icon);
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={`apex-global-search-item ${activeIndex === currentIndex ? 'is-active' : ''}`}
                    onMouseEnter={() => setActiveIndex(currentIndex)}
                    onClick={() => navigateToResult(item)}
                    role="option"
                    aria-selected={activeIndex === currentIndex}
                  >
                    <span className="apex-global-search-item-icon">
                      <Icon size={14} />
                    </span>
                    <span className="apex-global-search-item-body">
                      <span className="apex-global-search-item-title">{item.title}</span>
                      {item.subtitle && (
                        <span className="apex-global-search-item-subtitle">{item.subtitle}</span>
                      )}
                    </span>
                    <span className="apex-global-search-item-type">{TYPE_LABELS[item.type] || item.type}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default GlobalSearch;