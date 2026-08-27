import { useState } from 'react'
import LogHeaderSummary from './LogHeaderSummary'
import RuleCheckedFindings from './RuleCheckedFindings'
import LabCrossReferenceFindings from './LabCrossReferenceFindings'
import JudgmentFindings from './JudgmentFindings'
import ActionItems from './ActionItems'
import { isLabCrossRefFinding } from './boreholeReviewChecks'

/**
 * Navigation across every hole in the uploaded log PDF (Phase 2b Step 3) -
 * a single file can contain many holes, each potentially spanning
 * multiple sheets, so this is a tab per hole_id rather than one long page.
 * Sheets within a hole are shown as their own findings blocks underneath,
 * since rule_findings/judgment_findings are computed per sheet by the
 * backend and some findings (e.g. cross_sheet_continuity) are specifically
 * about the boundary between two sheets.
 */
export default function HoleTabs({ holes, judgmentModel }) {
  const holeIds = Object.keys(holes)
  const [selected, setSelected] = useState(holeIds[0] ?? null)

  if (holeIds.length === 0) {
    return <p className="no-holes-found">No log pages with a recognisable hole ID were found in this PDF.</p>
  }

  const pages = [...(holes[selected] ?? [])].sort(
    (a, b) => (a.parsed.header?.sheet ?? 0) - (b.parsed.header?.sheet ?? 0)
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

      <ActionItems pages={pages} />

      {pages.map((page) => {
        const ruleFindings = page.rule_findings ?? []
        const labCrossRef = ruleFindings.filter(isLabCrossRefFinding)
        const ruleChecked = ruleFindings.filter((f) => !isLabCrossRefFinding(f))

        return (
          <div className="hole-sheet" key={page.page}>
            <LogHeaderSummary header={page.parsed.header} />
            <RuleCheckedFindings findings={ruleChecked} />
            <LabCrossReferenceFindings findings={labCrossRef} />
            <JudgmentFindings
              findings={page.judgment_findings}
              judgmentError={page.judgment_error}
              judgmentModel={judgmentModel}
            />
          </div>
        )
      })}
    </div>
  )
}
