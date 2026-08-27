const STATUS_ORDER = { fail: 0, skipped: 1, pass: 2 }

/**
 * §3.2/§3.11 lab cross-reference checks (plasticity term vs. lab LL%,
 * USCS symbol vs. A-line, grading symbol vs. Cu/Cc) - split out from the
 * rest of rule_findings per Phase 2b Step 2.3, since these are some of
 * the most valuable findings the feature produces and carry an actionable
 * suggested correction that needs to be easy to spot and act on, not
 * folded anonymously into the general rule-checked list.
 */
export default function LabCrossReferenceFindings({ findings }) {
  if (!findings || findings.length === 0) return null

  const sorted = [...findings].sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status])

  return (
    <div className="findings-group lab-cross-ref-group">
      <h3>Lab cross-reference findings</h3>
      <p className="findings-group-subtitle">
        Field description checked against the attached lab report's actual measured values.
      </p>
      <ul className="lab-cross-ref-list">
        {sorted.map((f, i) => {
          const sampleId = f.compared?.sample_id
          return (
            <li key={i} className={`lab-cross-ref-finding lab-cross-ref-${f.status}`}>
              <div className="lab-cross-ref-head">
                {sampleId && <span className="lab-cross-ref-sample">Sample {sampleId}</span>}
                <span className="lab-cross-ref-section">{f.standard_section}</span>
              </div>
              {f.status === 'fail' ? (
                <p className="lab-cross-ref-suggestion">
                  <strong>Suggested correction: </strong>
                  {f.explanation}
                </p>
              ) : f.status === 'skipped' ? (
                <p className="lab-cross-ref-skipped">Not checked — {f.explanation}</p>
              ) : (
                <p className="lab-cross-ref-pass">{f.explanation}</p>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
