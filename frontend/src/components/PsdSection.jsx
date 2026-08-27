import PsdChart from './PsdChart'

export default function PsdSection({ results }) {
  if (!results || results.length === 0) return null

  return (
    <section className="result-section">
      <h2>Particle Size Distribution ({results.length})</h2>
      <PsdChart samples={results} />
      <p className="calc-explanation-text">
        This curve shows what percentage of the soil sample (by weight) passes through each
        sieve size. A steep curve means the soil is well-graded (mixed particle sizes); a flat
        curve at one point means most particles are a similar size.
      </p>
      {results.map((row, i) => (
        <div className="result-card" key={i}>
          <dl>
            <dt>Sample</dt>
            <dd>{row.mg_sample_no ?? '—'} ({row.sample_id ?? '—'})</dd>
            <dt>Description</dt>
            <dd>{row.sample_description ?? '—'}</dd>
            <dt>Readings (sieve mm → % passing)</dt>
            <dd>{row.readings.map((r) => `${r.sieve_mm}→${r.passing_pct}%`).join(', ')}</dd>
          </dl>
        </div>
      ))}
    </section>
  )
}
