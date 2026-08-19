import EmersonChart from './EmersonChart'

export default function EmersonSection({ results }) {
  if (!results || results.length === 0) return null

  return (
    <section className="result-section">
      <h2>Emerson Class ({results.length})</h2>
      <EmersonChart samples={results} />
      <p className="calc-explanation-text">
        The Emerson Class Number (1-8) indicates how a soil breaks down when immersed in water -
        a quick indicator of dispersive/erosion-prone behaviour. Lower numbers (1-3) indicate
        dispersive, erosion-susceptible soils; higher numbers (7-8) indicate stable,
        non-dispersive soils. No calculation is involved - it's a direct lab observation.
      </p>
      {results.map((row, i) => (
        <div className="result-card" key={i}>
          <dl>
            <dt>Sample</dt>
            <dd>{row.mg_sample_no ?? '—'} ({row.sample_id ?? '—'})</dd>
            <dt>Description</dt>
            <dd>{row.sample_description ?? '—'}</dd>
            <dt>Raw value: Emerson Class</dt>
            <dd>{row.emerson_class ?? '—'}</dd>
            <dt>Lookup applied: dispersion table</dt>
            <dd>{row.dispersion_potential ?? '—'}</dd>
            <dt>Notes</dt>
            <dd>{row.notes ?? '—'}</dd>
          </dl>
        </div>
      ))}
    </section>
  )
}
