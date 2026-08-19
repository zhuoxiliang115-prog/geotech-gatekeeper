import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { SERIES_BLUE, INK } from '../theme'

/**
 * Emerson class bar chart: one bar per sample, class number 1-8, matching
 * the spreadsheet's own bar chart (spec chart 6). No calculation involved
 * - it's a direct lab observation, so this is presentation-only.
 */
export default function EmersonChart({ samples }) {
  const data = samples.map((s) => ({
    name: s.sample_id ?? s.mg_sample_no,
    emerson_class: s.emerson_class,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 8, right: 24, bottom: 24, left: 8 }}>
        <CartesianGrid stroke={INK.gridline} strokeDasharray="2 2" vertical={false} />
        <XAxis dataKey="name" stroke={INK.axis} tick={{ fill: INK.muted, fontSize: 12 }} />
        <YAxis
          domain={[0, 8]}
          allowDecimals={false}
          label={{ value: 'Emerson Class Number', angle: -90, position: 'insideLeft', fill: INK.secondary }}
          stroke={INK.axis}
          tick={{ fill: INK.muted, fontSize: 12 }}
        />
        <Tooltip />
        <Bar dataKey="emerson_class" fill={SERIES_BLUE} radius={[4, 4, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}
