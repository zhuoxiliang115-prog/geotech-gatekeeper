import './StatDisplay.css'

/**
 * CBR result as a labeled stat display plus the Achieved/Target table -
 * the source PDF's load-penetration curve is a continuous drawn line with
 * no discrete data points at all, so (like SMDD) there's nothing real to
 * chart; this shows the values the report actually states instead.
 */
export default function CbrSummary({ sample }) {
  const at = sample.achieved_target ?? {}

  return (
    <div className="stat-display">
      <div className="stat-value">
        CBR {sample.cbr_value_pct ?? '—'}% @ {sample.cbr_governing_penetration_mm ?? '—'}mm penetration (governing)
      </div>

      <table className="achieved-target-table">
        <thead>
          <tr>
            <th></th>
            <th>Achieved</th>
            <th>Target</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Lab Moisture Ratio (%)</td>
            <td>{at.lab_moisture_ratio_pct?.achieved ?? '—'}</td>
            <td>{at.lab_moisture_ratio_pct?.target ?? '—'}</td>
          </tr>
          <tr>
            <td>Lab Density Ratio (%)</td>
            <td>{at.lab_density_ratio_pct?.achieved ?? '—'}</td>
            <td>{at.lab_density_ratio_pct?.target ?? '—'}</td>
          </tr>
          <tr>
            <td>Dry Density at Compaction (t/m³)</td>
            <td>{at.dry_density_at_compaction_t_m3?.achieved ?? '—'}</td>
            <td>{at.dry_density_at_compaction_t_m3?.target ?? '—'}</td>
          </tr>
        </tbody>
      </table>

      <dl className="stat-details">
        <div><dt>Specimen swell</dt><dd>{sample.specimen_swell_pct ?? '—'}%</dd></div>
        <div><dt>Dry density after soaking</dt><dd>{sample.dry_density_after_soaking_t_m3 ?? '—'} t/m³</dd></div>
      </dl>
      <p className="stat-note">
        The load-penetration curve isn't available - the source PDF renders it as a graphic
        with no underlying data points.
      </p>
    </div>
  )
}
