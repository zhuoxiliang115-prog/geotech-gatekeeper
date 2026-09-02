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
    PAGE_TYPE_LOG,
    PAGE_TYPE_PHOTO_REPORT,
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
