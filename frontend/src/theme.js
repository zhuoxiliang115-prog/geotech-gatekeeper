// Chart color tokens - the validated categorical palette (fixed order,
// never cycled per-series) plus chart chrome/ink from the dataviz skill's
// reference palette. Matches the "clean axis labels, blue markers/lines"
// look of the existing lab PDF reports: blue is the default single-series
// hue everywhere, with the categorical order used only when a chart
// genuinely has multiple identity series (e.g. one line per PSD sample).

export const CATEGORICAL = [
  '#2a78d6', // blue
  '#eb6834', // orange
  '#1baf7a', // aqua
  '#eda100', // yellow
  '#e87ba4', // magenta
  '#008300', // green
  '#4a3aa7', // violet
  '#e34948', // red
]

export const SERIES_BLUE = CATEGORICAL[0]

export const INK = {
  primary: '#0b0b0b',
  secondary: '#52514e',
  muted: '#898781',
  gridline: '#e1e0d9',
  axis: '#c3c2b7',
}

export const SURFACE = '#fcfcfb'

export function categoricalColor(index) {
  return CATEGORICAL[index % CATEGORICAL.length]
}

// Sequential blue ramp (light -> dark), for ordered severity bands like
// the ECe salinity classes - a magnitude scale, not a set of identities.
export const SEQUENTIAL_BLUE = {
  'Non-saline': '#9ec5f4',
  'Slightly saline': '#6da7ec',
  'Moderately saline': '#2a78d6',
  'Very saline': '#1c5cab',
  'Highly saline': '#0d366b',
}
