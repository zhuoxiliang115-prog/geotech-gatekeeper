"""Integration tests for POST /soil-parameters, uploading real sample log
PDFs end to end through the actual FastAPI app - no LLM/API calls
involved (this endpoint is rules-only), so unlike /review-log's tests
there's nothing to stub."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "reference" / "logs"


def _upload(filename):
    with open(REFERENCE_DIR / filename, "rb") as f:
        return client.post("/soil-parameters", files={"file": (filename, f, "application/pdf")})


def test_rejects_non_pdf():
    resp = client.post("/soil-parameters", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 400


def test_rejects_empty_file():
    resp = client.post("/soil-parameters", files={"file": ("empty.pdf", b"", "application/pdf")})
    assert resp.status_code == 400


def test_alex_canal_end_to_end_response_shape():
    resp = _upload("Alex Canal.pdf")
    assert resp.status_code == 200
    data = resp.json()

    assert data["filename"] == "Alex Canal.pdf"
    assert "BH04" in data["holes"]
    assert len(data["pages_processed"]) > 0

    bh04_pages = data["holes"]["BH04"]
    assert len(bh04_pages) == 1
    strata_results = bh04_pages[0]["strata_results"]
    assert len(strata_results) > 0

    by_bucket = {
        sr["classification"]["bucket_id"]: sr
        for sr in strata_results
        if sr["classification"]["classified"]
    }
    assert "sand_medium_dense" in by_bucket
    assert "clay_stiff" in by_bucket

    clay_stiff_result = by_bucket["clay_stiff"]
    assert clay_stiff_result["parameters"]["fields"]["cu_kPa"]["value"] == "50-100"
    assert clay_stiff_result["classification"]["warnings"]  # the St/VSt transition

    unclassified = [sr for sr in strata_results if not sr["classification"]["classified"]]
    assert all(sr["parameters"] is None for sr in unclassified)
    assert all(sr["classification"]["flag"] for sr in unclassified)


def test_non_log_pages_are_excluded():
    """A photo-report or similar non-log page shouldn't appear in
    pages_processed at all (mirrors /review-log's is_log_page gating)."""
    resp = _upload("Alex Canal.pdf")
    data = resp.json()
    for page in data["pages_processed"]:
        assert page["header"] is not None


def test_cored_borehole_strata_have_empty_consistency_and_still_respond():
    """Cored Borehole logs never carry a CONSISTENCY/RELATIVE DENSITY
    column - strata there should come back with parameters: None and a
    "consistency/relative density not stated" (or out-of-scope Rock/no-
    principal-type) flag, not an error."""
    resp = _upload("Heathcote.pdf")
    assert resp.status_code == 200
    data = resp.json()

    cored_pages = [
        p for p in data["pages_processed"] if (p["header"] or {}).get("log_type") == "Cored Borehole"
    ]
    assert cored_pages
    for page in cored_pages:
        for sr in page["strata_results"]:
            assert sr["stratum"]["consistency_relative_density"] == []
