import AtterbergChart from './AtterbergChart'
import CalculationExplanation from './CalculationExplanation'

export default function AtterbergSection({ results }) {
  if (!results || results.length === 0) return null

  return (
    <section className="result-section">
      <h2>Atterberg / Plasticity Index ({results.length})</h2>
      <AtterbergChart samples={results} />
      <div className="uscs-glossary">
        <p>
          The chart classifies each sample by where its Liquid Limit and Plasticity Index plot
          relative to the "A" and "U" lines. Letters denote soil type (<strong>C</strong> = clay,{' '}
          <strong>M</strong> = silt, <strong>O</strong> = organic clay/silt), and the second letter
          denotes plasticity (<strong>L</strong> = low, LL&lt;35; <strong>I</strong> = intermediate,
          35≤LL&lt;50; <strong>H</strong> = high, LL≥50). A sample reads "X or Y" (e.g. "CL or OL")
          because clay and organic soils can plot in the same zone - lab observations (odour,
          colour, fibre content) distinguish them, not the LL/PI position alone.
        </p>
        <dl>
          <div><dt>CL-ML</dt><dd>Borderline zone (PI 4-7) for very low plasticity silty clays / clayey silts - too close to the clay/silt boundary to call either way.</dd></div>
          <div><dt>CL or OL</dt><dd>Clay or organic clay/silt of low plasticity (LL&lt;35, above the A-line).</dd></div>
          <div><dt>CI or OI</dt><dd>Clay or organic clay of intermediate plasticity (35≤LL&lt;50, above the A-line).</dd></div>
          <div><dt>CH or OH</dt><dd>Clay or organic clay of high plasticity (LL≥50, above the A-line).</dd></div>
          <div><dt>ML or OL</dt><dd>Silt or organic silt of low-to-intermediate plasticity (LL&lt;50, below the A-line).</dd></div>
          <div><dt>MH or OH</dt><dd>Silt or organic silt of high plasticity (LL≥50, below the A-line).</dd></div>
        </dl>
        <p className="uscs-glossary-note">
          The shaded region above the "U" line (the practical upper bound of PI for a given LL) is
          rarely encountered in natural soils - a point plotting there is worth double-checking.
        </p>
      </div>
      {results.map((row, i) => (
        <div className="result-card" key={i}>
          <dl>
            <dt>Sample</dt>
            <dd>{row.mg_sample_no ?? '—'} ({row.sample_id ?? '—'})</dd>
            <dt>Description</dt>
            <dd>{row.sample_description ?? '—'}</dd>
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
