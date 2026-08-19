import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { eceSalinity, MF_TABLE, ECE_TABLE } from '../calculations'
import { SEQUENTIAL_BLUE, INK } from '../theme'
import './SalinityChart.css'

/**
 * Soil salinity (ECe) classification, spec chart 8. MF is a manual
 * per-sample number input (not auto-detected - it reflects a hand-feel
 * texture assessment the parser can't determine from lab data), with
 * Table 6.1 shown alongside so the person entering it can look the value
 * up rather than guess. Bars are color-coded by classification band and
 * update live as MF changes.
 */
export default function SalinityChart({ samples }) {
  const [mfValues, setMfValues] = useState({})

  const setMf = (key, value) => {
    const parsed = value === '' ? null : parseFloat(value)
    setMfValues((prev) => ({ ...prev, [key]: Number.isFinite(parsed) ? parsed : null }))
  }

  const rows = samples
    .filter((s) => s.ec_us_cm != null)
    .map((s, i) => {
      const key = s.mg_sample_no ?? s.lab_reference ?? s.sample_id ?? i
      const mf = mfValues[key] ?? null
      const result = mf != null ? eceSalinity(s.ec_us_cm, mf) : null
      return {
        key,
        sample: s.sample_id ?? s.mg_sample_no ?? `Sample ${i + 1}`,
        ec15: s.ec_us_cm / 1000,
        mf,
        ece: result?.ece ?? null,
        className: result?.className ?? null,
      }
    })

  const chartData = rows.filter((r) => r.ece != null)

  return (
    <div>
      {chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={Math.max(120, chartData.length * 44)}>
          <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
            <CartesianGrid stroke={INK.gridline} strokeDasharray="2 2" horizontal={false} />
            <XAxis
              type="number"
              domain={[0, (max) => Math.max(18, max * 1.1)]}
              label={{ value: 'ECe (dS/m)', position: 'insideBottom', offset: -4, fill: INK.secondary }}
              stroke={INK.axis}
              tick={{ fill: INK.muted, fontSize: 12 }}
            />
            <YAxis type="category" dataKey="sample" width={110} stroke={INK.axis} tick={{ fill: INK.muted, fontSize: 12 }} />
            <Tooltip formatter={(value, name, p) => [`${value} dS/m (${p.payload.className})`, 'ECe']} />
            <Bar dataKey="ece" radius={[0, 4, 4, 0]} isAnimationActive={false}>
              {chartData.map((r) => (
                <Cell key={r.key} fill={SEQUENTIAL_BLUE[r.className]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}

      <div className="table-scroll">
        <table className="salinity-table">
          <thead>
            <tr>
              <th>Sample</th>
              <th>EC(1:5) (dS/m)</th>
              <th>MF</th>
              <th>ECe (dS/m)</th>
              <th>Class</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key}>
                <td>{r.sample}</td>
                <td>{r.ec15.toFixed(3)}</td>
                <td>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={r.mf ?? ''}
                    placeholder="enter MF"
                    onChange={(e) => setMf(r.key, e.target.value)}
                  />
                </td>
                <td>{r.ece != null ? r.ece.toFixed(2) : '—'}</td>
                <td>{r.className ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <details className="mf-reference">
        <summary>Table 6.1 — soil texture → Multiplication Factor reference</summary>
        <table className="mf-table">
          <thead>
            <tr>
              <th>Texture</th>
              <th>Description</th>
              <th>MF</th>
            </tr>
          </thead>
          <tbody>
            {MF_TABLE.map((row) => (
              <tr key={row.texture}>
                <td>{row.texture}</td>
                <td>{row.description}</td>
                <td>{row.mf}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>

      <details className="mf-reference">
        <summary>Table 6.2 — ECe salinity classes</summary>
        <table className="mf-table">
          <thead>
            <tr>
              <th>Class</th>
              <th>ECe (dS/m)</th>
              <th>Comments</th>
            </tr>
          </thead>
          <tbody>
            {ECE_TABLE.map((row) => (
              <tr key={row.className}>
                <td>{row.className}</td>
                <td>{row.range}</td>
                <td>{row.comment}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}
