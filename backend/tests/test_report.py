"""Tests for backend/app/report.py's build_report_pdf() and the POST
/report endpoint, generating PDFs from real reference corpus data run
through the actual /review-log, /soil-parameters, and /rock-parameters
endpoints first (same real-PDF-through-real-endpoint pattern as every
other test file here), then verifying the PDF content with pdfplumber -
the same library this whole project already uses to read input PDFs.

The judgment layer's real Claude API call is monkeypatched out, same as
test_review_log_api.py - no live credentials are available in this
environment, and these tests are about report content, not model output
quality.
"""

import io
import json
from pathlib import Path

import pdfplumber
import pytest
from fastapi.testclient import TestClient

from app.borehole_review import judgment
from app.main import app
from app.report import build_report_pdf

client = TestClient(app)

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "reference"
LOGS_DIR = REFERENCE_DIR / "logs"


def _pdf_text(pdf_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        assert pdf.pages
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


@pytest.fixture(autouse=True)
def _stub_judgment_layer(monkeypatch):
    def _fake_review(parsed_page, client=None):
        if parsed_page.get("page_type") != "log":
            return {"findings": [], "error": None, "usage": None}
        return {
            "findings": [
                {
                    "judgment_category": "colour_term_plausibility",
                    "standard_section": "§3.3",
                    "finding": "stub judgment finding text",
                    "confidence": "low",
                    "uncertainty_note": "stubbed for testing",
                    "stratum_reference": None,
                    "category": "judgment_based",
                }
            ],
            "error": None,
            "usage": {
                "input_tokens": 1,
                "output_tokens": 1,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        }

    monkeypatch.setattr(judgment, "review_page_judgment", _fake_review)


def _soil_and_rock_results(filename):
    with open(LOGS_DIR / filename, "rb") as f:
        soil_resp = client.post("/soil-parameters", files={"file": (filename, f, "application/pdf")})
    with open(LOGS_DIR / filename, "rb") as f:
        rock_resp = client.post("/rock-parameters", files={"file": (filename, f, "application/pdf")})
    return soil_resp.json(), rock_resp.json()


def test_build_report_pdf_renders_soil_and_rock_parameters():
    soil_result, rock_result = _soil_and_rock_results("PRUP_BH Logs.pdf")

    pdf_bytes = build_report_pdf("PRUP_BH Logs.pdf", None, soil_result, rock_result)
    assert pdf_bytes[:5] == b"%PDF-"

    text = _pdf_text(pdf_bytes)
    assert "PRUP_BH Logs.pdf" in text
    assert "PRUP_BH01" in text
    assert "Soil Parameters" in text
    assert "Rock Parameters" in text
    # These use symbols outside reportlab's default-font glyph coverage
    # (γ, φ, ₀) - the reason report.py bundles DejaVu Sans. A regression
    # back to the default fonts would mangle these, not fail loudly.
    assert "Unit weight (γ)" in text
    assert "Effective friction angle (φ')" in text
    assert "K₀ (at-rest earth pressure)" in text
    assert "Class V" in text  # PRUP_BH01's Is(50)-estimated sandstone bucket


def test_build_report_pdf_renders_review_log_findings():
    filename = "Alex Canal.pdf"
    with open(LOGS_DIR / filename, "rb") as f:
        resp = client.post("/review-log", files={"file": (filename, f, "application/pdf")})
    review_result = resp.json()

    pdf_bytes = build_report_pdf(filename, review_result, None, None)
    text = _pdf_text(pdf_bytes)

    assert "BH01" in text
    assert "Rule-checked findings" in text
    assert "§2 (Borehole)" in text
    assert "Judgment-based findings" in text
    assert "Colour-term plausibility" in text
    assert "stub judgment finding text" in text


def test_build_report_pdf_with_no_results_still_produces_valid_pdf():
    pdf_bytes = build_report_pdf("empty.pdf", None, None, None)
    assert pdf_bytes[:5] == b"%PDF-"
    text = _pdf_text(pdf_bytes)
    assert "No holes with a recognisable hole ID were found in this file." in text


def test_report_endpoint_rejects_non_pdf():
    resp = client.post("/report", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 400


def test_report_endpoint_rejects_invalid_json_result_field():
    filename = "PRUP_BH Logs.pdf"
    with open(LOGS_DIR / filename, "rb") as f:
        resp = client.post(
            "/report",
            files={"file": (filename, f, "application/pdf")},
            data={"soil_parameters_result": "not json"},
        )
    assert resp.status_code == 400


def test_report_endpoint_with_no_result_fields_still_returns_a_pdf():
    """All three result fields are optional - a bare upload should still
    produce a (mostly empty) valid PDF rather than erroring."""
    filename = "PRUP_BH Logs.pdf"
    with open(LOGS_DIR / filename, "rb") as f:
        resp = client.post("/report", files={"file": (filename, f, "application/pdf")})
    assert resp.status_code == 200
    assert resp.content[:5] == b"%PDF-"


def test_report_endpoint_end_to_end():
    filename = "PRUP_BH Logs.pdf"
    soil_result, rock_result = _soil_and_rock_results(filename)

    with open(LOGS_DIR / filename, "rb") as f:
        resp = client.post(
            "/report",
            files={"file": (filename, f, "application/pdf")},
            data={
                "soil_parameters_result": json.dumps(soil_result),
                "rock_parameters_result": json.dumps(rock_result),
            },
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.headers["content-disposition"] == 'attachment; filename="PRUP_BH Logs-report.pdf"'
    assert resp.content[:5] == b"%PDF-"

    text = _pdf_text(resp.content)
    assert "PRUP_BH01" in text
    assert "Class V" in text
