import { useState } from 'react'
import LogHeaderSummary from './LogHeaderSummary'
import SoilParameterFindings from './SoilParameterFindings'

/**
 * Navigation across every hole in the uploaded log PDF - same tab-per-
 * hole_id UX as HoleTabs.jsx (reusing its .hole-tab-bar CSS from
 * BoreholeLogReview.css, and LogHeaderSummary directly - both are generic
 * page-shell widgets, not part of the findings-card pattern), but for
 * POST /soil-parameters' page shape: {page, header, strata_results}, no
 * `.parsed` wrapper and no rule/lab/judgment findings to split out, so no
 * ActionItems either - there's nothing here that's a "fail" to collect
 * into a checklist, just classified-or-not strata.
 */
export default function SoilParameterHoleTabs({ holes }) {
  const holeIds = Object.keys(holes)
  const [selected, setSelected] = useState(holeIds[0] ?? null)

  if (holeIds.length === 0) {
    return <p className="no-holes-found">No log pages with a recognisable hole ID were found in this PDF.</p>
  }

  const pages = [...(holes[selected] ?? [])].sort(
    (a, b) => (a.header?.sheet ?? 0) - (b.header?.sheet ?? 0)
  )

  return (
    <div className="hole-tabs">
      <div className="hole-tab-bar" role="tablist">
        {holeIds.map((holeId) => (
          <button
            key={holeId}
            role="tab"
            aria-selected={holeId === selected}
            className={`hole-tab${holeId === selected ? ' hole-tab-active' : ''}`}
            onClick={() => setSelected(holeId)}
          >
            {holeId} <span className="hole-tab-count">({holes[holeId].length})</span>
          </button>
        ))}
      </div>

      {pages.map((page) => (
        <div className="hole-sheet" key={page.page}>
          <LogHeaderSummary header={page.header} />
          <SoilParameterFindings strataResults={page.strata_results} />
        </div>
      ))}
    </div>
  )
}
