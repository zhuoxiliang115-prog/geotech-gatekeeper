import { useState } from 'react'
import { soilParameters } from '../api'
import SoilParameterHoleTabs from './SoilParameterHoleTabs'
// Reusing BoreholeLogReview.css for its generic page-shell classes only
// (.log-review-form/.log-review-field/.review-submit-button/.hole-tab-bar/
// .log-header-summary) - this page's own findings-card pattern lives in
// SoilParameters.css instead, imported by SoilParameterFindings.jsx.
import './BoreholeLogReview.css'

/**
 * Top-level page for Stage 3: soil parameter derivation. A separate page
 * from Borehole Log Review, not a tab within it or merged into its
 * results - POST /soil-parameters is a genuinely separate, unrelated
 * backend call (deterministic classification + table lookup, no LLM, no
 * standard-compliance checks) with no shared response shape or stable ID
 * to join its strata back onto /review-log's findings by. Free and
 * instant (no per-page API cost), unlike the log review's judgment layer.
 */
export default function SoilParametersReview() {
  const [logFile, setLogFile] = useState(null)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!logFile) return

    setStatus('loading')
    setError(null)
    setResult(null)

    try {
      const data = await soilParameters(logFile)
      setResult(data)
      setStatus('done')
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  let totalStrata = 0
  let classifiedStrata = 0
  if (result) {
    for (const page of result.pages_processed) {
      for (const sr of page.strata_results) {
        totalStrata += 1
        if (sr.classification.classified) classifiedStrata += 1
      }
    }
  }

  return (
    <>
      <h1>Soil Parameters</h1>
      <p className="subtitle">
        Upload a borehole, pavement dip, test pit, or cored borehole log PDF to classify each
        Fill/Clay/Sand stratum and look up its typical design-parameter range. Rock strata aren't
        classified in this pass. This is the review step — nothing is saved.
      </p>

      <form onSubmit={handleSubmit} className="log-review-form">
        <div className="log-review-field">
          <label htmlFor="soil-param-log-file">Borehole/pavement dip/test pit log PDF</label>
          <input
            id="soil-param-log-file"
            type="file"
            accept="application/pdf"
            onChange={(e) => setLogFile(e.target.files?.[0] ?? null)}
          />
        </div>

        <button type="submit" disabled={!logFile || status === 'loading'} className="review-submit-button">
          {status === 'loading' ? 'Deriving parameters…' : 'Derive soil parameters'}
        </button>
      </form>

      {error && <p className="error">Error: {error}</p>}

      {result && (
        <div className="log-review-results">
          <p className="summary">
            Processed <strong>{result.filename}</strong> — {Object.keys(result.holes).length} hole(s),{' '}
            {classifiedStrata} of {totalStrata} stratum/strata classified.
          </p>

          <SoilParameterHoleTabs holes={result.holes} />

          <details className="raw-json">
            <summary>Raw JSON response</summary>
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </details>
        </div>
      )}
    </>
  )
}
