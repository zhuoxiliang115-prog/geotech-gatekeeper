import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'
import { SERIES_BLUE, INK } from '../theme'
import './PointLoadTable.css'

const FAILURE_MODE_KEY = {
  1: 'Fracture through fabric of specimen oblique to bedding, not influenced by weak planes.',
  2: 'Fracture along bedding.',
  3: 'Fracture influenced by pre-existing plane, microfracture, vein or chemical alteration.',
  4: 'Chip or partial fracture.',
}

function depthFromSampleId(sampleId) {
  // Sample IDs look like "ABH01 0.3-0.4m" - take the midpoint of the depth range.
  const match = /([\d.]+)-([\d.]+)m/.exec(sampleId ?? '')
  if (!match) return null
  return (parseFloat(match[1]) + parseFloat(match[2])) / 2
}

/**
 * Point Load results as a table (matches the PDF exactly, per spec chart
 * 5), plus an Is50-vs-depth scatter as the suggested secondary view.
 */
export default function PointLoadTable({ readings }) {
  const depthPoints = readings
    .map((r) => ({ ...r, depth: depthFromSampleId(r.sample_id) }))
    .filter((r) => r.depth != null && r.corrected_is50 != null)

  return (
    <div>
      <div className="table-scroll">
        <table className="point-load-table">
          <thead>
            <tr>
              <th>MG Sample No.</th>
              <th>Sample ID</th>
              <th>Test Type</th>
              <th>Failure Load (kN)</th>
              <th>Is</th>
              <th>Is50</th>
              <th>Failure Mode</th>
            </tr>
          </thead>
          <tbody>
            {readings.map((r, i) => (
              <tr key={`${r.mg_sample_no}-${r.test_type}-${i}`}>
                <td>{r.mg_sample_no}</td>
                <td>{r.sample_id}</td>
                <td>{r.test_type}</td>
                <td>{r.failure_load_kn}</td>
                <td>{r.uncorrected_is}</td>
                <td>{r.corrected_is50}</td>
                <td>{r.failure_mode}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="failure-mode-key">
        <strong>Failure Mode Key:</strong>
        <ul>
          {Object.entries(FAILURE_MODE_KEY).map(([mode, desc]) => (
            <li key={mode}>{mode} — {desc}</li>
          ))}
        </ul>
      </div>

      {depthPoints.length > 1 && (
        <>
          <h4 className="secondary-chart-title">Is50 vs depth</h4>
          <ResponsiveContainer width="100%" height={280}>
            <ScatterChart margin={{ top: 8, right: 24, bottom: 24, left: 8 }}>
              <CartesianGrid stroke={INK.gridline} strokeDasharray="2 2" />
              <XAxis
                dataKey="depth"
                type="number"
                name="Depth"
                unit="m"
                label={{ value: 'Depth (m)', position: 'insideBottom', offset: -12, fill: INK.secondary }}
                stroke={INK.axis}
                tick={{ fill: INK.muted, fontSize: 12 }}
              />
              <YAxis
                dataKey="corrected_is50"
                type="number"
                name="Is50"
                label={{ value: 'Is50', angle: -90, position: 'insideLeft', fill: INK.secondary }}
                stroke={INK.axis}
                tick={{ fill: INK.muted, fontSize: 12 }}
              />
              <Tooltip formatter={(value, name) => [value, name]} cursor={{ strokeDasharray: '3 3' }} />
              <Scatter data={depthPoints} fill={SERIES_BLUE} isAnimationActive={false} />
            </ScatterChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  )
}
