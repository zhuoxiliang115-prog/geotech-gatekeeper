// Shared display helpers for the Soil Parameters page - the analogue of
// boreholeReviewChecks.js, but for a different problem. A rule finding's
// location is scattered across each check's own `compared` payload, which
// is why boreholeReviewChecks.js needs a per-check dispatch
// (getRuleFindingLocation). A stratum's location isn't scattered anywhere -
// the stratum itself already carries its depth and description text - so
// this is a plain formatter, not a dispatch table.

const _truncate = (text, max) => (text && text.length > max ? `${text.slice(0, max).trimEnd()}…` : text)

export function formatStratumLocation(stratum) {
  const depth = stratum?.depth_from_m
  const depthLabel = depth != null ? `${depth.toFixed(2)} m` : 'Depth unknown'
  const excerpt = _truncate((stratum?.text ?? '').trim(), 60)
  return excerpt ? `${depthLabel} — "${excerpt}"` : depthLabel
}

// lookup.py's `fields` dict preserves soil_typical_parameters.json's own
// per-bucket key order, and JS preserves object key order too, so this
// only needs to supply the human-readable label per key - display order
// comes straight from Object.entries(parameters.fields), not from here.
export const PARAMETER_FIELD_LABELS = {
  gamma_kNm3: 'Unit weight (γ)',
  cu_kPa: 'Undrained shear strength (cu)',
  c_prime_kPa: "Effective cohesion (c')",
  phi_prime_deg: "Effective friction angle (φ')",
  K0: 'K₀ (at-rest earth pressure)',
  Kp: 'Kp (passive earth pressure)',
  reduced_phi_deg: "Reduced φ' (factored)",
  reduced_c_kPa: "Reduced c' (factored)",
  E_prime_MPa: "Drained modulus (E')",
  poissons_ratio: "Poisson's ratio (ν)",
  end_bearing_ult_MPa: 'End bearing, ultimate',
  end_bearing_serv_MPa: 'End bearing, serviceability',
  active_wedge_angle_deg: 'Active wedge angle',
}
