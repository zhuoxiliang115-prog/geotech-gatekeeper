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
