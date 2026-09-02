"""Unit tests for defect-spacing derivation
(app/rock_parameters/defects.py). Synthetic defect_entries for the
targeted logic (artifact exclusion, stated-vs-computed spacing, the
aperture-vs-spacing regex trap) plus one real-corpus check that the two
type sets stay a clean partition of rules.VALID_DEFECT_TYPES and that
computing spacing across every real Cored Borehole stratum window
doesn't crash or produce nonsense."""

from pathlib import Path

import pdfplumber
import pytest

from app.borehole_review.rules import VALID_DEFECT_TYPES
from app.parsers.borehole_log import parse_log_page, process_log_pdf
from app.rock_parameters.defects import (
    DRILLING_ARTIFACT_TYPES,
    NATURAL_DEFECT_TYPES,
    _stated_spacing_mm,
    compute_defect_spacing,
)

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "reference" / "logs"


def _entry(depth_from_m, defect_type, text, depth_to_m=None):
    return {
        "depth_from_m": depth_from_m,
        "depth_to_m": depth_to_m if depth_to_m is not None else depth_from_m,
        "type": defect_type,
        "text": text,
    }


def test_natural_and_artifact_types_partition_valid_defect_types():
    assert NATURAL_DEFECT_TYPES | DRILLING_ARTIFACT_TYPES == VALID_DEFECT_TYPES
    assert NATURAL_DEFECT_TYPES.isdisjoint(DRILLING_ARTIFACT_TYPES)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("EW, RF, clay, 20 mm aperture, 500 mm spacing, x 2", (500, 500)),
        ("J, 0-30°, RF, VN CL, 10 -40 mm spacing, x 6", (10, 40)),
        ("J, 10-25°, RF, PR, VN root fibres, 30 spacing, x 4", (30, 30)),
        ("P, 5°, RF, PR, SN Fe", None),
    ],
)
def test_stated_spacing_parsing(text, expected):
    assert _stated_spacing_mm(text) == expected


def test_stated_spacing_ignores_an_earlier_aperture_value():
    # "5 mm aperture" must not be mistaken for the spacing value - only
    # the number immediately before the literal word "spacing" counts.
    text = "J, 5-30°, RF, CT CL, 5 mm aperture, up to 80 mm spacing, x 5"
    assert _stated_spacing_mm(text) == (80, 80)


def test_compute_defect_spacing_excludes_drilling_artifacts():
    entries = [
        _entry(1.0, "P", "P, 10°, RF, PR, CN"),
        _entry(1.2, "DB", "DB"),
        _entry(1.3, "MB", "MB"),
        _entry(1.5, "P", "P, 5°, RF, PR, CN"),
    ]
    result = compute_defect_spacing(entries, 0.0, 2.0)
    assert result["artifact_count_excluded"] == 2
    assert len(result["natural_defects"]) == 2
    assert result["computed_gaps_mm"] == [500]


def test_compute_defect_spacing_flags_unrecognised_type_without_using_it():
    entries = [
        _entry(1.0, "P", "P, 10°, RF, PR, CN"),
        _entry(1.1, "CZ", "CZ, 30 mm thick"),
    ]
    result = compute_defect_spacing(entries, 0.0, 2.0)
    assert result["unrecognised_types"] == ["CZ"]
    assert len(result["natural_defects"]) == 1  # CZ excluded, not guessed


def test_compute_defect_spacing_prefers_stated_over_computed_per_entry():
    # A generalised-set entry's own stated spacing is used directly for
    # that entry - it does not also contribute a depth to the
    # computed-gap diffing (there's nothing to diff it against within a
    # single logged interval anyway).
    entries = [
        _entry(1.0, "J", "J, 10-20°, RF, CN, 50 mm spacing, x 2"),
        _entry(1.4, "P", "P, 5°, RF, PR, CN"),
        _entry(1.6, "P", "P, 5°, RF, PR, CN"),
    ]
    result = compute_defect_spacing(entries, 0.0, 2.0)
    assert result["stated_spacings_mm"] == [(50, 50)]
    assert result["computed_gaps_mm"] == [200]  # only the two plain P entries


def test_compute_defect_spacing_window_is_half_open():
    entries = [_entry(1.0, "P", "P"), _entry(2.0, "P", "P")]
    result = compute_defect_spacing(entries, 0.0, 2.0)
    assert len(result["natural_defects"]) == 1  # 2.0 excluded, matches next stratum


def test_compute_defect_spacing_empty_window_is_not_an_error():
    result = compute_defect_spacing([], 0.0, 5.0)
    assert result["natural_defects"] == []
    assert result["stated_spacings_mm"] == []
    assert result["computed_gaps_mm"] == []
    assert result["artifact_count_excluded"] == 0
    assert result["unrecognised_types"] == []


def test_defect_spacing_across_real_corpus_stratum_windows_does_not_crash():
    checked = 0
    for path in REFERENCE_DIR.glob("*.pdf"):
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                parsed = parse_log_page(page)
                if (parsed.get("header") or {}).get("log_type") != "Cored Borehole":
                    continue
                strata = parsed["strata"]
                for i, stratum in enumerate(strata):
                    d_from = stratum.get("depth_from_m")
                    if d_from is None:
                        continue
                    d_to = strata[i + 1]["depth_from_m"] if i + 1 < len(strata) else d_from + 1000
                    if d_to is None:
                        d_to = d_from + 1000
                    result = compute_defect_spacing(parsed["defect_entries"], d_from, d_to)
                    assert all(gap >= 0 for gap in result["computed_gaps_mm"])
                    checked += 1
    assert checked > 500  # sanity: this exercised a real, substantial sample
