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

// judgment.py's JUDGMENT_CATEGORIES, humanized for display.
export const JUDGMENT_CATEGORY_LABELS = {
  field_id_vs_uscs_symbol: 'Field ID vs. USCS symbol',
  secondary_minor_component_wording: 'Secondary/minor component wording',
  spt_consistency_correlation: 'SPT vs. consistency/density correlation',
  geological_origin_plausibility: 'Geological origin plausibility',
  cross_sheet_continuity: 'Cross-sheet continuity',
  colour_term_plausibility: 'Colour-term plausibility',
}
