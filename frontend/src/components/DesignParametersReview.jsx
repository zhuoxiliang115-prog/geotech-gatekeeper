import { useState } from 'react'
import { rockParameters, soilParameters } from '../api'
import DesignParameterHoleTabs from './DesignParameterHoleTabs'
import { mergeParameterHoles } from './designParameterDisplay'
// Reusing BoreholeLogReview.css for its generic page-shell classes only
// (.log-review-form/.log-review-field/.review-submit-button/.hole-tab-bar/
// .log-header-summary) - this page's own findings-card pattern lives in
// DesignParameters.css instead, imported by Soil/RockStratumCard.jsx.
import './BoreholeLogReview.css'

/**
 * Top-level page for Stage 3 + 3b combined: soil and rock parameter
 * derivation from the same uploaded log PDF. One upload triggers both
 * POST /soil-parameters and POST /rock-parameters (independent,
 * deterministic, rules-only calls - no shared response shape between
 * them), and mergeParameterHoles combines each hole's strata from both
 * into one depth-ordered list, since depth_from_m is a safe join key
 * here (a Cored Borehole sheet's genuine rock strata are never also
 * soil-classified, and vice versa - see mergeParameterHoles' own
 * docstring) unlike the /review-log + /soil-parameters case, where no
 * such join was ever attempted.
 */
export default function DesignParametersReview() {
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
      const [soilData, rockData] = await Promise.all([soilParameters(logFile), rockParameters(logFile)])
      const mergedHoles = mergeParameterHoles(soilData.holes, rockData.holes)
      setResult({ filename: soilData.filename, soilData, rockData, mergedHoles })
      setStatus('done')
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  let totalStrata = 0
  let classifiedStrata = 0
  if (result) {
    for (const entries of Object.values(result.mergedHoles)) {
      for (const entry of entries) {
        totalStrata += 1
        if (entry.sr.classification.classified) classifiedStrata += 1
      }
    }
  }

  return (
    <>
      <h1>Design Parameters</h1>
      <p className="subtitle">
        Upload a borehole, pavement dip, test pit, or cored borehole log PDF to classify each
        stratum and look up its typical design-parameter range — Fill/Clay/Sand strata against the
        soil table, Sandstone/Shale strata (Cored Borehole sheets) against Table 9.1 of the Sydney
        Classification System. Soil and rock strata for the same hole are shown together, in one
        depth-ordered column. This is the review step — nothing is saved.
      </p>

      <form onSubmit={handleSubmit} className="log-review-form">
        <div className="log-review-field">
          <label htmlFor="design-param-log-file">Borehole/pavement dip/test pit/cored borehole log PDF</label>
          <input
            id="design-param-log-file"
            type="file"
            accept="application/pdf"
            onChange={(e) => setLogFile(e.target.files?.[0] ?? null)}
          />
        </div>

        <button type="submit" disabled={!logFile || status === 'loading'} className="review-submit-button">
          {status === 'loading' ? 'Deriving parameters…' : 'Derive design parameters'}
        </button>
      </form>

      {error && <p className="error">Error: {error}</p>}

      {result && (
        <div className="log-review-results">
          <p className="summary">
            Processed <strong>{result.filename}</strong> — {Object.keys(result.mergedHoles).length} hole(s),{' '}
            {classifiedStrata} of {totalStrata} stratum/strata classified.
          </p>

          <DesignParameterHoleTabs mergedHoles={result.mergedHoles} />

          <details className="raw-json">
            <summary>Raw JSON response (soil-parameters + rock-parameters)</summary>
            <pre>{JSON.stringify({ soilData: result.soilData, rockData: result.rockData }, null, 2)}</pre>
          </details>
        </div>
      )}
    </>
  )
}
