// Rock-only display helpers for the Design Parameters page - the
// Hoek-Brown field labels have no soil equivalent, unlike
// DESIGN_TABLE_FIELD_LABELS (designParameterDisplay.js), which rock's
// design_table shares with soil's table.

// sti_MPa is deliberately left unlabelled - rock_typical_parameters.json
// carries no citation for what it stands for, and guessing an expansion
// for a technical field an engineer will read verbatim is worse than
// falling back to the raw key (the field label lookup already does that
// for any key missing here, same as soil's).
export const HOEK_BROWN_FIELD_LABELS = {
  gamma_kNm3: 'Unit weight (γ)',
  min_ucs_MPa: 'Minimum UCS for this class',
  poissons_ratio: "Poisson's ratio (ν)",
  hoek_brown_mi: 'Hoek-Brown mᵢ (intact rock constant)',
  Emass_MPa: 'Rock mass modulus (Emass)',
  c_star_kPa: 'Equivalent cohesion (c*), at σ₃=500 kPa',
  phi_star_deg: 'Equivalent friction angle (φ*), at σ₃=500 kPa',
  GSI: 'Geological Strength Index (GSI)',
  hoek_brown_s: 'Hoek-Brown s',
  mb: 'Hoek-Brown mb',
}

/**
 * The confidence tag's label, distinct from the *_source_note "⚠
 * provisional" badge - that badge means one specific value might be a
 * transcription error; this tag means the strength this whole
 * classification rests on is inherently an estimate (or, rarely, isn't).
 * Returns null when there's no strength to report (stratum wasn't
 * classified).
 */
export function strengthConfidenceLabel(strength) {
  if (!strength) return null
  return strength.source === 'is50_estimated' ? 'Estimated from Is(50)' : 'Measured'
}
