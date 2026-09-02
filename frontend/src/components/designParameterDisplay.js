// Shared display helpers for the Design Parameters page (soil + rock
// together). Split from the old soilParameterDisplay.js once rock
// parameters needed the same stratum-location formatting and the same
// "design table" field-label set (rock's design_table shares every field
// name soil's table has, plus two pile/anchor-specific ones) - genuinely
// shared, not duplicated. Hoek-Brown's field labels are rock-only and
// live in rockParameterDisplay.js instead.

const _truncate = (text, max) => (text && text.length > max ? `${text.slice(0, max).trimEnd()}…` : text)

export function formatStratumLocation(stratum) {
  const depth = stratum?.depth_from_m
  const depthLabel = depth != null ? `${depth.toFixed(2)} m` : 'Depth unknown'
  const excerpt = _truncate((stratum?.text ?? '').trim(), 60)
  return excerpt ? `${depthLabel} — "${excerpt}"` : depthLabel
}

// Both soil_parameters/lookup.py's single table and rock_parameters/
// lookup.py's design_table preserve their JSON source's own per-bucket
// key order, and JS preserves object key order too, so this only needs
// to supply the human-readable label per key - display order comes
// straight from Object.entries(parameters.fields), not from here.
export const DESIGN_TABLE_FIELD_LABELS = {
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
  shaft_adhesion_ult_kPa: 'Shaft adhesion, ultimate',
  anchor_bond_ult_kPa: 'Anchor bond, ultimate',
  active_wedge_angle_deg: 'Active wedge angle',
}

/**
 * Combines POST /soil-parameters' and POST /rock-parameters' `holes`
 * responses into one per-hole list, sorted by depth_from_m, each entry
 * tagged with which endpoint it came from so the caller can render the
 * matching card type.
 *
 * A Cored Borehole sheet is processed by *both* endpoints (soil-
 * parameters runs on every log-type page, not just soil ones), but
 * soil's classifier can never actually succeed there - Cored Borehole
 * sheets have no CONSISTENCY/RELATIVE DENSITY column, and soil's gate
 * requires one, so every stratum on that sheet fails soil's classifier
 * regardless of content (verified against the full reference corpus:
 * 0/288 strata classified by /soil-parameters across every Cored
 * Borehole page checked). So for any page number rock-parameters also
 * covers, its response wins outright and soil's copy of that page is
 * dropped rather than kept as a second, uniformly-unhelpful
 * "not classified" card sitting next to rock's real one.
 */
export function mergeParameterHoles(soilHoles, rockHoles) {
  const holeIds = new Set([...Object.keys(soilHoles ?? {}), ...Object.keys(rockHoles ?? {})])
  const merged = {}

  for (const holeId of holeIds) {
    const rockPages = rockHoles?.[holeId] ?? []
    const rockPageNumbers = new Set(rockPages.map((p) => p.page))
    const soilPages = (soilHoles?.[holeId] ?? []).filter((p) => !rockPageNumbers.has(p.page))

    const entries = []
    for (const page of soilPages) {
      for (const sr of page.strata_results) {
        entries.push({ origin: 'soil', page: page.page, header: page.header, sr })
      }
    }
    for (const page of rockPages) {
      for (const sr of page.strata_results) {
        entries.push({ origin: 'rock', page: page.page, header: page.header, sr })
      }
    }

    entries.sort((a, b) => {
      const da = a.sr.stratum?.depth_from_m ?? Number.POSITIVE_INFINITY
      const db = b.sr.stratum?.depth_from_m ?? Number.POSITIVE_INFINITY
      if (da !== db) return da - db
      return a.page - b.page // stable tiebreak on a depth tie: original sheet order
    })

    merged[holeId] = entries
  }

  return merged
}

/**
 * Groups an already depth-sorted entries array (mergeParameterHoles'
 * output for one hole) into runs of consecutive same-page entries, so
 * the UI can show one LogHeaderSummary per physical sheet while the
 * strata underneath still read as one continuous depth-ordered column -
 * every log sheet in this corpus covers a contiguous, non-overlapping
 * depth range, so this reproduces the same grouping a literal flatten
 * would, without discarding each sheet's own header metadata (project,
 * dates, logged/checked by) that a fully headerless list would lose.
 */
export function groupEntriesBySheet(entries) {
  const runs = []
  for (const entry of entries) {
    const last = runs[runs.length - 1]
    if (last && last.page === entry.page) {
      last.items.push(entry)
    } else {
      runs.push({ page: entry.page, header: entry.header, items: [entry] })
    }
  }
  return runs
}
