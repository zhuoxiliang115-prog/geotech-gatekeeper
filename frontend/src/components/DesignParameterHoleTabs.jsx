import { useState } from 'react'
import DesignParameterFindings from './DesignParameterFindings'

/**
 * Navigation across every hole in the uploaded log PDF - same tab-per-
 * hole_id UX as HoleTabs.jsx/the old SoilParameterHoleTabs.jsx (reusing
 * .hole-tab-bar from BoreholeLogReview.css), but driven off
 * mergeParameterHoles' combined {holeId: entries[]} shape instead of one
 * endpoint's own `holes`, since a hole's soil and rock strata now render
 * together as one column.
 */
export default function DesignParameterHoleTabs({ mergedHoles }) {
  const holeIds = Object.keys(mergedHoles)
  const [selected, setSelected] = useState(holeIds[0] ?? null)

  if (holeIds.length === 0) {
    return <p className="no-holes-found">No log pages with a recognisable hole ID were found in this PDF.</p>
  }

  const entries = mergedHoles[selected] ?? []

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
            {holeId} <span className="hole-tab-count">({mergedHoles[holeId].length})</span>
          </button>
        ))}
      </div>

      <DesignParameterFindings entries={entries} />
    </div>
  )
}
