import { groupEntriesBySheet } from './designParameterDisplay'
import LogHeaderSummary from './LogHeaderSummary'
import RockStratumCard from './RockStratumCard'
import SoilStratumCard from './SoilStratumCard'
import './DesignParameters.css'

/**
 * One hole's merged, depth-sorted strata (mergeParameterHoles' output for
 * that hole), rendered as one continuous depth-ordered column across
 * however many sheets the hole was split across in the source PDF - soil
 * strata from its Borehole sheet, then rock strata from its Cored
 * Borehole sheet(s), each with the card type matching where it actually
 * came from. Grouped into per-sheet runs (groupEntriesBySheet) purely so
 * each sheet's own header metadata (project, dates, logged/checked by)
 * still shows once, without breaking the overall depth ordering - every
 * sheet in this corpus covers a contiguous depth range, so this reads
 * the same as a literal flat list would.
 */
export default function DesignParameterFindings({ entries }) {
  if (!entries || entries.length === 0) {
    return <p className="soil-param-empty">No strata were extracted from this hole.</p>
  }

  const runs = groupEntriesBySheet(entries)

  return (
    <>
      {runs.map((run) => (
        <div className="hole-sheet" key={run.page}>
          <LogHeaderSummary header={run.header} />
          <ul className="soil-param-list">
            {run.items.map((entry, i) =>
              entry.origin === 'soil' ? (
                <SoilStratumCard key={i} sr={entry.sr} />
              ) : (
                <RockStratumCard key={i} sr={entry.sr} />
              )
            )}
          </ul>
        </div>
      ))}
    </>
  )
}
