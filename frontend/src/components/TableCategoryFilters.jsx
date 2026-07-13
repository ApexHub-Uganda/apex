import { FiX } from 'react-icons/fi';
import { buildSelectOptions } from '../utils/categoryFilters';

/**
 * Renders category filter dropdowns for DataTable toolbar.
 *
 * filterDefs: [{ key, label, field?, getValue?, options?, allLabel?, labelMap? }]
 */
export function TableCategoryFilters({
  data = [],
  filterDefs = [],
  values = {},
  onChange,
  onClear,
  activeCount = 0,
}) {
  if (!filterDefs.length) return null;

  return (
    <>
      {filterDefs.map((def) => {
        const options = def.options
          || buildSelectOptions(data, def.field, def.labelMap, def.optionLabelField);
        const selectValue = values[def.key] || '';

        return (
          <select
            key={def.key}
            className="form-select form-select-sm apex-table-category-filter"
            aria-label={`Filter by ${def.label}`}
            value={selectValue}
            onChange={(e) => onChange(def.key, e.target.value)}
          >
            <option value="">{def.allLabel || `All ${def.label}`}</option>
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        );
      })}
      {activeCount > 0 && onClear && (
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary d-inline-flex align-items-center gap-1"
          onClick={onClear}
        >
          <FiX size={14} /> Clear
        </button>
      )}
    </>
  );
}

export default TableCategoryFilters;