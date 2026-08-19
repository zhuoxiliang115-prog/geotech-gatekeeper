// Client-side port of backend/app/calculations.py's AS 2159 and ECe
// salinity logic, used only where the app needs live recomputation from a
// manual per-sample input (Soil Condition A/B, salinity Multiplication
// Factor) without a network round-trip on every keystroke. Keep this in
// sync with the backend module by hand - Phase 2 is frontend-only, so the
// backend isn't touched, but the threshold tables must match exactly.
// See reference/charts-and-calculations-spec.md for the source tables.

export function plasticityIndex(ll, pl) {
  return ll - pl
}

export function pointLoadIs50(isValue, de) {
  return isValue * (de / 50) ** 0.45
}

function bandIndex(value, thresholds, higherIsWorse = true) {
  if (higherIsWorse) {
    for (let i = 0; i < thresholds.length; i++) {
      if (value < thresholds[i]) return i
    }
    return thresholds.length
  }
  for (let i = 0; i < thresholds.length; i++) {
    if (value > thresholds[i]) return i
  }
  return thresholds.length
}

export const CONCRETE_LABELS = {
  A: ['Mild', 'Moderate', 'Severe', 'Very severe'],
  B: ['Non-aggressive', 'Mild', 'Moderate', 'Severe'],
}

export function as2159ConcreteClass(soilCondition, { ph, sulfateSoilPpm, sulfateGwPpm, chlorideGwPpm } = {}) {
  const bandIndices = []
  if (sulfateSoilPpm != null) bandIndices.push(bandIndex(sulfateSoilPpm, [5000, 10000, 20000]))
  if (sulfateGwPpm != null) bandIndices.push(bandIndex(sulfateGwPpm, [1000, 3000, 10000]))
  if (ph != null) bandIndices.push(bandIndex(ph, [5.5, 4.5, 4], false))
  if (chlorideGwPpm != null) bandIndices.push(bandIndex(chlorideGwPpm, [6000, 12000, 30000]))

  if (bandIndices.length === 0) return null
  const governing = Math.max(...bandIndices)
  return CONCRETE_LABELS[soilCondition][governing]
}

export const STEEL_LABELS = {
  A: ['Non-aggressive', 'Mild', 'Moderate', 'Severe'],
  B: ['Non-aggressive', 'Non-aggressive', 'Mild', 'Moderate'],
}

export function as2159SteelClass(soilCondition, { ph, chlorideSoilPpm, chlorideGwPpm, resistivityOhmCm } = {}) {
  const bandIndices = []
  if (ph != null) bandIndices.push(bandIndex(ph, [5, 4, 3], false))
  if (chlorideSoilPpm != null) bandIndices.push(bandIndex(chlorideSoilPpm, [5000, 20000, 50000]))
  if (chlorideGwPpm != null) bandIndices.push(bandIndex(chlorideGwPpm, [1000, 10000, 20000]))
  if (resistivityOhmCm != null) bandIndices.push(bandIndex(resistivityOhmCm, [5000, 2000, 1000], false))

  if (bandIndices.length === 0) return null
  const governing = Math.max(...bandIndices)
  return STEEL_LABELS[soilCondition][governing]
}

const ECE_CLASS_BANDS = [
  [2, 'Non-saline'],
  [4, 'Slightly saline'],
  [8, 'Moderately saline'],
  [16, 'Very saline'],
]
const ECE_CLASS_ABOVE_TOP_BAND = 'Highly saline'

function eceClass(ece) {
  for (const [upperBound, label] of ECE_CLASS_BANDS) {
    if (ece < upperBound) return label
  }
  return ECE_CLASS_ABOVE_TOP_BAND
}

export function eceSalinity(ecUsCm, mf) {
  const ec15DsM = ecUsCm / 1000
  const ece = ec15DsM * mf
  return { ece, className: eceClass(ece) }
}

export const MF_TABLE = [
  { texture: 'Sands', description: 'Very little or no coherence; cannot be rolled into a stable ball. Individual sand grains adhere to fingers.', mf: 17 },
  { texture: 'Sandy loams', description: 'Some coherence, can be rolled into a stable ball but not a thread. Sand grains can be felt.', mf: 14 },
  { texture: 'Loams', description: 'Can be rolled into a thick thread, breaks up before 3-4mm thick. Smooth, spongy feel, no obvious sandiness.', mf: 10 },
  { texture: 'Clay loam', description: 'Can be rolled to a 3-4mm thread but with fractures along its length. Becoming plastic, capable of being moulded.', mf: 9 },
  { texture: 'Light clays', description: 'Rolls to a 3-4mm thread without fracture. Plastic, smooth feel, some resistance to rolling out.', mf: 8.5 },
  { texture: 'Light medium clay', description: 'Plastic and smooth to the touch; forms a ribbon of 7.5cm.', mf: 8 },
  { texture: 'Medium clay', description: 'Handles like plasticine, forms rods without fracture, some resistance to ribboning shear, ribbons to 7.5cm+.', mf: 7 },
  { texture: 'Heavy clays', description: 'Rolls to a 3-4mm thread, forms a ring in the palm without fracture. Smooth, very plastic, moderate-to-strong resistance to rolling out.', mf: 6 },
]

export const ECE_TABLE = [
  { className: 'Non-saline', range: '<2', comment: 'Salinity effects mostly negligible' },
  { className: 'Slightly saline', range: '2-4', comment: 'Yields of very sensitive crops may be affected' },
  { className: 'Moderately saline', range: '4-8', comment: 'Yields of many crops affected' },
  { className: 'Very saline', range: '8-16', comment: 'Only tolerant crops yield satisfactorily' },
  { className: 'Highly saline', range: '>16', comment: 'Only a few very tolerant crops yield satisfactorily' },
]
