"""Integration test for POST /upload: exercises the real FastAPI app,
pdfplumber PDF parsing, and the report-type dispatch together against a
synthetic multi-page PDF (see fixtures/build_sample_pdf.py)."""

import io

from fastapi.testclient import TestClient

from app.main import app
from tests.fixtures.build_sample_pdf import build_sample_pdf

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_upload_rejects_non_pdf():
    resp = client.post(
        "/upload",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_parses_all_report_types():
    pdf_bytes = build_sample_pdf()

    resp = client.post(
        "/upload",
        files={"file": ("sample_report.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )

    assert resp.status_code == 200
    body = resp.json()

    assert body["filename"] == "sample_report.pdf"
    assert body["pages_parsed"] == 4

    assert len(body["emerson_results"]) == 1
    emerson = body["emerson_results"][0]
    assert emerson["page"] == 1
    assert emerson["mg_sample_no"] == "S116199"
    assert emerson["emerson_class"] == 5
    assert emerson["dispersion_potential"] == "Low"

    assert len(body["atterberg_results"]) == 1
    atterberg = body["atterberg_results"][0]
    assert atterberg["page"] == 2
    assert atterberg["liquid_limit"] == 54.0
    assert atterberg["classification_zone"] == "CLAY"

    assert len(body["psd_results"]) == 1
    psd = body["psd_results"][0]
    assert psd["page"] == 3
    assert psd["sieve_sizes_mm"][:3] == [200.0, 75.0, 63.0]
    assert len(psd["readings"]) == 10

    assert len(body["unrecognized_pages"]) == 1
    assert body["unrecognized_pages"][0]["page"] == 4
    assert "California Bearing Ratio" in body["unrecognized_pages"][0]["title"]
