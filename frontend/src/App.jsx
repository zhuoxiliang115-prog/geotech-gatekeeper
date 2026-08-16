import { useState } from 'react'
import { uploadReport } from './api'
import './App.css'

function ReportSection({ title, rows, renderRow }) {
  if (!rows || rows.length === 0) return null
  return (
    <section className="result-section">
      <h2>{title} ({rows.length})</h2>
      {rows.map((row, i) => (
        <div className="result-card" key={i}>
          {renderRow(row)}
        </div>
      ))}
    </section>
  )
}

function EmersonRow({ row }) {
  return (
    <dl>
      <dt>Sample</dt>
      <dd>{row.mg_sample_no ?? '—'} ({row.sample_id ?? '—'})</dd>
      <dt>Description</dt>
      <dd>{row.sample_description ?? '—'}</dd>
      <dt>Raw value: Emerson Class</dt>
      <dd>{row.emerson_class ?? '—'}</dd>
      <dt>Lookup applied: dispersion table</dt>
      <dd>{row.dispersion_potential ?? '—'}</dd>
      <dt>Notes</dt>
      <dd>{row.notes ?? '—'}</dd>
    </dl>
  )
}

function AtterbergRow({ row }) {
  return (
    <dl>
      <dt>Sample</dt>
      <dd>{row.mg_sample_no ?? '—'} ({row.sample_id ?? '—'})</dd>
      <dt>Raw values: LL / PL / PI</dt>
      <dd>
        {row.liquid_limit ?? '—'} / {row.plastic_limit ?? '—'} / {row.plasticity_index ?? '—'}
      </dd>
      <dt>Formula applied: A-line PI = 0.73(LL-20)</dt>
      <dd>{row.a_line_pi_at_this_ll ?? '—'}</dd>
      <dt>Classification</dt>
      <dd>{row.classification_zone ?? '—'}</dd>
    </dl>
  )
}

function PsdRow({ row }) {
  return (
    <dl>
      <dt>Sample</dt>
      <dd>{row.mg_sample_no ?? '—'} ({row.sample_id ?? '—'})</dd>
      <dt>Readings (sieve mm → % passing)</dt>
      <dd>
        {row.readings.map((r) => `${r.sieve_mm}→${r.passing_pct}%`).join(', ')}
      </dd>
    </dl>
  )
}

function App() {
  const [file, setFile] = useState(null)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!file) return

    setStatus('loading')
    setError(null)
    setResult(null)

    try {
      const data = await uploadReport(file)
      setResult(data)
      setStatus('done')
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  return (
    <main className="app">
      <h1>Geotech Lab Report Upload</h1>
      <p className="subtitle">
        Upload a Macquarie Geotech report PDF to see what gets extracted.
        This is the review step — nothing is saved yet.
      </p>

      <form onSubmit={handleSubmit} className="upload-form">
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button type="submit" disabled={!file || status === 'loading'}>
          {status === 'loading' ? 'Parsing…' : 'Upload & Parse'}
        </button>
      </form>

      {error && <p className="error">Error: {error}</p>}

      {result && (
        <div className="results">
          <p className="summary">
            Parsed {result.pages_parsed} page(s) from <strong>{result.filename}</strong>
          </p>

          <ReportSection
            title="Emerson Class"
            rows={result.emerson_results}
            renderRow={(row) => <EmersonRow row={row} />}
          />
          <ReportSection
            title="Atterberg / Plasticity Index"
            rows={result.atterberg_results}
            renderRow={(row) => <AtterbergRow row={row} />}
          />
          <ReportSection
            title="Particle Size Distribution"
            rows={result.psd_results}
            renderRow={(row) => <PsdRow row={row} />}
          />

          {result.unrecognized_pages?.length > 0 && (
            <section className="result-section">
              <h2>Unrecognized pages ({result.unrecognized_pages.length})</h2>
              <p>These need manual entry — no parser matched the report title.</p>
              <ul>
                {result.unrecognized_pages.map((p) => (
                  <li key={p.page}>
                    Page {p.page}: "{p.title}"
                  </li>
                ))}
              </ul>
            </section>
          )}

          <details className="raw-json">
            <summary>Raw JSON response</summary>
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </details>
        </div>
      )}
    </main>
  )
}

export default App
