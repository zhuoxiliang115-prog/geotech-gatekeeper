"""Unit tests for the deterministic rule-checking engine
(app/borehole_review/rules.py), checked against real example logs in
reference/logs/ and, for the lab cross-referencing checks (which need a
matching lab report this repo doesn't have a real paired example of),
synthetic data constructed to exercise the matching and comparison logic."""

from pathlib import Path

import pdfplumber
import pytest

from app.borehole_review import rules
from app.parsers.borehole_log import parse_log_page

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "reference" / "logs"


def _parse_and_words(filename, page_number):
    with pdfplumber.open(REFERENCE_DIR / filename) as pdf:
        page = pdf.pages[page_number - 1]
        parsed = parse_log_page(page)
        words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
    return parsed, words


# ---------- §2: required header fields ----------


def test_required_header_fields_pass_for_complete_borehole():
    parsed, _ = _parse_and_words("WSM_ BH Logs FINAL.pdf", 1)
    findings = rules.check_required_header_fields(parsed["header"])
    main = findings[0]
    assert main["status"] == "pass"
    assert main["compared"]["missing"] == []


def test_required_header_fields_flags_missing_field():
    header = {"log_type": "Borehole", "hole_id": "BH01", "client": "ACME"}
    findings = rules.check_required_header_fields(header)
    main = findings[0]
    assert main["status"] == "fail"
    assert "driller" in main["compared"]["missing"]


def test_required_header_fields_skipped_for_unknown_type():
    findings = rules.check_required_header_fields({"log_type": None})
    assert findings[0]["status"] == "skipped"


def test_required_header_fields_notes_unextracted_coverage_gap():
    parsed, _ = _parse_and_words("WSM_ BH Logs FINAL.pdf", 1)
    findings = rules.check_required_header_fields(parsed["header"])
    coverage_note = [f for f in findings if f["check"] == "required_header_fields_coverage"]
    assert coverage_note
    assert "Drill Rig" in coverage_note[0]["compared"]["not_yet_extracted"]


# ---------- §2: required table-column captions ----------


def test_required_columns_pass_for_borehole():
    _, words = _parse_and_words("WSM_ BH Logs FINAL.pdf", 1)
    findings = rules.check_required_columns(words, "Borehole")
    assert findings[0]["status"] == "pass"


def test_required_columns_pass_for_cored_borehole():
    _, words = _parse_and_words("Heathcote.pdf", 2)
    findings = rules.check_required_columns(words, "Cored Borehole")
    assert findings[0]["status"] == "pass"


def test_required_columns_flags_missing_keyword():
    findings = rules.check_required_columns([], "Borehole")
    assert findings[0]["status"] == "fail"
    assert len(findings[0]["compared"]["missing"]) > 0


# ---------- §3.11: USCS symbol validity + boundary format ----------


def test_valid_uscs_symbol_simple():
    strata = [{"text": "CL Gravelly CLAY: low plasticity, grey."}]
    findings = rules.check_valid_uscs_symbols(strata)
    assert findings[0]["status"] == "pass"
    assert findings[0]["compared"]["symbol"] == "CL"


def test_valid_uscs_boundary_symbol():
    strata = [{"text": "CI-CH CLAY: medium to high plasticity, pale brown."}]
    findings = rules.check_valid_uscs_symbols(strata)
    assert findings[0]["status"] == "pass"
    assert findings[0]["compared"]["symbol"] == "CI-CH"


def test_valid_uscs_symbol_skips_non_symbol_words():
    strata = [{"text": "TOPSOIL -Silty SAND: fine grained."}, {"text": "FILL -SAND: fine grained."}]
    findings = rules.check_valid_uscs_symbols(strata)
    assert findings == []


def test_invalid_boundary_symbol_fails():
    strata = [{"text": "XX-YY CLAY: nonsense symbol."}]
    findings = rules.check_valid_uscs_symbols(strata)
    assert findings[0]["status"] == "fail"


def test_real_examples_produce_valid_uscs_findings():
    parsed, _ = _parse_and_words("PRUP_TP Logs.pdf", 1)
    findings = rules.check_valid_uscs_symbols(parsed["strata"])
    assert any(f["status"] == "pass" for f in findings)
    assert all(f["status"] == "pass" for f in findings)


# ---------- §3.14: weathering symbol validity ----------


def test_weathering_symbol_valid():
    strata = [{"text": "SHALE: dark grey, HW, VL strength."}]
    findings = rules.check_weathering_symbols(strata)
    assert findings[0]["status"] == "pass"
    assert findings[0]["compared"]["symbol"] == "HW"


# ---------- §3.1 / §3.15: defect description format ----------


def test_defect_description_valid_format():
    notes = ["P, 30/145°, PR, RF, CT, gy"]
    findings = rules.check_defect_descriptions(notes)
    assert findings[0]["status"] == "pass"


def test_defect_description_invalid_symbol():
    notes = ["P, 30/145°, PL, ro, co, gy"]  # retired 2017 symbols
    findings = rules.check_defect_descriptions(notes)
    assert findings[0]["status"] == "fail"
    assert "planarity" in findings[0]["explanation"] or "roughness" in findings[0]["explanation"]


def test_defect_description_not_applicable_to_plain_text():
    notes = ["Sandstone boulders observed."]
    assert rules.check_defect_descriptions(notes) == []


# ---------- §3.16: field-test type validity + HB disambiguation ----------


def test_field_test_types_valid_for_real_example():
    parsed, _ = _parse_and_words("WSM_ BH Logs FINAL.pdf", 1)
    findings = rules.check_field_test_types(parsed["field_test_entries"])
    assert findings
    assert all(f["status"] == "pass" for f in findings)


def test_hb_context_disambiguates_field_test_vs_defect():
    field_test_entries = [{"type": "SPT", "blows": "10/50 mm HB", "n_value": "R", "depth_from_m": 3.0}]
    notes = ["MB, healed, HB observed in core run"]
    findings = rules.check_hb_context(field_test_entries, notes)
    contexts = {f["compared"]["context"] for f in findings}
    assert contexts == {"field_test_entry", "notes"}
    for f in findings:
        assert f["status"] == "pass"


# ---------- §3.13: rock strength band consistency ----------


def test_rock_strength_band_consistent():
    readings = [{"type": "ucs", "value_mpa": 15.0, "depth_m": 5.0}]
    strata = [{"text": "SANDSTONE: Medium strength, fine grained."}]
    findings = rules.check_rock_strength_band(readings, strata, [])
    assert findings[0]["status"] == "pass"
    assert findings[0]["compared"]["implied_term"] == "Medium"


def test_rock_strength_band_inconsistent():
    readings = [{"type": "ucs", "value_mpa": 150.0, "depth_m": 5.0}]
    strata = [{"text": "SANDSTONE: Low strength, fine grained."}]
    findings = rules.check_rock_strength_band(readings, strata, [])
    assert findings[0]["status"] == "fail"
    assert findings[0]["compared"]["implied_term"] == "Very High"


def test_rock_strength_band_skipped_when_no_term_logged():
    readings = [{"type": "point_load_is50_d", "value_mpa": 0.5, "depth_m": 5.0}]
    findings = rules.check_rock_strength_band(readings, [{"text": "SANDSTONE: fine grained."}], [])
    assert findings[0]["status"] == "skipped"


# ---------- Cross-referencing against lab report results ----------


@pytest.fixture
def synthetic_lab_match():
    strata = [{"text": "CI Sandy CLAY: medium plasticity, brown.", "depth_from_m": 1.0}]
    atterberg = [
        {"sample_id": "HA02_0.9-1.3", "liquid_limit": 30.0, "plastic_limit": 15.0, "plasticity_index": 15.0}
    ]
    return strata, atterberg


def test_match_lab_samples_by_hole_and_depth(synthetic_lab_match):
    strata, atterberg = synthetic_lab_match
    matches = rules.match_lab_samples_to_log("PRUP_HA02", [], strata, atterberg)
    assert len(matches) == 1
    assert matches[0]["matched_stratum"] is strata[0]


def test_match_lab_samples_no_match_for_different_hole(synthetic_lab_match):
    strata, atterberg = synthetic_lab_match
    matches = rules.match_lab_samples_to_log("PRUP_BH03", [], strata, atterberg)
    assert matches == []


def test_plasticity_vs_lab_flags_mismatch_with_correction(synthetic_lab_match):
    strata, atterberg = synthetic_lab_match
    matches = rules.match_lab_samples_to_log("PRUP_HA02", [], strata, atterberg)
    findings = rules.check_plasticity_vs_lab(matches)
    assert findings[0]["status"] == "fail"
    assert "low plasticity" in findings[0]["explanation"]  # the suggested correction
    assert findings[0]["compared"]["implied_term"] == "low"
    assert findings[0]["compared"]["logged_term"] == "medium"


def test_plasticity_vs_lab_passes_when_consistent():
    strata = [{"text": "CL Sandy CLAY: low plasticity, brown.", "depth_from_m": 1.0}]
    atterberg = [{"sample_id": "HA02_0.9-1.3", "liquid_limit": 30.0}]
    matches = rules.match_lab_samples_to_log("PRUP_HA02", [], strata, atterberg)
    findings = rules.check_plasticity_vs_lab(matches)
    assert findings[0]["status"] == "pass"


def test_uscs_symbol_vs_lab_flags_mismatch_with_correction(synthetic_lab_match):
    strata, atterberg = synthetic_lab_match
    matches = rules.match_lab_samples_to_log("PRUP_HA02", [], strata, atterberg)
    findings = rules.check_uscs_symbol_vs_lab(matches)
    assert findings[0]["status"] == "fail"
    assert findings[0]["compared"]["logged_symbol"] == "CI"
    assert findings[0]["compared"]["implied_zone"] == "CL or OL"


def test_grading_symbol_vs_lab_well_graded_pass():
    strata = [{"text": "SW SAND: well graded.", "depth_from_m": 1.0}]
    psd = [
        {
            "sample_id": "HA02_0.9-1.3",
            "readings": [
                {"sieve_mm": 19.0, "passing_pct": 100},
                {"sieve_mm": 9.5, "passing_pct": 90},
                {"sieve_mm": 4.75, "passing_pct": 70},
                {"sieve_mm": 2.36, "passing_pct": 50},
                {"sieve_mm": 1.18, "passing_pct": 30},
                {"sieve_mm": 0.6, "passing_pct": 15},
                {"sieve_mm": 0.3, "passing_pct": 8},
                {"sieve_mm": 0.15, "passing_pct": 3},
                {"sieve_mm": 0.075, "passing_pct": 1},
            ],
        }
    ]
    findings = rules.check_grading_symbol_vs_lab("PRUP_HA02", strata, psd)
    assert findings[0]["status"] == "pass"


def test_grading_symbol_vs_lab_flags_mislabeled_poorly_graded():
    # Same well-graded curve as above, but logged as SP (poorly graded) -
    # should fail, since the curve actually meets the well-graded criteria.
    strata = [{"text": "SP SAND: poorly graded.", "depth_from_m": 1.0}]
    psd = [
        {
            "sample_id": "HA02_0.9-1.3",
            "readings": [
                {"sieve_mm": 19.0, "passing_pct": 100},
                {"sieve_mm": 9.5, "passing_pct": 90},
                {"sieve_mm": 4.75, "passing_pct": 70},
                {"sieve_mm": 2.36, "passing_pct": 50},
                {"sieve_mm": 1.18, "passing_pct": 30},
                {"sieve_mm": 0.6, "passing_pct": 15},
                {"sieve_mm": 0.3, "passing_pct": 8},
                {"sieve_mm": 0.15, "passing_pct": 3},
                {"sieve_mm": 0.075, "passing_pct": 1},
            ],
        }
    ]
    findings = rules.check_grading_symbol_vs_lab("PRUP_HA02", strata, psd)
    assert findings[0]["status"] == "fail"
    assert "SW" in findings[0]["explanation"]


# ---------- orchestration ----------


def test_run_all_checks_skips_lab_checks_cleanly_without_lab_reports():
    parsed, words = _parse_and_words("WSM_ BH Logs FINAL.pdf", 1)
    findings = rules.run_all_checks(parsed, words, lab_results=None)
    skipped = [f for f in findings if f["status"] == "skipped" and "lab report was provided" in f["explanation"]]
    assert len(skipped) == 2  # plasticity/USCS-vs-lab, and grading-vs-lab
    assert all(f["category"] == "rule_checked" for f in findings)


def test_run_all_checks_on_real_cored_borehole_page():
    parsed, words = _parse_and_words("Heathcote.pdf", 2)
    findings = rules.run_all_checks(parsed, words)
    assert findings
    checks_run = {f["check"] for f in findings}
    assert "required_header_fields" in checks_run
    assert "required_table_columns" in checks_run
