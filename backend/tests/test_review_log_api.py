"""Integration tests for POST /review-log, uploading real sample PDFs
end to end through the actual FastAPI app. The judgment layer's real
Claude API call is monkeypatched out - no live credentials are available
in this environment, and these tests are about the endpoint's wiring
(parser -> rule engine -> judgment layer -> response shape), not model
output quality."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.borehole_review import judgment
from app.main import app

client = TestClient(app)

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "reference"
LOGS_DIR = REFERENCE_DIR / "logs"


@pytest.fixture(autouse=True)
def _stub_judgment_layer(monkeypatch):
    """Every test in this file runs without a real Claude API call."""

    def _fake_review(parsed_page, client=None):
        if parsed_page.get("page_type") != "log":
            return {"findings": [], "error": None, "usage": None}
        return {
            "findings": [
                {
                    "judgment_category": "colour_term_plausibility",
                    "standard_section": "§3.3",
                    "finding": "stub finding",
                    "confidence": "low",
                    "uncertainty_note": "stubbed for testing",
                    "stratum_reference": None,
                    "category": "judgment_based",
                }
            ],
            "error": None,
            "usage": {
                "input_tokens": 8500,
                "output_tokens": 120,
                "cache_creation_input_tokens": 8400,
                "cache_read_input_tokens": 0,
            },
        }

    monkeypatch.setattr(judgment, "review_page_judgment", _fake_review)


def _upload_log(filename, lab_report_filenames=None):
    files = [("file", (filename, open(LOGS_DIR / filename, "rb"), "application/pdf"))]
    for lab_filename in lab_report_filenames or []:
        files.append(
            ("lab_reports", (lab_filename, open(REFERENCE_DIR / lab_filename, "rb"), "application/pdf"))
        )
    try:
        return client.post("/review-log", files=files)
    finally:
        for _, (_, fh, _) in files:
            fh.close()


def test_review_log_basic_shape():
    resp = _upload_log("PRUP_AC Logs.pdf")
    assert resp.status_code == 200
    body = resp.json()

    assert body["filename"] == "PRUP_AC Logs.pdf"
    assert len(body["pages_reviewed"]) == 16
    assert body["lab_reports_provided"] == {"atterberg_samples": 0, "psd_samples": 0}

    first_page = body["pages_reviewed"][0]
    assert first_page["page_type"] == "log"
    assert "parsed" in first_page
    assert "rule_findings" in first_page
    assert "judgment_findings" in first_page
    assert first_page["judgment_error"] is None
    assert first_page["judgment_usage"]["input_tokens"] == 8500


def test_review_log_reports_model_and_aggregate_usage():
    resp = _upload_log("PRUP_AC Logs.pdf")
    body = resp.json()

    assert body["judgment_model"] == "claude-sonnet-5"
    # 16 log pages, each stubbed at the same usage figures - exact totals,
    # not an estimate.
    log_pages = [p for p in body["pages_reviewed"] if p["page_type"] == "log"]
    assert body["judgment_usage_total"] == {
        "input_tokens": 8500 * len(log_pages),
        "output_tokens": 120 * len(log_pages),
        "cache_creation_input_tokens": 8400 * len(log_pages),
        "cache_read_input_tokens": 0,
    }


def test_review_log_findings_are_tagged_by_category():
    resp = _upload_log("PRUP_AC Logs.pdf")
    body = resp.json()
    first_page = body["pages_reviewed"][0]

    assert all(f["category"] == "rule_checked" for f in first_page["rule_findings"])
    assert all(f["category"] == "judgment_based" for f in first_page["judgment_findings"])


def test_review_log_skips_lab_checks_cleanly_without_lab_reports():
    resp = _upload_log("WSM_ BH Logs FINAL.pdf")
    body = resp.json()
    first_page = body["pages_reviewed"][0]

    skipped_lab_checks = [
        f
        for f in first_page["rule_findings"]
        if f["status"] == "skipped" and "lab report was provided" in f["explanation"]
    ]
    # exactly the two lab cross-reference checks should report a clean
    # skip - not silently absent, not marked "pass".
    assert len(skipped_lab_checks) == 2
    for f in skipped_lab_checks:
        assert f["explanation"].lower().startswith("no ")


def test_review_log_groups_pages_by_hole():
    resp = _upload_log("PRUP_AC Logs.pdf")
    body = resp.json()
    assert "PRUP_AC01L" in body["holes"]
    assert body["holes"]["PRUP_AC01L"][0]["parsed"]["header"]["hole_id"] == "PRUP_AC01L"


def test_review_log_with_lab_report_attaches_lab_counts():
    resp = _upload_log("PRUP_AC Logs.pdf", lab_report_filenames=["ALS-COA-ES2604846.pdf"])
    assert resp.status_code == 200
    body = resp.json()
    # this lab report is a chemical COA, not Atterberg/PSD - counts stay 0,
    # but the request must still succeed rather than erroring on mismatch.
    assert body["lab_reports_provided"] == {"atterberg_samples": 0, "psd_samples": 0}


def test_review_log_rejects_non_pdf():
    resp = client.post("/review-log", files={"file": ("not_a_pdf.txt", b"hello", "text/plain")})
    assert resp.status_code == 400


def test_review_log_rejects_empty_file():
    resp = client.post("/review-log", files={"file": ("empty.pdf", b"", "application/pdf")})
    assert resp.status_code == 400
