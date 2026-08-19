import './CalculationExplanation.css'

/**
 * Reusable calculation-steps + plain-language explanation block, shared
 * across every test type per Phase 2 Step 2: formula, the actual input
 * values, the computed output, and why it matters - not just the number.
 *
 * inputs: array of { label, value, unit? }
 */
export default function CalculationExplanation({ formula, inputs, output, explanation, note }) {
  return (
    <div className="calc-explanation">
      <div className="calc-formula">{formula}</div>
      <dl className="calc-inputs">
        {inputs.map((i) => (
          <div className="calc-input-row" key={i.label}>
            <dt>{i.label}</dt>
            <dd>{i.value ?? '—'}{i.unit ?? ''}</dd>
          </div>
        ))}
      </dl>
      <div className="calc-output">
        <span className="calc-output-arrow">→</span>
        <span className="calc-output-value">{output}</span>
      </div>
      {explanation && <p className="calc-explanation-text">{explanation}</p>}
      {note && <p className="calc-note">{note}</p>}
    </div>
  )
}
