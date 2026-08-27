import { JUDGMENT_CATEGORY_LABELS } from './boreholeReviewChecks'

/**
 * §4.2 LLM-assisted judgment findings - deliberately styled as a distinct
 * section (not just a different icon) from RuleCheckedFindings, and
 * deliberately not pass/fail: these are "worth a second look" at a stated
 * confidence, not verdicts, per Phase 2b Step 2.2. judgmentError is shown
 * as an explicit failure banner rather than an empty list, since a failed
 * review and a clean log both produce zero findings and must not look the
 * same.
 */
export default function JudgmentFindings({ findings, judgmentError, judgmentModel }) {
  return (
    <div className="findings-group judgment-group">
      <h3>Judgment-based findings <span className="judgment-badge">AI-assisted</span></h3>
      <p className="findings-group-subtitle">
        {judgmentModel ? `${judgmentModel} ` : ''}
        checked this page for things worth a second look - interpretive judgment calls, not
        verified defects. Treat every item below as a prompt to look closer, not a verdict.
      </p>

      {judgmentError ? (
        <p className="judgment-error">
          Judgment-based review did not complete for this page: {judgmentError}
        </p>
      ) : !findings || findings.length === 0 ? (
        <p className="judgment-empty">
          No judgment-based findings — the AI-assisted review ran and found nothing worth a
          second look on this page.
        </p>
      ) : (
        <ul className="judgment-findings-list">
          {findings.map((f, i) => (
            <li key={i} className="judgment-finding">
              <div className="judgment-finding-head">
                <span className="judgment-finding-location">
                  {f.stratum_reference ?? 'General (whole page)'}
                </span>
                <span className={`confidence-badge confidence-${f.confidence}`}>
                  {f.confidence} confidence
                </span>
              </div>
              <div className="judgment-finding-meta">
                <span className="judgment-finding-category">
                  {JUDGMENT_CATEGORY_LABELS[f.judgment_category] ?? f.judgment_category}
                </span>
                <span className="judgment-finding-section">{f.standard_section}</span>
              </div>
              <p className="judgment-finding-text">{f.finding}</p>
              <p className="judgment-finding-uncertainty">{f.uncertainty_note}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
