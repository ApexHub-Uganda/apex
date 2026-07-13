function MetaCell({ label, value, wide = false, children }) {
  return (
    <div
      className={`dashboard-header-meta-cell${wide ? ' dashboard-header-meta-cell--wide' : ''}`}
      role="listitem"
    >
      <span className="dashboard-header-meta-label">{label}</span>
      {children ?? <span className="dashboard-header-meta-value">{value}</span>}
    </div>
  );
}

export function DashboardHeaderMeta({ context }) {
  if (!context) return null;

  const { academic_year: year, current_term: term, assigned_classes: classes, subject_codes: codes } = context;
  const hasYear = Boolean(year?.name);
  const hasTerm = Boolean(term?.name);
  const hasClasses = Array.isArray(classes) && classes.length > 0;
  const hasCodes = Array.isArray(codes) && codes.length > 0;

  if (!hasYear && !hasTerm && !hasClasses && !hasCodes) {
    return null;
  }

  const termDisplay = term?.term_number ? `Term ${term.term_number}` : term?.name;
  const termExtra = term?.term_number && term?.name && term.name !== `Term ${term.term_number}`
    ? term.name
    : null;

  return (
    <div className="dashboard-header-meta" role="list" aria-label="School context">
      <div className="dashboard-header-meta-grid">
        {hasYear && (
          <MetaCell label="Academic year" value={year.name} />
        )}
        {hasTerm && (
          <MetaCell label="Current term" value={termDisplay}>
            <span className="dashboard-header-meta-value">
              {termDisplay}
              {termExtra && (
                <span className="dashboard-header-meta-muted"> · {termExtra}</span>
              )}
            </span>
          </MetaCell>
        )}
        {hasClasses && (
          <MetaCell
            label={classes.length === 1 ? 'Class' : 'Classes'}
            value={classes.join(', ')}
          />
        )}
        {hasCodes && (
          <MetaCell
            label={codes.length === 1 ? 'Subject' : 'Subjects'}
            wide
          >
            <span className="dashboard-header-meta-codes">
              {codes.map((code) => (
                <span key={code} className="dashboard-header-code">{code}</span>
              ))}
            </span>
          </MetaCell>
        )}
      </div>
    </div>
  );
}

export default DashboardHeaderMeta;