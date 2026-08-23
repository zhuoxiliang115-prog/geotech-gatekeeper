import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { categoricalColor, INK } from '../theme'

/**
 * PSD grading curve: % passing vs sieve size, log-x, one line per sample,
 * circular markers - matching the spec's chart 1 and the PDF's own style.
 */
export default function PsdChart({ samples }) {
  const allSizes = samples.flatMap((s) => s.readings.map((r) => r.sieve_mm))
  if (allSizes.length === 0) return null
  const domain = [Math.min(...allSizes), Math.max(...allSizes)]

  // Reserve enough legend height for however many samples there are, so it
  // doesn't wrap into a cramped block as the sample count grows.
  const legendRows = samples.length > 1 ? Math.ceil(samples.length / 4) : 0
  const legendHeight = legendRows > 0 ? legendRows * 24 + 12 : 0
  const chartHeight = 340 + legendHeight

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <LineChart margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid stroke={INK.gridline} strokeDasharray="2 2" />
        <XAxis
          dataKey="sieve_mm"
          type="number"
          scale="log"
          domain={domain}
          allowDuplicatedCategory={false}
          tickFormatter={(v) => (v >= 1 ? v : v.toFixed(3))}
          label={{ value: 'Sieve aperture (mm, log scale)', position: 'insideBottom', offset: -4, fill: INK.secondary }}
          stroke={INK.axis}
          tick={{ fill: INK.muted, fontSize: 12 }}
        />
        <YAxis
          domain={[0, 100]}
          label={{ value: '% Passing', angle: -90, position: 'insideLeft', fill: INK.secondary }}
          stroke={INK.axis}
          tick={{ fill: INK.muted, fontSize: 12 }}
        />
        <Tooltip formatter={(value, name) => [`${value}%`, name]} labelFormatter={(v) => `${v} mm`} />
        {samples.length > 1 && (
          <Legend
            verticalAlign="bottom"
            height={legendHeight}
            wrapperStyle={{ fontSize: 12, color: INK.secondary, lineHeight: '24px', paddingTop: 8 }}
          />
        )}
        {samples.map((sample, i) => (
          <Line
            key={sample.mg_sample_no ?? i}
            data={sample.readings}
            dataKey="passing_pct"
            name={sample.sample_id ?? sample.mg_sample_no ?? `Sample ${i + 1}`}
            stroke={categoricalColor(i)}
            strokeWidth={2}
            dot={{ r: 4, fill: categoricalColor(i) }}
            activeDot={{ r: 6 }}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
