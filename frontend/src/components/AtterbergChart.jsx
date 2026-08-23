import {
  CartesianGrid,
  Legend,
  Line,
  ComposedChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { categoricalColor, INK } from '../theme'

const PI_MAX = 60

// Both lines are trimmed to stay within the chart's PI domain (0-60) -
// the U-line's formula would otherwise overshoot it well before LL=100.
const A_LINE = Array.from({ length: 17 }, (_, i) => {
  const ll = 20 + i * 5
  return { ll, pi: 0.73 * (ll - 20) }
}).filter((p) => p.pi <= PI_MAX)

const U_LINE = Array.from({ length: 18 }, (_, i) => {
  const ll = 16 + i * 5
  return { ll, pi: 0.9 * (ll - 8) }
}).filter((p) => p.pi <= PI_MAX)

/**
 * Atterberg plasticity chart: LL vs PI scatter with the A-line and U-line
 * reference lines (spec chart 2). Each sample point gets dashed guide
 * lines down to each axis and an "LL {v} / PI {v}" label, matching the
 * annotation style on every Macquarie Geotech Atterberg PDF.
 */
export default function AtterbergChart({ samples }) {
  const points = samples.filter((s) => s.liquid_limit != null && s.plasticity_index != null)
  if (points.length === 0) return null

  // Legend needs one entry per sample (so each dot's identity is readable)
  // plus A-line/U-line - reserve enough height that it doesn't feel cramped
  // as the sample count grows, matching the PDF's own labeled-point style.
  const legendItemCount = points.length + 2
  const legendRows = Math.ceil(legendItemCount / 4)
  const legendHeight = legendRows * 24 + 12
  const chartHeight = 360 + legendHeight

  return (
    <>
    <ResponsiveContainer width="100%" height={chartHeight}>
      <ComposedChart margin={{ top: 8, right: 24, bottom: 24, left: 8 }}>
        <CartesianGrid stroke={INK.gridline} strokeDasharray="2 2" />
        <XAxis
          dataKey="ll"
          type="number"
          domain={[0, 100]}
          label={{ value: 'Liquid Limit (%)', position: 'insideBottom', offset: -12, fill: INK.secondary }}
          stroke={INK.axis}
          tick={{ fill: INK.muted, fontSize: 12 }}
        />
        <YAxis
          dataKey="pi"
          type="number"
          domain={[0, 60]}
          label={{ value: 'Plasticity Index (%)', angle: -90, position: 'insideLeft', fill: INK.secondary }}
          stroke={INK.axis}
          tick={{ fill: INK.muted, fontSize: 12 }}
        />
        <Tooltip
          formatter={(value, name) => [value, name]}
          labelFormatter={() => ''}
        />
        <Legend
          verticalAlign="top"
          height={legendHeight}
          wrapperStyle={{ fontSize: 12, color: INK.secondary, lineHeight: '24px', paddingBottom: 8 }}
        />

        <Line data={A_LINE} dataKey="pi" stroke={INK.muted} strokeWidth={1.5} dot={false} isAnimationActive={false} name="A-line" />
        <Line data={U_LINE} dataKey="pi" stroke={INK.muted} strokeWidth={1} strokeDasharray="4 3" dot={false} isAnimationActive={false} name="U-line" />

        {points.map((s, i) => (
          <ReferenceLine
            key={`guide-x-${s.mg_sample_no ?? i}`}
            segment={[{ x: s.liquid_limit, y: 0 }, { x: s.liquid_limit, y: s.plasticity_index }]}
            stroke={categoricalColor(i)}
            strokeDasharray="3 3"
          />
        ))}
        {points.map((s, i) => (
          <ReferenceLine
            key={`guide-y-${s.mg_sample_no ?? i}`}
            segment={[{ x: 0, y: s.plasticity_index }, { x: s.liquid_limit, y: s.plasticity_index }]}
            stroke={categoricalColor(i)}
            strokeDasharray="3 3"
          />
        ))}

        {points.map((s, i) => (
          <Scatter
            key={`point-${s.mg_sample_no ?? i}`}
            data={[{ ll: s.liquid_limit, pi: s.plasticity_index }]}
            dataKey="pi"
            name={s.sample_id ?? s.mg_sample_no ?? `Sample ${i + 1}`}
            fill={categoricalColor(i)}
            shape={(props) => <circle cx={props.cx} cy={props.cy} r={6} fill={categoricalColor(i)} stroke="#fff" strokeWidth={1} />}
            label={({ x, y }) => (
              <text x={x + 8} y={y - 8} fontSize={11} fill={INK.primary}>
                {`LL ${s.liquid_limit} / PI ${s.plasticity_index}`}
              </text>
            )}
            isAnimationActive={false}
          />
        ))}
      </ComposedChart>
    </ResponsiveContainer>
    <p className="chart-caption">
      A-line: PI = 0.73×(LL−20) — CLAY above, SILT below. U-line: PI = 0.9×(LL−8), the upper bound
      for naturally occurring soils.
    </p>
    </>
  )
}
