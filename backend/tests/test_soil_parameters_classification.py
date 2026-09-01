"""Unit tests for the deterministic stratum classifier
(app/soil_parameters/classification.py). Real reference logs exercise the
paths that occur naturally in real data (clean clay/sand matches, the
printed-term-spans-a-transition case, the SPT-N fallback, the printed-
term-vs-SPT-N disagreement cross-check, out-of-scope Silt/Gravel/no-match
text); synthetic stratum dicts cover the FILL paths, which no reference
log happens to exercise (none of the sample logs' FILL descriptions carry
a compaction descriptor - see FILL_COMPACTED_KEYWORDS/
FILL_UNCOMPACTED_KEYWORDS), plus a couple of edge cases (no SPT data at
all) that are inconvenient to find in real data on demand."""

from pathlib import Path

import pdfplumber
import pytest

from app.parsers.borehole_log import parse_log_page
from app.soil_parameters.classification import classify_stratum

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "reference" / "logs"


def _stratum_by_text(filename, page_number, needle):
    with pdfplumber.open(REFERENCE_DIR / filename) as pdf:
        parsed = parse_log_page(pdf.pages[page_number - 1])
    for stratum in parsed["strata"]:
        if needle in (stratum.get("text") or ""):
            return stratum, parsed["field_test_entries"]
    raise AssertionError(f"no stratum containing {needle!r} found on {filename} page {page_number}")


# ---------- real data: Clay ----------


def test_clay_clean_match_from_printed_consistency_term():
    stratum, field_tests = _stratum_by_text(
        "Alex Canal.pdf", 4, "Silty CLAY: medium plasticity, dark grey; with sand"
    )
    result = classify_stratum(stratum, field_tests)
    assert result["classified"] is True
    assert result["bucket_id"] == "clay_very_soft"
    assert result["principal_soil_type"] == "Clay"
    assert result["classification_basis"] == "printed consistency term"
    assert result["warnings"] == []


def test_clay_transitional_term_uses_first_shallower_code():
    stratum, field_tests = _stratum_by_text("Alex Canal.pdf", 4, "CLAY: high plasticity, grey; trace sand, fine grained.")
    assert stratum["consistency_relative_density"] == ["St", "to", "VSt"]
    result = classify_stratum(stratum, field_tests)
    assert result["classified"] is True
    assert result["bucket_id"] == "clay_stiff"
    assert len(result["warnings"]) == 1
    assert "transition" in result["warnings"][0]
    assert "ST" in result["warnings"][0] and "VST" in result["warnings"][0]


def test_clay_missing_consistency_flags_with_spt_hint():
    stratum, field_tests = _stratum_by_text(
        "Alex Canal.pdf", 4, "from 4.62 to 4.67 m: organic CLAY band, low plasticity, black"
    )
    assert stratum["consistency_relative_density"] == []
    result = classify_stratum(stratum, field_tests)
    assert result["classified"] is False
    assert result["bucket_id"] is None
    assert "consistency not stated" in result["flag"]
    assert "SPT N=4" in result["flag"]


def test_clay_missing_consistency_no_spt_data_at_all():
    stratum = {"text": "CLAY: high plasticity, grey.", "depth_from_m": 5.0, "consistency_relative_density": []}
    result = classify_stratum(stratum, [])
    assert result["classified"] is False
    assert result["flag"] == "consistency not stated"


def test_clay_never_auto_assigned_from_spt_alone():
    """SPT-N/consistency correlation isn't reliable enough to assign a
    bucket from N alone (per the user's own instruction) - N only ever
    appears as a hint in the flag message on the no-printed-term path."""
    stratum = {
        "text": "CLAY: high plasticity, grey.",
        "depth_from_m": 5.0,
        "consistency_relative_density": [],
    }
    field_tests = [{"type": "SPT", "depth_from_m": 5.0, "n_value": "60"}]
    result = classify_stratum(stratum, field_tests)
    assert result["classified"] is False
    assert result["bucket_id"] is None


# ---------- real data: Sand ----------


def test_sand_clean_match_from_printed_relative_density_term():
    stratum, field_tests = _stratum_by_text("Alex Canal.pdf", 4, "SAND: fine to coarse grained, grey; with silt.")
    result = classify_stratum(stratum, field_tests)
    assert result["classified"] is True
    assert result["bucket_id"] == "sand_medium_dense"
    assert result["principal_soil_type"] == "Sand"
    assert result["classification_basis"] == "printed relative-density term"
    assert result["warnings"] == []


def test_sand_spt_fallback_when_relative_density_term_missing():
    stratum, field_tests = _stratum_by_text(
        "WSM_ BH Logs FINAL.pdf", 1, "TOPSOIL -Silty SAND: fine to coarse grained, dark brown; trace gravel, fine to m"
    )
    assert stratum["consistency_relative_density"] == []
    result = classify_stratum(stratum, field_tests)
    assert result["classified"] is True
    assert result["bucket_id"] == "sand_dense"
    assert "SPT N=32 fallback" in result["classification_basis"]
    assert "Terzaghi" in result["classification_basis"]


def test_sand_printed_term_vs_spt_disagreement_is_flagged_not_blocked():
    stratum, field_tests = _stratum_by_text(
        "Heathcote.pdf", 7, "SAND: medium to coarse grained, yellow-brown; trace clay."
    )
    assert stratum["consistency_relative_density"] == ["MD"]
    result = classify_stratum(stratum, field_tests)
    # Printed term is authoritative - disagreement is a warning, not a block.
    assert result["classified"] is True
    assert result["bucket_id"] == "sand_medium_dense"
    assert len(result["warnings"]) == 1
    assert "disagrees with nearby SPT N=3" in result["warnings"][0]
    assert "more than one band" in result["warnings"][0]


def test_sand_missing_relative_density_and_no_spt_flags():
    stratum = {"text": "SAND: fine grained, grey.", "depth_from_m": 5.0, "consistency_relative_density": []}
    result = classify_stratum(stratum, [])
    assert result["classified"] is False
    assert "no nearby SPT N-value" in result["flag"]


def test_sand_transitional_term_uses_first_shallower_code():
    stratum = {
        "text": "SAND: fine grained, grey.",
        "depth_from_m": 5.0,
        "consistency_relative_density": ["L", "to", "MD"],
    }
    result = classify_stratum(stratum, [])
    assert result["classified"] is True
    assert result["bucket_id"] == "sand_loose"
    assert len(result["warnings"]) == 1
    assert "transition" in result["warnings"][0]


# ---------- real data: out of scope / no match ----------


def test_silt_flagged_as_no_bucket_defined_this_pass():
    # Constructed directly - Silt/Gravel strata exist in reference logs but
    # picking a stable page/text needle across future reference-file edits
    # is brittle; the rule itself only depends on the principal-type regex.
    stratum = {"text": "Sandy SILT: low plasticity, brown.", "depth_from_m": 1.0, "consistency_relative_density": []}
    result = classify_stratum(stratum, [])
    assert result["classified"] is False
    assert result["principal_soil_type"] == "Silt"
    assert "no typical-parameter bucket defined yet" in result["flag"]


def test_gravel_flagged_as_no_bucket_defined_this_pass():
    stratum = {"text": "Sandy GRAVEL: coarse grained, brown.", "depth_from_m": 1.0, "consistency_relative_density": []}
    result = classify_stratum(stratum, [])
    assert result["classified"] is False
    assert result["principal_soil_type"] == "Gravel"


def test_no_recognisable_principal_type_flags():
    stratum, field_tests = _stratum_by_text("Alex Canal.pdf", 4, "Terminated at 10.00 m. Target depth.")
    result = classify_stratum(stratum, field_tests)
    assert result["classified"] is False
    assert result["principal_soil_type"] is None
    assert "no recognisable principal soil type" in result["flag"]


# ---------- synthetic: FILL (no reference log has a compaction descriptor) ----------


def test_fill_well_compacted():
    stratum = {"text": "FILL -Gravelly CLAY: well compacted, brown.", "depth_from_m": 0.3, "consistency_relative_density": []}
    result = classify_stratum(stratum, [])
    assert result["classified"] is True
    assert result["bucket_id"] == "fill_well_compacted"
    assert result["principal_soil_type"] == "Fill"


def test_fill_engineered_counts_as_compacted():
    stratum = {"text": "FILL -SAND: engineered, brown.", "depth_from_m": 0.3, "consistency_relative_density": []}
    result = classify_stratum(stratum, [])
    assert result["classified"] is True
    assert result["bucket_id"] == "fill_well_compacted"


def test_fill_uncompacted_cohesive():
    stratum = {"text": "FILL -CLAY: uncompacted, low plasticity, brown.", "depth_from_m": 0.3, "consistency_relative_density": []}
    result = classify_stratum(stratum, [])
    assert result["classified"] is True
    assert result["bucket_id"] == "fill_uncompacted_cohesive"


def test_fill_uncompacted_non_cohesive():
    stratum = {"text": "FILL -Gravelly SAND: loose, fine to coarse grained, brown.", "depth_from_m": 0.3, "consistency_relative_density": []}
    result = classify_stratum(stratum, [])
    assert result["classified"] is True
    assert result["bucket_id"] == "fill_uncompacted_non_cohesive"


def test_fill_uncompacted_but_no_clear_dominant_type_flags():
    stratum = {"text": "FILL -TOPSOIL: uncompacted, dark brown organic material.", "depth_from_m": 0.1, "consistency_relative_density": []}
    result = classify_stratum(stratum, [])
    assert result["classified"] is False
    assert "no clear dominant soil type" in result["flag"]


def test_fill_no_compaction_descriptor_flags():
    stratum = {"text": "FILL -Gravelly CLAY: low plasticity, brown.", "depth_from_m": 0.3, "consistency_relative_density": []}
    result = classify_stratum(stratum, [])
    assert result["classified"] is False
    assert result["principal_soil_type"] == "Fill"
    assert "no compaction descriptor found" in result["flag"]


def test_concrete_capping_prefix_means_stratum_is_not_treated_as_fill():
    """A stratum whose text starts with something other than "FILL" (e.g.
    a concrete cap description followed by a FILL note further in) is
    classified from its own principal type, not routed through
    _classify_fill - matches real Alex Canal.pdf BH04 behaviour, where the
    first stratum is "CONCRETE: ... FILL -Gravelly CLAY: ..." and is
    correctly classified as Clay (flagged for missing consistency), not
    Fill."""
    stratum, field_tests = _stratum_by_text(
        "Alex Canal.pdf", 4, "CONCRETE: grey; aggregates up to 20 mm, 270 mm thick. FILL -Gravelly CLAY"
    )
    result = classify_stratum(stratum, field_tests)
    assert result["principal_soil_type"] == "Clay"
    assert result["classified"] is False
    assert "consistency not stated" in result["flag"]
