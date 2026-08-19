import { useState } from 'react'
import { uploadReport } from './api'
import AtterbergSection from './components/AtterbergSection'
import CbrSection from './components/CbrSection'
import ChemicalCoaSection from './components/ChemicalCoaSection'
import EmersonSection from './components/EmersonSection'
import PointLoadSection from './components/PointLoadSection'
import PsdSection from './components/PsdSection'
import SmddSection from './components/SmddSection'
import './App.css'

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

          <EmersonSection results={result.emerson_results} />
          <AtterbergSection results={result.atterberg_results} />
          <PsdSection results={result.psd_results} />
          <SmddSection results={result.smdd_results} />
          <CbrSection results={result.cbr_results} />
          <PointLoadSection results={result.point_load_results} />
          <ChemicalCoaSection results={result.chemical_coa_results} />

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
