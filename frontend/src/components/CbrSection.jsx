import CbrSummary from './CbrSummary'

export default function CbrSection({ results }) {
  if (!results || results.length === 0) return null

  return (
    <section className="result-section">
      <h2>California Bearing Ratio (CBR) ({results.length})</h2>
      <p className="calc-explanation-text">
        CBR measures the strength of a compacted material by comparing its resistance to a
        standard penetration test against a reference crushed-stone value. It's widely used to
        design pavement and subgrade thickness.
      </p>
      {results.map((row, i) => (
        <div className="result-card" key={i}>
          <dl>
            <dt>Sample</dt>
            <dd>{row.mg_sample_no ?? '—'} ({row.sample_id ?? '—'})</dd>
            <dt>Description</dt>
            <dd>{row.sample_description ?? '—'}</dd>
          </dl>
          <CbrSummary sample={row} />
        </div>
      ))}
    </section>
  )
}
