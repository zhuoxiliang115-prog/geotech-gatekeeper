/**
 * Compact quick-reference header for one log sheet - the parsed metadata,
 * not the point of the page (the findings below are). Per Phase 2b Step
 * 2.1: hole ID, log type, project, dates, etc., kept out of the way of
 * the findings that follow.
 */
export default function LogHeaderSummary({ header }) {
  if (!header) return null

  const sheetLabel =
    header.sheet != null && header.sheet_total != null
      ? `Sheet ${header.sheet} of ${header.sheet_total}`
      : null

  const continuity = [
    header.continued_from_previous && 'continued from previous sheet',
    header.continued_to_next && 'continues to next sheet',
  ].filter(Boolean)

  return (
    <div className="log-header-summary">
      <div className="log-header-title">
        <span className="log-header-hole-id">{header.hole_id ?? 'Unknown hole'}</span>
        <span className="log-header-type">{header.log_type ?? 'Unknown type'}</span>
        {sheetLabel && <span className="log-header-sheet">{sheetLabel}</span>}
      </div>
      <dl className="log-header-fields">
        <div><dt>Project</dt><dd>{header.project ?? '—'} {header.project_no ? `(${header.project_no})` : ''}</dd></div>
        <div><dt>Client</dt><dd>{header.client ?? '—'}</dd></div>
        <div><dt>Location</dt><dd>{header.location ?? '—'}</dd></div>
        <div><dt>Dates</dt><dd>{header.start_date ?? '—'} – {header.end_date ?? '—'}</dd></div>
        <div><dt>Logged / checked by</dt><dd>{header.logged_by ?? '—'} / {header.checked_by ?? '—'}</dd></div>
        <div><dt>RL / Total depth</dt><dd>{header.rl_m ?? '—'}m / {header.total_depth_m ?? '—'}m</dd></div>
      </dl>
      {continuity.length > 0 && (
        <p className="log-header-continuity">{continuity.join(' · ')}</p>
      )}
    </div>
  )
}
