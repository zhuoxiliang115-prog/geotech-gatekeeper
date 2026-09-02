"""Unit tests for Sandstone/Shale Class I-V classification
(app/rock_parameters/classification.py) - Table 9.1 of the Sydney
Classification System. Real reference logs exercise the paths that
occur naturally in real data (this corpus has zero direct UCS lab
readings - every strength reading is Is(50) point-load, so the
Is(50)->UCS estimation path, UCS+spacing disagreement, spacing-not-
assessed, and seam flagging are all checked against real strata);
synthetic stratum/reading data covers paths the real corpus doesn't
happen to exercise (a direct UCS reading, and Shale's Class IV/V shared-
UCS-floor tie - Shale is rare in this corpus and never lands in that
narrow band)."""

from pathlib import Path

import pdfplumber
import pytest

from app.parsers.borehole_log import parse_log_page
from app.rock_parameters.classification import (
    STRENGTH_SOURCE_DIRECT_UCS,
    STRENGTH_SOURCE_IS50_ESTIMATED,
    classify_rock_stratum,
)

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "reference" / "logs"


def _parse_page(filename, page_number):
    with pdfplumber.open(REFERENCE_DIR / filename) as pdf:
        return parse_log_page(pdf.pages[page_number - 1])


def _classify_stratum_by_text(filename, page_number, needle):
    parsed = _parse_page(filename, page_number)
    strata = parsed["strata"]
    for i, s in enumerate(strata):
        if needle in (s.get("text") or ""):
            next_depth = strata[i + 1]["depth_from_m"] if i + 1 < len(strata) else None
            return classify_rock_stratum(
                s, next_depth, parsed["point_load_ucs_readings"], parsed["defect_entries"]
            )
    raise AssertionError(f"no stratum containing {needle!r} found on {filename} page {page_number}")


# ---------- rock-type gate ----------


def test_out_of_scope_rock_type_flags_not_guessed():
    stratum = {"text": "CLAYSTONE: fine grained, dark brown.", "depth_from_m": 5.0}
    result = classify_rock_stratum(stratum, None, [], [])
    assert result["classified"] is False
    assert result["rock_type"] == "Claystone"
    assert "no Table 9.1 classification defined" in result["flag"]


def test_no_recognisable_rock_type_flags():
    result = _classify_stratum_by_text("PRUP_BH Logs.pdf", 2, "NO CORE:")
    assert result["classified"] is False
    assert result["rock_type"] is None
    assert "no recognisable rock type" in result["flag"]


def test_soil_interbed_in_a_rock_run_is_out_of_scope_not_misread():
    # A genuine soil stratum can appear within a Cored Borehole run - it
    # must not be mistaken for Sandstone/Shale just because the page is
    # a rock page.
    stratum = {"text": "Gravelly CLAY: high plasticity, pale grey.", "depth_from_m": 3.0}
    result = classify_rock_stratum(stratum, None, [], [])
    assert result["classified"] is False
    assert result["rock_type"] is None


# ---------- strength gate ----------


def test_no_strength_reading_nearby_flags():
    stratum = {"text": "SANDSTONE: fine grained, grey.", "depth_from_m": 5.0}
    result = classify_rock_stratum(stratum, 6.0, [], [])
    assert result["classified"] is False
    assert result["flag"] == "no UCS or Is(50) reading nearby to classify against Table 9.1."


def test_direct_ucs_reading_wins_over_is50_when_both_present():
    stratum = {"text": "SANDSTONE: fine grained, grey.", "depth_from_m": 5.0}
    readings = [
        {"type": "ucs", "value_mpa": 30.0, "depth_m": 5.1},
        {"type": "point_load_is50_a", "value_mpa": 0.5, "depth_m": 5.2},
    ]
    result = classify_rock_stratum(stratum, 6.0, readings, [])
    assert result["classified"] is True
    assert result["strength"]["source"] == STRENGTH_SOURCE_DIRECT_UCS
    assert result["strength"]["ucs_mpa"] == 30.0
    assert result["strength"]["is50_mpa"] is None
    assert result["strength"]["confidence"] == "high"
    assert result["bucket_id"] == "sandstone_class_1"
    assert "estimated" not in result["classification_basis"]
    assert not any("estimated" in w for w in result["warnings"])


def test_ucs_below_table_9_1_lowest_floor_not_classified():
    stratum = {"text": "SANDSTONE: fine grained, grey.", "depth_from_m": 5.0}
    readings = [{"type": "ucs", "value_mpa": 0.5, "depth_m": 5.1}]
    result = classify_rock_stratum(stratum, 6.0, readings, [])
    assert result["classified"] is False
    assert "below Table 9.1's lowest defined class threshold" in result["flag"]
    assert "Class V requires UCS>1 MPa" in result["flag"]


# ---------- Is(50) estimation (real data - this corpus has no direct UCS) ----------


def test_is50_estimation_real_example():
    result = _classify_stratum_by_text(
        "WSM_ BH Logs FINAL.pdf", 3, "SANDSTONE: medium to coarse grained, pale grey, tr"
    )
    assert result["classified"] is True
    strength = result["strength"]
    assert strength["source"] == STRENGTH_SOURCE_IS50_ESTIMATED
    assert strength["is50_mpa"] == 1.15
    assert strength["ucs_mpa"] == pytest.approx(23.0)
    assert strength["confidence"] == "low"
    assert "estimated from Is(50)=1.15 MPa via UCS ~ 20x Is50" in result["classification_basis"]
    assert "not a direct UCS test" in result["classification_basis"]
    assert "indicative only" in result["classification_basis"]
    assert any("estimated from Is(50)" in w and "indicative only" in w for w in result["warnings"])


def test_is50_estimation_never_produces_a_float_display_artifact():
    stratum = {"text": "SANDSTONE: fine grained, grey.", "depth_from_m": 5.0}
    readings = [{"type": "point_load_is50_a", "value_mpa": 2.03, "depth_m": 5.1}]
    result = classify_rock_stratum(stratum, 6.0, readings, [])
    assert result["strength"]["ucs_mpa"] == 40.6
    assert "40.6 MPa" in result["classification_basis"]


def test_ucs_and_spacing_disagree_by_more_than_one_class_flags():
    result = _classify_stratum_by_text(
        "WSM_ BH Logs FINAL.pdf", 2, "SANDSTONE: medium to coarse grained, pale grey, tr"
    )
    assert result["classified"] is True
    assert any("differ by more than one class" in w for w in result["warnings"])
    assert "-> Class" in result["classification_basis"]


def test_spacing_not_assessed_flags_when_insufficient_defect_data():
    result = _classify_stratum_by_text(
        "WSM_ BH Logs FINAL.pdf", 3, "SANDSTONE: medium to coarse grained, pale grey, tr"
    )
    assert result["classified"] is True
    assert any("spacing not assessed" in w for w in result["warnings"])
    assert "only - spacing not assessed" in result["classification_basis"]
    assert result["spacing_basis"] is None


# ---------- spacing_basis provenance ----------


def test_spacing_basis_states_computed_when_no_stated_spacing():
    # Real example: PRUP_BH Logs.pdf page 2, depth 6.44m - three natural
    # defects with no stated spacing of their own, depth-diffed instead.
    result = _classify_stratum_by_text(
        "WSM_ BH Logs FINAL.pdf", 2, "SANDSTONE: medium to coarse grained, pale grey, tr"
    )
    assert result["classified"] is True
    assert result["spacing_basis"] is not None
    assert result["spacing_basis"].startswith("computed: gaps of ")
    assert result["spacing_basis"].endswith("mm between consecutive natural defects")


def test_spacing_basis_states_stated_and_wins_over_computed():
    stratum = {"text": "SANDSTONE: fine grained, grey to green grey, variable spacing.", "depth_from_m": 5.0}
    readings = [{"type": "point_load_is50_axial", "value_mpa": 0.28, "depth_m": 5.1}]
    defects = [
        {"depth_from_m": 5.1, "depth_to_m": 5.1, "type": "J", "text": "J, 20-100 mm spacing, x 5"},
        {"depth_from_m": 5.9, "depth_to_m": 5.9, "type": "J", "text": "J, unrelated defect, no spacing stated"},
    ]
    result = classify_rock_stratum(stratum, 6.0, readings, defects)
    assert result["classified"] is True
    assert result["spacing_basis"] == "stated: 20-100mm (printed on log)"
    assert "800" not in result["spacing_basis"]  # the computed 800mm gap must not leak in once stated wins


def test_spacing_basis_none_when_no_defects_in_window():
    stratum = {"text": "SANDSTONE: fine grained, green grey.", "depth_from_m": 16.0}
    readings = [{"type": "point_load_is50_axial", "value_mpa": 1.9, "depth_m": 16.1}]
    result = classify_rock_stratum(stratum, 17.0, readings, [])
    assert result["classified"] is True
    assert result["spacing_basis"] is None


def test_seam_content_flags_without_blocking_classification():
    result = _classify_stratum_by_text(
        "WSM_ BH Logs FINAL.pdf", 8, "NO CORE: 4.80 -4.93 m. SANDSTONE: medium to coarse"
    )
    assert result["classified"] is True
    assert any("seam content present" in w for w in result["warnings"])
    assert "allowable-seam percentage not computed" in next(
        w for w in result["warnings"] if "seam content" in w
    )


# ---------- Shale Class IV/V shared-UCS-floor tie (synthetic - not in this corpus) ----------


def test_shale_class_4_5_tie_flagged_not_silently_resolved():
    stratum = {"text": "SHALE: dark grey, laminated.", "depth_from_m": 5.0}
    readings = [{"type": "ucs", "value_mpa": 1.5, "depth_m": 5.1}]  # >1, <=2: tied band
    result = classify_rock_stratum(stratum, 6.0, readings, [])
    assert result["classified"] is True
    assert result["bucket_id"] == "shale_class_4"  # UCS alone -> the tied class, not guessed higher
    assert any("shared Table 9.1 threshold" in w for w in result["warnings"])
    assert any("Class IV/V" in w for w in result["warnings"])


def test_shale_tie_resolved_by_spacing_when_available():
    stratum = {"text": "SHALE: dark grey, laminated.", "depth_from_m": 5.0}
    readings = [{"type": "ucs", "value_mpa": 1.5, "depth_m": 5.1}]
    defects = [
        {"depth_from_m": 5.0, "depth_to_m": 5.0, "type": "J", "text": "J, 10°, RF, PR, CN"},
        {"depth_from_m": 5.9, "depth_to_m": 5.9, "type": "J", "text": "J, 10°, RF, PR, CN"},
    ]
    result = classify_rock_stratum(stratum, 6.0, readings, defects)
    assert result["classified"] is True
    # spacing=900mm > Shale Class I's 600mm floor -> Class I; final = max(4, 1) = Class IV
    assert result["bucket_id"] == "shale_class_4"
    # spacing genuinely available this time, so the tie note shouldn't
    # also claim spacing "wasn't assessed above"
    tie_warning = next(w for w in result["warnings"] if "shared Table 9.1 threshold" in w)
    assert "verify against Table 9.1 if spacing wasn't assessed" in tie_warning


# ---------- bucket_id naming ----------


@pytest.mark.parametrize(
    "rock_type,ucs_mpa,expected_bucket",
    [
        ("SANDSTONE", 30, "sandstone_class_1"),
        ("SANDSTONE", 15, "sandstone_class_2"),
        ("SANDSTONE", 9, "sandstone_class_3"),
        ("SANDSTONE", 3, "sandstone_class_4"),
        ("SANDSTONE", 1.5, "sandstone_class_5"),
        ("SHALE", 20, "shale_class_1"),
        ("SHALE", 10, "shale_class_2"),
        ("SHALE", 3, "shale_class_3"),
    ],
)
def test_bucket_id_naming_by_ucs_alone(rock_type, ucs_mpa, expected_bucket):
    stratum = {"text": f"{rock_type}: grey.", "depth_from_m": 5.0}
    readings = [{"type": "ucs", "value_mpa": ucs_mpa, "depth_m": 5.1}]
    result = classify_rock_stratum(stratum, 6.0, readings, [])
    assert result["bucket_id"] == expected_bucket


# ---------- real corpus sweep ----------


def test_classification_across_real_corpus_does_not_crash():
    checked = 0
    classified = 0
    for path in REFERENCE_DIR.glob("*.pdf"):
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                parsed = parse_log_page(page)
                if (parsed.get("header") or {}).get("log_type") != "Cored Borehole":
                    continue
                strata = parsed["strata"]
                for i, stratum in enumerate(strata):
                    next_depth = strata[i + 1]["depth_from_m"] if i + 1 < len(strata) else None
                    result = classify_rock_stratum(
                        stratum, next_depth, parsed["point_load_ucs_readings"], parsed["defect_entries"]
                    )
                    checked += 1
                    if result["classified"]:
                        classified += 1
                        assert result["bucket_id"].startswith(("sandstone_class_", "shale_class_"))
                        assert result["strength"]["source"] in (
                            STRENGTH_SOURCE_DIRECT_UCS,
                            STRENGTH_SOURCE_IS50_ESTIMATED,
                        )
                        assert result["spacing_basis"] is None or result["spacing_basis"].startswith(
                            ("stated: ", "computed: ")
                        )
                    else:
                        assert result["flag"]
    assert checked > 500
    assert classified > 200  # this corpus's real Is(50)-estimated coverage
