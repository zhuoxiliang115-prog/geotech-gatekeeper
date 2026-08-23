import { useState } from 'react'
import { categoricalColor, INK } from '../theme'
import './AtterbergChart.css'

// Standard AS 1726 Casagrande plasticity chart: A-line, U-line, the LL=35
// and LL=50 dividers, the CL-ML borderline zone, and the "rarely
// encountered in nature" zone above the U-line - built as a plain SVG
// rather than composed from chart-library primitives, since none of those
// pieces are a standard line/scatter/bar shape and forcing them through
// one would be more fragile than direct geometry.

const A_LINE_SLOPE = 0.73
const A_LINE_INTERCEPT = -20 // PI = 0.73 * (LL - 20)
const U_LINE_SLOPE = 0.9
const U_LINE_INTERCEPT = -8 // PI = 0.9 * (LL - 8)

const aLine = (ll) => A_LINE_SLOPE * (ll + A_LINE_INTERCEPT)
const uLine = (ll) => U_LINE_SLOPE * (ll + U_LINE_INTERCEPT)
const aLineInverseLL = (pi) => pi / A_LINE_SLOPE - A_LINE_INTERCEPT
const uLineInverseLL = (pi) => pi / U_LINE_SLOPE - U_LINE_INTERCEPT

const PLOT = { left: 56, right: 16, top: 16, bottom: 44 }
const VIEW_W = 760
const VIEW_H = 520

const CL_ML_BOX = [
  [16, 4],
  [aLineInverseLL(4), 4],
  [aLineInverseLL(7), 7],
  [16, 7],
]

const REGION_LABELS = [
  { text: 'CH or OH', ll: 63, pi: 37 },
  { text: 'CI or OI', ll: 41, pi: 21 },
  { text: 'CL or OL', ll: 27, pi: 15 },
  { text: 'MH or OH', ll: 60, pi: 9 },
  { text: 'ML or OL', ll: 34, pi: 3 },
]

export default function AtterbergChart({ samples }) {
  const points = samples.filter((s) => s.liquid_limit != null && s.plasticity_index != null)
  const [hovered, setHovered] = useState(null)
  if (points.length === 0) return null

  const llMax = Math.max(80, Math.ceil(Math.max(...points.map((p) => p.liquid_limit)) / 10) * 10)
  const piMax = Math.max(60, Math.ceil(Math.max(...points.map((p) => p.plasticity_index)) / 10) * 10)
  const plotW = VIEW_W - PLOT.left - PLOT.right
  const plotH = VIEW_H - PLOT.top - PLOT.bottom

  const X = (ll) => PLOT.left + (ll / llMax) * plotW
  const Y = (pi) => VIEW_H - PLOT.bottom - (pi / piMax) * plotH

  const xTicks = Array.from({ length: llMax / 10 + 1 }, (_, i) => i * 10)
  const yTicks = Array.from({ length: piMax / 10 + 1 }, (_, i) => i * 10)

  // A-line: visible from PI=0 (LL=20) up to the right edge.
  const aLineFrom = { ll: 20, pi: 0 }
  const aLineTo = { ll: llMax, pi: Math.min(aLine(llMax), piMax) }

  // U-line: visible from PI=0 (LL=8) up to wherever it exits the plot.
  const uLineFrom = { ll: 8, pi: 0 }
  const uLineToLL = Math.min(llMax, uLineInverseLL(piMax))
  const uLineTo = { ll: uLineToLL, pi: uLine(uLineToLL) }

  // Shaded "rarely encountered" zone above the U-line.
  const shadedZone = [
    [0, 0],
    [0, piMax],
    [uLineToLL, piMax],
    [8, 0],
  ]

  // LL=50 divider: axis up to the U-line (or plot top if the U-line is
  // already off-chart there).
  const divider50Top = Math.min(uLine(50), piMax)
  // LL=35 divider: A-line up to the U-line.
  const divider35Bottom = aLine(35)
  const divider35Top = uLine(35)

  return (
    <div className="atterberg-chart-layout">
      <svg
        className="atterberg-chart-main"
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        role="img"
        aria-label="Atterberg plasticity chart"
      >
        {/* shaded zone above U-line */}
        <polygon
          points={shadedZone.map(([ll, pi]) => `${X(ll)},${Y(pi)}`).join(' ')}
          fill="#e1e0d9"
          opacity={0.6}
        />

        {/* gridlines */}
        {xTicks.map((ll) => (
          <line key={`gx-${ll}`} x1={X(ll)} y1={Y(0)} x2={X(ll)} y2={Y(piMax)} stroke={INK.gridline} strokeWidth={1} />
        ))}
        {yTicks.map((pi) => (
          <line key={`gy-${pi}`} x1={X(0)} y1={Y(pi)} x2={X(llMax)} y2={Y(pi)} stroke={INK.gridline} strokeWidth={1} />
        ))}

        {/* plot border */}
        <rect x={X(0)} y={Y(piMax)} width={plotW} height={plotH} fill="none" stroke={INK.axis} strokeWidth={1} />

        {/* A-line / U-line */}
        <line x1={X(aLineFrom.ll)} y1={Y(aLineFrom.pi)} x2={X(aLineTo.ll)} y2={Y(aLineTo.pi)} stroke={INK.primary} strokeWidth={1.5} />
        <line
          x1={X(uLineFrom.ll)}
          y1={Y(uLineFrom.pi)}
          x2={X(uLineTo.ll)}
          y2={Y(uLineTo.pi)}
          stroke={INK.primary}
          strokeWidth={1}
          strokeDasharray="5 4"
        />

        {/* CL-ML box */}
        <polygon
          points={CL_ML_BOX.map(([ll, pi]) => `${X(ll)},${Y(pi)}`).join(' ')}
          fill="none"
          stroke={INK.primary}
          strokeWidth={1}
        />

        {/* LL=35 / LL=50 dividers */}
        <line x1={X(35)} y1={Y(divider35Bottom)} x2={X(35)} y2={Y(divider35Top)} stroke={INK.primary} strokeWidth={1} />
        <line x1={X(50)} y1={Y(0)} x2={X(50)} y2={Y(divider50Top)} stroke={INK.primary} strokeWidth={1} />

        {/* axis ticks + labels */}
        {xTicks.map((ll) => (
          <text key={`xt-${ll}`} x={X(ll)} y={Y(0) + 16} textAnchor="middle" fontSize={11} fill={INK.muted}>
            {ll}
          </text>
        ))}
        {yTicks.map((pi) => (
          <text key={`yt-${pi}`} x={X(0) - 8} y={Y(pi) + 4} textAnchor="end" fontSize={11} fill={INK.muted}>
            {pi}
          </text>
        ))}
        <text x={X(llMax / 2)} y={VIEW_H - 8} textAnchor="middle" fontSize={12} fill={INK.secondary}>
          Liquid Limit (%)
        </text>
        <text
          x={16}
          y={VIEW_H / 2}
          textAnchor="middle"
          fontSize={12}
          fill={INK.secondary}
          transform={`rotate(-90, 16, ${VIEW_H / 2})`}
        >
          Plasticity Index (%)
        </text>

        {/* region labels */}
        {REGION_LABELS.map((r) => (
          <text key={r.text} x={X(r.ll)} y={Y(r.pi)} textAnchor="middle" fontSize={11} fill={INK.secondary}>
            {r.text}
          </text>
        ))}
        <text x={X(20.5)} y={Y(5.5)} textAnchor="start" fontSize={9} fill={INK.secondary}>
          CL-ML
        </text>
        <text x={X(llMax) - 4} y={Y(aLineTo.pi) - 6} textAnchor="end" fontSize={10} fill={INK.primary}>
          "A" line: PI = 0.73(LL-20)
        </text>
        <text x={X(uLineTo.ll) - 4} y={Y(uLineTo.pi) - 6} textAnchor="end" fontSize={10} fill={INK.primary}>
          "U" line: PI = 0.9(LL-8)
        </text>

        {/* sample points */}
        {points.map((s, i) => (
          <circle
            key={s.mg_sample_no ?? i}
            cx={X(s.liquid_limit)}
            cy={Y(s.plasticity_index)}
            r={5}
            fill={categoricalColor(i)}
            stroke="#fff"
            strokeWidth={1}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
          />
        ))}
        {hovered != null && (
          <text
            x={X(points[hovered].liquid_limit) + 8}
            y={Y(points[hovered].plasticity_index) - 8}
            fontSize={11}
            fill={INK.primary}
          >
            {`${points[hovered].sample_id ?? points[hovered].mg_sample_no}: LL ${points[hovered].liquid_limit} / PI ${points[hovered].plasticity_index}`}
          </text>
        )}
      </svg>

      <div className="chart-side-legend">
        {points.map((s, i) => (
          <div className="chart-side-legend-item" key={s.mg_sample_no ?? i}>
            <span className="chart-side-legend-dot" style={{ background: categoricalColor(i) }} />
            {s.sample_id ?? s.mg_sample_no ?? `Sample ${i + 1}`}
          </div>
        ))}
      </div>
    </div>
  )
}
