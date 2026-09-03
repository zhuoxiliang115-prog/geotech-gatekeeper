"""Unit + integration tests for the borehole log parser, checked against
the real AECOM-template sample PDFs in reference/logs/ - no synthetic
fixture, since the column-position extraction this parser relies on can't
be faithfully reproduced with reportlab's simple drawString layout (see
borehole_log.py's module docstring for why reading order alone isn't
enough here)."""

from pathlib import Path

import pdfplumber
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.parsers.borehole_log import (
    COLUMN_RANGES,
    PAGE_TYPE_LOG,
    PAGE_TYPE_PHOTO_REPORT,
    _depth_calibration,
    _MAX_OUTLIER_REJECTIONS,
    _TOTAL_DEPTH_MARGIN_M,
    classify_log_page,
    parse_log_header,
    parse_log_page,
    process_log_pdf,
)

client = TestClient(app)

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "reference" / "logs"


def _page_text(filename, page_number):
    with pdfplumber.open(REFERENCE_DIR / filename) as pdf:
        return pdf.pages[page_number - 1].extract_text()


def _parse_page(filename, page_number):
    with pdfplumber.open(REFERENCE_DIR / filename) as pdf:
        return parse_log_page(pdf.pages[page_number - 1])


def test_classify_log_page_borehole():
    text = _page_text("WSM_ BH Logs FINAL.pdf", 1)
    assert classify_log_page(text) == PAGE_TYPE_LOG


def test_classify_log_page_photo_report():
    text = _page_text("Alex Canal.pdf", 2)
    assert classify_log_page(text) == PAGE_TYPE_PHOTO_REPORT


def test_parse_log_header_borehole():
    header = parse_log_header(_page_text("WSM_ BH Logs FINAL.pdf", 1))
    assert header["log_type"] == "Borehole"
    assert header["hole_id"] == "WSM_BH01"
    assert header["sheet"] == 1
    assert header["sheet_total"] == 4
    assert header["client"] == "Sydney Water"
    assert header["project_no"] == "60764076"
    assert header["driller"] == "Hard Access Drilling"
    assert header["rl_m"] == "50.96"
    assert header["total_depth_m"] == "18.85"
    assert header["continued_to_next"] is True
    assert header["continued_from_previous"] is False


def test_parse_log_header_pavement_dip():
    header = parse_log_header(_page_text("PRUP_AC Logs.pdf", 1))
    assert header["log_type"] == "Pavement Dip"
    assert header["hole_id"] == "PRUP_AC01L"
    assert header["client"] == "TfNSW"


def test_parse_log_header_test_pit_uses_operator_not_driller():
    header = parse_log_header(_page_text("PRUP_TP Logs.pdf", 1))
    assert header["log_type"] == "Test Pit"
    assert header["operator"] == "Durkin"
    assert header["driller"] is None


def test_parse_log_page_extracts_spt_and_samples():
    result = _parse_page("WSM_ BH Logs FINAL.pdf", 1)
    assert result["page_type"] == PAGE_TYPE_LOG
    assert result["depth_axis_calibrated"] is True

    entries = result["field_test_entries"]
    spt_entries = [e for e in entries if e["type"] == "SPT"]
    assert len(spt_entries) >= 3

    first_spt = spt_entries[0]
    assert first_spt["depth_from_m"] == 1.5
    assert first_spt["depth_to_m"] == 1.95
    assert first_spt["blows"] == "9,19,13"
    assert first_spt["n_value"] == "32"

    refusal = next(e for e in spt_entries if e["n_value"] == "R")
    assert "HB" in refusal["blows"]

    es_entries = [e for e in entries if e["type"] == "ES"]
    assert any(e["pid_ppm"] is not None for e in es_entries)


def test_parse_log_page_estimates_strata_depths():
    result = _parse_page("WSM_ BH Logs FINAL.pdf", 1)
    strata = result["strata"]
    assert len(strata) >= 2
    assert "TOPSOIL" in strata[0]["text"]
    assert all(s["depth_estimated"] for s in strata)
    depths = [s["depth_from_m"] for s in strata]
    assert depths == sorted(depths)


def test_parse_log_page_skips_photo_report():
    result = _parse_page("Alex Canal.pdf", 2)
    assert result == {"page_type": PAGE_TYPE_PHOTO_REPORT}


def test_parse_log_page_extracts_point_load_readings():
    result = _parse_page("Heathcote.pdf", 2)
    readings = result["point_load_ucs_readings"]
    types = {r["type"] for r in readings}
    assert "point_load_is50_d" in types
    assert "point_load_is50_a" in types


def test_parse_log_page_extracts_dcp_readings_test_pit():
    result = _parse_page("PRUP_TP Logs.pdf", 1)
    readings = result["dcp_readings"]
    assert len(readings) >= 10
    assert all(r["penetration_mm"] == 100 for r in readings)
    assert all(not r["partial_penetration"] for r in readings)
    assert all(isinstance(r["blows"], int) for r in readings)


def test_parse_log_page_extracts_dcp_partial_penetration():
    result = _parse_page("PRUP_PTP Logs.pdf", 1)
    partials = [r for r in result["dcp_readings"] if r["partial_penetration"]]
    assert partials
    reading = partials[0]
    assert reading["blows"] == 25
    assert reading["penetration_mm"] == 70


def test_parse_log_page_no_dcp_readings_on_cored_borehole():
    # Cored boreholes use point load/UCS, not DCP - the field-tests column
    # holds Is(50)/UCS text there instead of bare blow-count integers.
    result = _parse_page("Heathcote.pdf", 2)
    assert result["dcp_readings"] == []


def test_cored_borehole_rock_type_label_survives_in_description():
    # Regression test: the shared soil description-column range (198,429)
    # was clipping "SANDSTONE:" (x0=162, below the soil range's left
    # bound) and letting the WEATHERING code (x0~301+) bleed into it
    # instead - confirmed systematic across every Cored Borehole page in
    # the corpus.
    result = _parse_page("PRUP_BH Logs.pdf", 2)
    assert result["header"]["log_type"] == "Cored Borehole"
    first = result["strata"][0]
    assert first["text"].startswith("SANDSTONE:")
    assert "XW" not in first["text"]  # the weathering code, not description


def test_cored_borehole_weathering_attached_per_stratum():
    result = _parse_page("PRUP_BH Logs.pdf", 2)
    strata = result["strata"]
    assert strata[0]["weathering"] == ["XW"]
    # A printed transition ("HW to MW") wraps across separate pdfplumber
    # rows, the same shape as soil's "St to VSt" - split into codes plus a
    # connector, not treated as a single unrecognised token.
    assert strata[2]["weathering"] == ["HW", "to", "MW"]


def test_soil_strata_have_no_weathering_field_populated():
    # consistency_relative_density/moisture_condition are soil-only;
    # weathering is Cored-Borehole-only - every stratum carries all three
    # keys regardless of type, but only the applicable ones are ever
    # populated.
    result = _parse_page("Alex Canal.pdf", 4)
    assert result["header"]["log_type"] == "Borehole"
    for stratum in result["strata"]:
        assert stratum["weathering"] == []


def test_rock_formation_extracted_on_first_sheet_of_a_run():
    result = _parse_page("PRUP_BH Logs.pdf", 2)
    assert result["header"]["sheet"] == 2
    assert result["rock_formation"] == "BULGO SANDSTONE"
    # The formation name isn't a defect description - it shouldn't leak
    # into notes.
    assert not any("BULGO" in n for n in result["notes"])


def test_rock_formation_absent_on_continuation_sheets():
    # BULGO SANDSTONE is stated once, on sheet 2 - it doesn't repeat on
    # PRUP_BH01's sheets 3/4, matching real AECOM logging practice (stated
    # once per rock run, not once per printed page).
    result = _parse_page("PRUP_BH Logs.pdf", 3)
    assert result["header"]["sheet"] == 3
    assert result["rock_formation"] is None


def test_cored_borehole_defect_description_keeps_full_depth_prefix():
    # Regression test: the shared soil notes-column range (429,600) was
    # clipping the leading digit off the overwhelming majority (2866 of
    # 2882 sampled) of defect-description depth prefixes on Cored
    # Borehole pages (real text starts as low as x0=417).
    result = _parse_page("PRUP_BH Logs.pdf", 2)
    assert any(n.startswith("3.06 m:") for n in result["notes"])


def test_depth_axis_not_poisoned_by_drill_rig_model_number():
    # Regression test: "Drill Rig: Commachio MC 450" prints "450" alone at
    # x0=134, inside the Cored Borehole DEPTH column's tick range
    # (125-141) - previously included as a bogus tick at top=138 (above
    # the header/body boundary), badly distorting the linear fit since
    # it's one wild outlier among the ~9 real ticks. Confirmed on 91 of
    # 169 Cored Borehole pages in the corpus.
    result = _parse_page("PRUP_BH Logs.pdf", 2)
    depths = [s["depth_from_m"] for s in result["strata"] if s["depth_from_m"] is not None]
    assert depths, "expected at least one calibrated depth"
    assert all(0 <= d <= 20 for d in depths)
    # Strictly increasing down the page - a poisoned fit produced
    # decreasing/negative values instead.
    assert depths == sorted(depths)


def test_borehole_depth_axis_not_poisoned_by_rl_column():
    # Regression test: PRUP_BH01 page 1 (a plain "Borehole" sheet, not
    # Cored Borehole) prints an RL (Reduced Level) column right next to
    # DEPTH - RL's tick-like values ("311.0", "310.0", ...) render at
    # x0=146.3, 1pt outside COLUMN_RANGES["rl"]'s declared upper bound
    # (145) and inside the old shared depth range's lower bound (145),
    # so they got vacuumed up as depth ticks alongside the genuine ones
    # at x0=164.3 - the same "wild outliers poison the linear fit"
    # failure mode as the Cored Borehole "MC 450" bug above, just via a
    # different column. Previously produced depths of 154-160m on a
    # 20.32m-deep hole; only surfaced once the Design Parameters UI's
    # depth-sorted merge made the resulting wrong sort order visible.
    result = _parse_page("PRUP_BH Logs.pdf", 1)
    depths = [s["depth_from_m"] for s in result["strata"] if s["depth_from_m"] is not None]
    assert depths, "expected at least one calibrated depth"
    assert all(0 <= d <= 20.32 for d in depths)
    assert depths == sorted(depths)


# ---------- _depth_calibration hardening: generic outlier rejection + validation ----------
#
# The two regressions above were each caught only because a symptom
# happened to be visible - neither is reproducible with real corpus data
# any more (both windows are already fixed), so the paths these tests
# exercise (recovering a fit despite an outlier, failing closed under
# heavy contamination, and the <=2-tick case residuals can't diagnose at
# all) use synthetic word dicts, the same "real corpus where it exists,
# synthetic for paths it doesn't happen to exercise" convention already
# used in rock_parameters' test suite. _depth_calibration takes already-
# extracted word dicts, not a PDF, so this doesn't run into this file's
# usual objection to synthetic fixtures (reportlab can't reproduce
# pdfplumber's real column layout - that's irrelevant here, since no PDF
# is involved at this level).


def _tick_words(ticks, x0=130.0):
    return [{"top": top, "x0": x0, "x1": x0 + 5, "text": f"{value:.1f}"} for top, value in ticks]


def test_outlier_rejection_budget_and_total_depth_margin_are_the_documented_values():
    # Locks in the two constants' rationale (see their comments in
    # borehole_log.py) as an actual assertion, not just a comment someone
    # could silently drift out of sync with the code: 2 rejections is
    # deliberately small (a rescue for a straggler or two, not a badly-
    # scoped window), and 15.0m was raised from an initial, too-tight 3.0
    # after real corpus data (Heathcote DBH01) showed a legitimate axis
    # overshoot of 7.9m past total_depth_m.
    assert _MAX_OUTLIER_REJECTIONS == 2
    assert _TOTAL_DEPTH_MARGIN_M == 15.0


def test_depth_calibration_recovers_a_single_stray_outlier_tick():
    # 9 genuine, perfectly-spaced ticks (0.0-8.0m) plus one wild point
    # that doesn't belong (mimicking a stray non-depth token landing in
    # the window) - the fit should reject and drop the outlier, not
    # refuse to calibrate a page that's otherwise fine.
    genuine = [(210.0 + i * 70.85, float(i)) for i in range(9)]
    words = _tick_words(genuine + [(400.0, 450.0)])
    depth_of = _depth_calibration(words, "Cored Borehole", total_depth_m="9.0")
    assert depth_of is not None
    assert depth_of(210.0) == pytest.approx(0.0, abs=0.05)
    assert depth_of(774.5) == pytest.approx(8.0, abs=0.05)


def test_depth_calibration_fails_closed_when_contamination_exceeds_rejection_budget():
    # 8 genuine ticks plus 8 RL-like contaminants (the actual scale of
    # the historical PRUP_BH01 case) - far more bad points than
    # _MAX_OUTLIER_REJECTIONS allows to trim. Must return None (the
    # existing, safe "uncalibrated" fallback) rather than keep deleting
    # points until something happens to fit.
    genuine = [(207.6 + i * 70.85, float(i)) for i in range(8)]
    contaminants = [(221.7 + i * 70.85, 311.0 - i) for i in range(8)]
    words = _tick_words(genuine + contaminants)
    assert _depth_calibration(words, "Cored Borehole", total_depth_m="9.0") is None


def test_depth_calibration_rejects_an_implausible_two_tick_fit():
    # Exactly two points always fit a perfect line (R^2=1, residual=0) -
    # residual/R^2 rejection literally cannot distinguish a genuine pair
    # from a coincidental one. This is exactly why the output-side
    # total_depth_m check exists: two points implying depths of 500m/600m
    # on an 9m-deep hole must still be rejected.
    words = _tick_words([(210.0, 500.0), (280.85, 600.0)])
    assert _depth_calibration(words, "Cored Borehole", total_depth_m="9.0") is None


def test_depth_calibration_accepts_a_valid_two_tick_fit():
    # The mirror case: two genuine-looking points within a plausible
    # range must still calibrate - the total_depth_m check is a sanity
    # backstop, not a reason to require 3+ ticks.
    words = _tick_words([(210.0, 0.0), (280.85, 1.0)])
    depth_of = _depth_calibration(words, "Cored Borehole", total_depth_m="9.0")
    assert depth_of is not None
    assert depth_of(210.0) == pytest.approx(0.0, abs=0.01)


def test_depth_calibration_accepts_legitimate_axis_overshoot_past_total_depth():
    # Real corpus case, not synthetic: Heathcote.pdf p26 (DBH01) prints a
    # depth-axis grid running 0-8m even though the hole's own printed
    # Total Depth is 1.8m - the axis is a fixed template feature, not
    # clipped to where the hole actually terminated. This must still
    # calibrate; a tight total_depth_m bound would wrongly reject it
    # (this exact page was the false-positive that fixed
    # _TOTAL_DEPTH_MARGIN_M at 15.0, up from an initial too-tight 3.0).
    result = _parse_page("Heathcote.pdf", 26)
    assert result["header"]["hole_id"] == "DBH01"
    assert result["header"]["total_depth_m"] == "1.8"
    assert result["depth_axis_calibrated"] is True


def test_depth_calibration_validation_alone_catches_the_historical_rl_bug():
    # Proves the R^2/residual + total_depth_m/monotonicity validation is
    # a genuine second line of defense, not just theoretical - reproduces
    # the exact historical failure using real PRUP_BH01 p1 word data
    # under the OLD, pre-fix (145-165) window (COLUMN_RANGES["depth"],
    # still used as-is for Pavement Dip's fallback, coincidentally equal
    # to the old Borehole window). Even with the contamination let all
    # the way through, the validation must still reject it - the window
    # narrowing and this validation are independent safety nets, not one
    # relying on the other having already fixed things.
    with pdfplumber.open(REFERENCE_DIR / "PRUP_BH Logs.pdf") as pdf:
        words = pdf.pages[0].extract_words(use_text_flow=False, keep_blank_chars=False)
    assert COLUMN_RANGES["depth"] == (145, 165), "test assumes this is still the old, wider window"
    depth_of = _depth_calibration(words, log_type="Pavement Dip", total_depth_m="20.32")
    assert depth_of is None


# ---------- Borehole two-digit continuation-sheet ticks (split-range window) ----------


def test_continuation_sheet_two_digit_ticks_now_calibrate():
    # Alex Canal p11 (BH06's sheet 2, covering ~10-20m) prints only
    # two-digit depth ticks - none of the single-digit ones a (147,165)
    # window alone would catch. Previously came back uncalibrated
    # entirely (0 usable ticks); the added (144.0, 145.5) sub-range picks
    # up the two-digit cluster (x0=144.5, and 144.8 for "11.0"
    # specifically - a font-kerning quirk, still the same column).
    result = _parse_page("Alex Canal.pdf", 11)
    assert result["header"]["hole_id"] == "BH06"
    assert result["depth_axis_calibrated"] is True
    depths = [s["depth_from_m"] for s in result["strata"] if s["depth_from_m"] is not None]
    assert depths
    assert all(9 <= d <= 21 for d in depths)
    assert depths == sorted(depths)


def test_prup_rl_contamination_still_excluded_after_split_range_widen():
    # The split-range window touches the same "Borehole" log_type PRUP_BH01
    # p1 uses (see test_borehole_depth_axis_not_poisoned_by_rl_column
    # above) - confirms widening for the two-digit cluster didn't
    # reopen the RL gap the original fix closed. The two sub-ranges are
    # disjoint by design (144.0-145.5 and 147-165, leaving 146.3 excluded
    # in between); this is the real-corpus proof that holds in practice,
    # not just in the range arithmetic.
    result = _parse_page("PRUP_BH Logs.pdf", 1)
    depths = [s["depth_from_m"] for s in result["strata"] if s["depth_from_m"] is not None]
    assert depths
    assert all(0 <= d <= 20.32 for d in depths)
    assert depths == sorted(depths)


def test_defect_entries_are_depth_tagged_and_typed():
    result = _parse_page("PRUP_BH Logs.pdf", 3)
    entries = result["defect_entries"]
    assert len(entries) > 20
    first = entries[0]
    assert first["depth_from_m"] == 7.96
    assert first["depth_to_m"] == 7.96
    assert first["type"] == "P"
    assert first["text"] == "P, 0-10°, RF, PR, SN Fe"


def test_defect_entry_depth_range_from_a_ranged_prefix():
    # "3.10-3.18 m:" - a range, not a point - depth_to_m should reflect
    # the printed range, not silently collapse to depth_from_m.
    result = _parse_page("PRUP_BH Logs.pdf", 2)
    ranged = next(e for e in result["defect_entries"] if e["depth_from_m"] == 3.10)
    assert ranged["depth_to_m"] == 3.18


def test_defect_entry_wrapped_continuation_line_is_merged():
    # Regression test: "...40-60 mm" / "spacing, x 3" print as two visual
    # rows for one defect - the state machine (mirroring
    # _extract_field_test_entries) should merge them into a single entry,
    # not two.
    result = _parse_page("PRUP_BH Logs.pdf", 3)
    merged = next(e for e in result["defect_entries"] if e["depth_from_m"] == 12.80)
    assert merged["text"] == "P, 20°, RF, UN, SN Fe, 40-60 mm spacing, x 3"
    assert not any(e["text"].strip() == "spacing, x 3" for e in result["defect_entries"])


def test_defect_entries_keep_every_type_including_artifacts_and_unrecognised():
    # borehole_log.py doesn't decide natural-vs-artifact-vs-unrecognised -
    # that's rock_parameters/defects.py's job. Every entry survives here,
    # typed, so nothing is silently lost before that decision is made.
    result = _parse_page("Heathcote.pdf", 91)
    types = {e["type"] for e in result["defect_entries"]}
    assert "CZ" in types  # unrecognised - not in rules.VALID_DEFECT_TYPES


def test_defect_entries_empty_on_soil_log_types():
    result = _parse_page("Alex Canal.pdf", 4)
    assert result["header"]["log_type"] == "Borehole"
    assert result["defect_entries"] == []


def test_cored_borehole_fix_holds_on_a_second_independent_file():
    # Not assumed from PRUP_BH01 alone - Heathcote.pdf is a different
    # project/template instance with its own weathering/notes column
    # x-positions (see the module's calibration comments).
    result = _parse_page("Heathcote.pdf", 2)
    assert result["header"]["log_type"] == "Cored Borehole"
    assert result["strata"][0]["text"].startswith("SANDSTONE:")
    assert result["rock_formation"] == "HAWKESBURY SANDSTONE"
    depths = [s["depth_from_m"] for s in result["strata"] if s["depth_from_m"] is not None]
    assert depths == sorted(depths)


def test_depth_axis_calibrated_for_cored_borehole():
    # Regression test for the fix: Cored Borehole's DEPTH column ticks sit
    # at x≈130, outside the Borehole/Pavement Dip column range - previously
    # always reported depth_axis_calibrated: false.
    result = _parse_page("Heathcote.pdf", 2)
    assert result["header"]["log_type"] == "Cored Borehole"
    assert result["depth_axis_calibrated"] is True
    assert result["strata"][0]["depth_from_m"] is not None


def test_depth_axis_calibrated_for_test_pit():
    # Regression test for the fix: Test Pit's DEPTH column ticks sit at
    # x≈193, outside the Borehole/Pavement Dip column range - previously
    # always reported depth_axis_calibrated: false.
    result = _parse_page("PRUP_TP Logs.pdf", 1)
    assert result["header"]["log_type"] == "Test Pit"
    assert result["depth_axis_calibrated"] is True
    assert result["strata"][0]["depth_from_m"] is not None


def test_depth_calibration_sweep_across_full_corpus():
    # Every log page, every one of the 4 log types (not just the 2 with a
    # known incident history) - both hardening layers plus the split-
    # range window together should now leave every real page correctly
    # calibrated: 0 pages falling back to uncalibrated, 0 pages producing
    # depths that violate the header's own printed Total Depth or aren't
    # monotonic down the page. This is the number that would have caught
    # all three bugs found in this area (MC 450, RL bleed, the two-digit
    # continuation-sheet gap) without needing to already know where to
    # look.
    checked = 0
    uncalibrated = 0
    for path in REFERENCE_DIR.glob("*.pdf"):
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                result = parse_log_page(page)
                if result.get("page_type") != PAGE_TYPE_LOG:
                    continue
                header = result.get("header") or {}
                checked += 1

                if not result.get("depth_axis_calibrated"):
                    uncalibrated += 1
                    continue

                total_depth_m = header.get("total_depth_m")
                total_depth_m = float(total_depth_m) if total_depth_m is not None else None
                bound = (total_depth_m + 20) if total_depth_m is not None else 200

                depths = [s["depth_from_m"] for s in result["strata"] if s["depth_from_m"] is not None]
                assert all(-0.5 <= d <= bound for d in depths), (path.name, header.get("hole_id"), depths)
                assert depths == sorted(depths), (path.name, header.get("hole_id"), depths)

    assert checked > 400
    assert uncalibrated == 0


@pytest.mark.parametrize(
    "filename,expected_pages",
    [
        ("PRUP_AC Logs.pdf", 16),
        ("PRUP_TP Logs.pdf", None),
    ],
)
def test_process_log_pdf_groups_pages_by_hole(filename, expected_pages):
    with open(REFERENCE_DIR / filename, "rb") as f:
        result = process_log_pdf(f)
    if expected_pages is not None:
        assert result["total_pages"] == expected_pages
    assert len(result["pages"]) == result["total_pages"]
    assert all(hole_id for hole_id in result["holes"])


def test_upload_log_endpoint():
    path = REFERENCE_DIR / "PRUP_AC Logs.pdf"
    with open(path, "rb") as f:
        resp = client.post(
            "/upload-log",
            files={"file": ("PRUP_AC Logs.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pages_parsed"] == 16
    assert body["filename"] == "PRUP_AC Logs.pdf"
    assert "PRUP_AC01L" in body["holes"]
