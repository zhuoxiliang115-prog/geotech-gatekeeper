import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { categoricalColor, INK } from '../theme'
import './PsdChart.css'

// Fixed AS 1726 particle-size domain and classification bands, matching
// the firm's standard chart template (Clay/Silt/Sand/Gravel header aligned
// to the log-x axis) rather than trimming to whatever sieve sizes a given
// sample happens to report - the header needs the full framework to make
// sense. Boundaries per the AECOM field logging guide: 0.002 (clay/silt),
// 0.075 (silt/sand), 0.2 / 0.6 (sand fine/medium/coarse), 2.36 (sand/
// gravel), 6 / 20 (gravel fine/medium/coarse). Gravel Coarse is shown
// capped at the chart's right edge (100mm) rather than adding separate
// Cobbles/Boulders columns, matching the reference template.
const DOMAIN_MIN = 0.001
const DOMAIN_MAX = 100
const DECADES = [0.001, 0.01, 0.1, 1, 10, 100]

function bandWidthPct(from, to) {
  const logMin = Math.log10(DOMAIN_MIN)
  const logMax = Math.log10(DOMAIN_MAX)
  return ((Math.log10(to) - Math.log10(from)) / (logMax - logMin)) * 100
}

const BAND_WIDTHS = {
  clay: bandWidthPct(0.001, 0.002),
  silt: bandWidthPct(0.002, 0.075),
  sandFine: bandWidthPct(0.075, 0.2),
  sandMedium: bandWidthPct(0.2, 0.6),
  sandCoarse: bandWidthPct(0.6, 2.36),
  gravelFine: bandWidthPct(2.36, 6),
  gravelMedium: bandWidthPct(6, 20),
  gravelCoarse: bandWidthPct(20, 100),
}

const Y_AXIS_WIDTH = 56
const RIGHT_PAD = 12

const MINOR_MULTIPLES = [2, 3, 4, 5, 6, 7, 8, 9]
const ALL_TICKS = [
  ...DECADES,
  ...DECADES.slice(0, -1).flatMap((d) => MINOR_MULTIPLES.map((m) => m * d)),
].filter((v) => v >= DOMAIN_MIN && v <= DOMAIN_MAX)
  .sort((a, b) => a - b)

const Y_TICKS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

function XAxisTick({ x, y, payload }) {
  if (!DECADES.includes(payload.value)) return null
  return (
    <text x={x} y={y + 12} textAnchor="middle" fontSize={11} fill={INK.muted}>
      {payload.value}
    </text>
  )
}

function ClassificationHeader() {
  return (
    <div className="psd-header-wrap" style={{ paddingLeft: Y_AXIS_WIDTH, paddingRight: RIGHT_PAD }}>
      <table className="psd-classification-header">
        <colgroup>
          <col style={{ width: `${BAND_WIDTHS.clay}%` }} />
          <col style={{ width: `${BAND_WIDTHS.silt}%` }} />
          <col style={{ width: `${BAND_WIDTHS.sandFine}%` }} />
          <col style={{ width: `${BAND_WIDTHS.sandMedium}%` }} />
          <col style={{ width: `${BAND_WIDTHS.sandCoarse}%` }} />
          <col style={{ width: `${BAND_WIDTHS.gravelFine}%` }} />
          <col style={{ width: `${BAND_WIDTHS.gravelMedium}%` }} />
          <col style={{ width: `${BAND_WIDTHS.gravelCoarse}%` }} />
        </colgroup>
        <tbody>
          <tr>
            <td rowSpan={2}>CLAY</td>
            <td rowSpan={2}>SILT</td>
            <td colSpan={3}>SAND</td>
            <td colSpan={3}>GRAVEL</td>
          </tr>
          <tr>
            <td>Fine</td>
            <td>Medium</td>
            <td>Coarse</td>
            <td>Fine</td>
            <td>Medium</td>
            <td>Coarse</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

/**
 * PSD grading curve matching the firm's standard chart template: log-x
 * particle size with a Clay/Silt/Sand/Gravel classification header
 * aligned to the axis, dense log-scale gridlines, and a side legend.
 */
export default function PsdChart({ samples }) {
  if (samples.length === 0) return null

  return (
    <div className="psd-chart-layout">
      <div className="psd-chart-main">
        <ClassificationHeader />
        <ResponsiveContainer width="100%" height={420}>
          <LineChart margin={{ top: 4, right: RIGHT_PAD, bottom: 30, left: 0 }}>
            <CartesianGrid stroke={INK.gridline} />
            <XAxis
              dataKey="sieve_mm"
              type="number"
              scale="log"
              domain={[DOMAIN_MIN, DOMAIN_MAX]}
              ticks={ALL_TICKS}
              interval={0}
              allowDuplicatedCategory={false}
              tick={<XAxisTick />}
              label={{ value: 'Particle Size (mm)', position: 'insideBottom', offset: -20, fill: INK.secondary }}
              stroke={INK.axis}
            />
            <YAxis
              width={Y_AXIS_WIDTH}
              domain={[0, 100]}
              ticks={Y_TICKS}
              label={{ value: 'Percentage Passing (%)', angle: -90, position: 'insideLeft', fill: INK.secondary }}
              stroke={INK.axis}
              tick={{ fill: INK.muted, fontSize: 11 }}
            />
            <Tooltip formatter={(value, name) => [`${value}%`, name]} labelFormatter={(v) => `${v} mm`} />
            {samples.map((sample, i) => (
              <Line
                key={sample.mg_sample_no ?? i}
                data={sample.readings}
                dataKey="passing_pct"
                name={sample.sample_id ?? sample.mg_sample_no ?? `Sample ${i + 1}`}
                stroke={categoricalColor(i)}
                strokeWidth={1.75}
                dot={false}
                activeDot={{ r: 4 }}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="chart-side-legend">
        {samples.map((sample, i) => (
          <div className="chart-side-legend-item" key={sample.mg_sample_no ?? i}>
            <span className="chart-side-legend-swatch" style={{ background: categoricalColor(i) }} />
            {sample.sample_id ?? sample.mg_sample_no ?? `Sample ${i + 1}`}
          </div>
        ))}
      </div>
    </div>
  )
}
