import './StatDisplay.css'

/**
 * SMDD compaction result as a labeled stat display, not a fitted curve -
 * the source PDF renders the dry-density/moisture curve as vector
 * graphics with no underlying data table (unlike PSD's sieve table), so
 * there are no real test points to plot. Showing only what was actually
 * measured (the peak) rather than a fabricated curve shape.
 */
export default function SmddSummary({ sample }) {
  return (
    <div className="stat-display">
      <div className="stat-value">
        MDD {sample.max_dry_density_t_m3 ?? '—'} t/m³ @ OMC {sample.optimum_moisture_content_pct ?? '—'}%
      </div>
      <dl className="stat-details">
        <div><dt>Oversize retained (19mm)</dt><dd>{sample.oversize_retained_19mm_pct ?? '—'}%</dd></div>
        <div><dt>Oversize retained (37.5mm)</dt><dd>{sample.oversize_retained_37_5mm_pct ?? '—'}%</dd></div>
        <div><dt>Mould / fraction tested</dt><dd>{sample.mould_size_and_fraction ?? '—'}</dd></div>
        <div><dt>MDD/OMC method</dt><dd>{sample.mdd_omc_method ?? '—'}</dd></div>
      </dl>
      <p className="stat-note">
        Individual test points aren't available - the source PDF renders this curve as a
        graphic, not extractable data.
      </p>
    </div>
  )
}
