import SmddSummary from './SmddSummary'

export default function SmddSection({ results }) {
  if (!results || results.length === 0) return null

  return (
    <section className="result-section">
      <h2>Standard Compaction (SMDD) ({results.length})</h2>
      <p className="calc-explanation-text">
        This shows how compacted density changes with moisture content for this material. The
        peak - Maximum Dry Density (MDD) at Optimum Moisture Content (OMC) - is the target used
        to assess how well the material has been compacted on site.
      </p>
      {results.map((row, i) => (
        <div className="result-card" key={i}>
          <dl>
            <dt>Sample</dt>
            <dd>{row.mg_sample_no ?? '—'} ({row.sample_id ?? '—'})</dd>
            <dt>Description</dt>
            <dd>{row.sample_description ?? '—'}</dd>
          </dl>
          <SmddSummary sample={row} />
        </div>
      ))}
    </section>
  )
}
