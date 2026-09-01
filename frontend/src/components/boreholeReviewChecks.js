// Shared between RuleCheckedFindings and LabCrossReferenceFindings so the
// two lists partition rule_findings consistently: every check name here
// compares the log against an attached lab report (rules.py's
// match_lab_samples_to_log-based checks), the rest are self-contained
// checks against the standard doc alone.
export const LAB_CROSS_REF_CHECKS = new Set([
  'plasticity_term_vs_lab_ll',
  'uscs_symbol_vs_lab_a_line',
  'grading_curve_symbol_vs_lab',
])

export function isLabCrossRefFinding(finding) {
  return LAB_CROSS_REF_CHECKS.has(finding.check)
}

// Rule-checked findings only carry a topic reference (standard_section,
// e.g. "§3.11") as "where" by default. Several checks' `compared` payload
// actually pinpoints a specific stratum, depth, or reading - a much more
// useful location than the section number alone. Returns null when
// nothing more specific than the section is available (e.g. the
// header/column-caption checks, which are log-wide, not tied to one
// spot), so the caller can leave those exactly as they were.
const _truncate = (text, max) => (text && text.length > max ? `${text.slice(0, max).trimEnd()}…` : text)

export function getRuleFindingLocation(finding) {
  const c = finding.compared || {}
  switch (finding.check) {
    case 'valid_uscs_symbol':
    case 'valid_weathering_symbol':
      return c.stratum_text ? _truncate(c.stratum_text, 55) : null
    case 'defect_description_format':
      return c.text ?? null
    case 'valid_field_test_type':
      return c.depth_from_m != null ? `${c.depth_from_m.toFixed(2)} m depth` : null
    case 'hb_context_disambiguation':
      return (c.context === 'field_test_entry' ? c.blows : c.text) ?? null
    case 'rock_strength_band_consistency':
      return c.source ?? null
    default:
      return null
  }
}

// judgment.py's JUDGMENT_CATEGORIES, humanized for display.
export const JUDGMENT_CATEGORY_LABELS = {
  field_id_vs_uscs_symbol: 'Field ID vs. USCS symbol',
  secondary_minor_component_wording: 'Secondary/minor component wording',
  spt_consistency_correlation: 'SPT vs. consistency/density correlation',
  geological_origin_plausibility: 'Geological origin plausibility',
  cross_sheet_continuity: 'Cross-sheet continuity',
  colour_term_plausibility: 'Colour-term plausibility',
}
