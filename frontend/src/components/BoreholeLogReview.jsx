import { useState } from 'react'
import { downloadReport, reviewLog } from '../api'
import { triggerDownload } from '../downloadFile'
import HoleTabs from './HoleTabs'
import './BoreholeLogReview.css'

/**
 * Phase 2b: borehole log review UI. Upload a log PDF, optionally attach
 * lab report PDFs for the same project, then explicitly trigger the
 * review - the judgment layer is one real, paid Claude API call per log
 * page, so it must never fire on file select/preview (Phase 2b Step 1).
 */
export default function BoreholeLogReview() {
  const [logFile, setLogFile] = useState(null)
  const [labFiles, setLabFiles] = useState([])
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [downloadError, setDownloadError] = useState(null)

  async function handleDownloadReport() {
    setDownloadError(null)
    try {
      const blob = await downloadReport(logFile, { reviewLogResult: result })
      triggerDownload(blob, `${result.filename.replace(/\.pdf$/i, '')}-report.pdf`)
    } catch (err) {
      setDownloadError(err.message)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!logFile) return

    setStatus('loading')
    setError(null)
    setResult(null)

    try {
      const data = await reviewLog(logFile, labFiles)
      setResult(data)
      setStatus('done')
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  const noLabReportsFound =
    result && result.lab_reports_provided.atterberg_samples === 0 && result.lab_reports_provided.psd_samples === 0

  return (
    <>
      <h1>Borehole Log Review</h1>
      <p className="subtitle">
        Upload a borehole, pavement dip, test pit, or cored borehole log PDF to check it against
        the AECOM logging standard. This is the review step — nothing is saved.
      </p>

      <form onSubmit={handleSubmit} className="log-review-form">
        <div className="log-review-field">
          <label htmlFor="log-file">Borehole/pavement dip/test pit log PDF</label>
          <input
            id="log-file"
            type="file"
            accept="application/pdf"
            onChange={(e) => setLogFile(e.target.files?.[0] ?? null)}
          />
        </div>

        <div className="log-review-field log-review-lab-field">
          <label htmlFor="lab-files">
            Lab report PDFs for this project <span className="optional-tag">(optional, but recommended)</span>
          </label>
          <p className="lab-field-callout">
            Attaching Atterberg/PSD lab reports for this hole unlocks the lab cross-reference
            checks — comparing the field-logged plasticity term and USCS symbol against the
            lab's actual measured LL/PI/grading. These are some of the most valuable findings
            this review produces. Without a lab report attached, those specific checks are
            skipped, not passed.
          </p>
          <input
            id="lab-files"
            type="file"
            accept="application/pdf"
            multiple
            onChange={(e) => setLabFiles(Array.from(e.target.files ?? []))}
          />
          {labFiles.length > 0 && (
            <p className="lab-files-selected">{labFiles.length} lab report(s) selected: {labFiles.map((f) => f.name).join(', ')}</p>
          )}
        </div>

        <button type="submit" disabled={!logFile || status === 'loading'} className="review-submit-button">
          {status === 'loading' ? 'Reviewing…' : 'Review this log'}
        </button>
        <p className="review-cost-note">
          This runs a real AI-assisted review (one API call per log page) — it isn't free, so it
          only runs when you click the button above.
        </p>
      </form>

      {error && <p className="error">Error: {error}</p>}

      {result && (
        <div className="log-review-results">
          <p className="summary">
            Reviewed <strong>{result.filename}</strong> — {Object.keys(result.holes).length} hole(s) found.
          </p>

          {noLabReportsFound && (
            <p className="no-lab-reports-banner">
              No lab reports were attached to this review — lab cross-reference checks below are
              shown as <strong>not checked</strong>, not passed.
            </p>
          )}

          <HoleTabs holes={result.holes} judgmentModel={result.judgment_model} />

          <button type="button" onClick={handleDownloadReport} className="review-submit-button">
            Download report (PDF)
          </button>
          {downloadError && <p className="error">Error: {downloadError}</p>}

          <details className="raw-json">
            <summary>Raw JSON response</summary>
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </details>
        </div>
      )}
    </>
  )
}
