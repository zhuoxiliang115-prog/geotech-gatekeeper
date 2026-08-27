const STATUS_ICON = { pass: '✓', fail: '✕', skipped: '–' }
const STATUS_LABEL = { pass: 'Pass', fail: 'Fail', skipped: 'Not checked' }
// Fails first (need attention), then skips (need attention too, just a
// different kind), then passes last - deterministic checks are genuinely
// right or wrong, so this is a pass/fail list, not a neutral log.
const STATUS_ORDER = { fail: 0, skipped: 1, pass: 2 }

/**
 * Deterministic §4.1 checks only - lab cross-reference checks (same
 * category="rule_checked" from the backend) are split out into
 * LabCrossReferenceFindings so they get their own visual treatment per
 * Phase 2b Step 2.2/2.3.
 */
export default function RuleCheckedFindings({ findings }) {
  if (!findings || findings.length === 0) return null

  const sorted = [...findings].sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status])

  return (
    <div className="findings-group rule-checked-group">
      <h3>Rule-checked findings</h3>
      <p className="findings-group-subtitle">
        Deterministic checks against the standard doc - genuinely pass or fail, no ambiguity.
      </p>
      <ul className="rule-findings-list">
        {sorted.map((f, i) => (
          <li key={i} className={`rule-finding rule-finding-${f.status}`}>
            <span className="rule-finding-icon" aria-hidden="true">{STATUS_ICON[f.status]}</span>
            <div className="rule-finding-body">
              <div className="rule-finding-head">
                <span className="rule-finding-status-label">{STATUS_LABEL[f.status]}</span>
                <span className="rule-finding-section">{f.standard_section}</span>
              </div>
              <p className="rule-finding-explanation">{f.explanation}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
