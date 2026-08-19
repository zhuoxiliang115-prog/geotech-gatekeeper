import AtterbergChart from './AtterbergChart'
import CalculationExplanation from './CalculationExplanation'

export default function AtterbergSection({ results }) {
  if (!results || results.length === 0) return null

  return (
    <section className="result-section">
      <h2>Atterberg / Plasticity Index ({results.length})</h2>
      <AtterbergChart samples={results} />
      {results.map((row, i) => (
        <div className="result-card" key={i}>
          <dl>
            <dt>Sample</dt>
            <dd>{row.mg_sample_no ?? '—'} ({row.sample_id ?? '—'})</dd>
            <dt>Raw values: LL / PL / PI</dt>
            <dd>{row.liquid_limit ?? '—'} / {row.plastic_limit ?? '—'} / {row.plasticity_index ?? '—'}</dd>
            <dt>Linear Shrinkage (separate lab measurement)</dt>
            <dd>{row.linear_shrinkage_pct ?? '—'}%</dd>
            <dt>A-line PI at this LL</dt>
            <dd>{row.a_line_pi_at_this_ll ?? '—'}</dd>
            <dt>Classification</dt>
            <dd>{row.classification_zone ?? '—'}</dd>
          </dl>

          {row.calculations?.plasticity_index && (
            <CalculationExplanation
              formula={row.calculations.plasticity_index.formula}
              inputs={[
                { label: 'LL', value: row.calculations.plasticity_index.inputs.ll, unit: '%' },
                { label: 'PL', value: row.calculations.plasticity_index.inputs.pl, unit: '%' },
              ]}
              output={`${row.calculations.plasticity_index.output}%`}
              explanation="Liquid Limit (LL) and Plastic Limit (PL) mark the moisture contents at which a soil
                changes behaviour - from liquid to plastic, and from plastic to solid. Plasticity
                Index (PI) is the range of moisture over which the soil stays plastic (workable). A
                higher PI generally means more clay content and greater potential for shrink-swell
                behaviour."
            />
          )}
        </div>
      ))}
    </section>
  )
}
