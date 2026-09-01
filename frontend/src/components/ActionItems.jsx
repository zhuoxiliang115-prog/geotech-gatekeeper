import { getRuleFindingLocation, isLabCrossRefFinding } from './boreholeReviewChecks'

const TYPE_LABEL = { rule: 'Rule', lab: 'Lab', judgment: 'AI' }

/**
 * A scannable checklist for one hole, pulled together from everything
 * across its sheets that's actually worth acting on - rule-checked
 * fails, lab cross-reference fails (with their suggested correction),
 * and judgment findings (present only when something's worth a second
 * look, per judgment.py). Meant to be read top-to-bottom instead of
 * digging through each sheet's three separate sections.
 */
export default function ActionItems({ pages }) {
  const items = []
  for (const page of pages) {
    const sheet = page.parsed.header?.sheet
    const ruleFindings = page.rule_findings ?? []

    for (const f of ruleFindings) {
      if (isLabCrossRefFinding(f) || f.status !== 'fail') continue
      items.push({ type: 'rule', sheet, location: getRuleFindingLocation(f) ?? f.standard_section, text: f.explanation })
    }
    for (const f of ruleFindings) {
      if (!isLabCrossRefFinding(f) || f.status !== 'fail') continue
      items.push({
        type: 'lab',
        sheet,
        location: f.compared?.sample_id ? `Sample ${f.compared.sample_id}` : f.standard_section,
        text: f.explanation,
      })
    }
    for (const f of page.judgment_findings ?? []) {
      items.push({
        type: 'judgment',
        sheet,
        location: f.stratum_reference ?? 'General (whole page)',
        text: f.finding,
      })
    }
  }

  if (items.length === 0) {
    return (
      <p className="action-items-empty">
        No action items for this hole — no rule failures, lab-mismatches, or judgment flags
        across any of its sheets.
      </p>
    )
  }

  return (
    <div className="action-items">
      <h3>Action items ({items.length})</h3>
      <p className="findings-group-subtitle">
        Everything worth acting on for this hole, pulled from every sheet below - read this
        first, then check the full sections for context.
      </p>
      <ul className="action-items-list">
        {items.map((item, i) => (
          <li key={i} className={`action-item action-item-${item.type}`}>
            <span className={`action-item-tag action-item-tag-${item.type}`}>{TYPE_LABEL[item.type]}</span>
            <div className="action-item-body">
              <div className="action-item-location">
                Sheet {item.sheet ?? '?'} · {item.location}
              </div>
              <p className="action-item-text">{item.text}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
