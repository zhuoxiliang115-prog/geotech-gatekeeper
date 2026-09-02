"""Integration tests for POST /rock-parameters, uploading real sample log
PDFs end to end through the actual FastAPI app - no LLM/API calls
involved (this endpoint is rules-only), so there's nothing to stub."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "reference" / "logs"


def _upload(filename):
    with open(REFERENCE_DIR / filename, "rb") as f:
        return client.post("/rock-parameters", files={"file": (filename, f, "application/pdf")})


def test_rejects_non_pdf():
    resp = client.post("/rock-parameters", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 400


def test_rejects_empty_file():
    resp = client.post("/rock-parameters", files={"file": ("empty.pdf", b"", "application/pdf")})
    assert resp.status_code == 400


def test_only_cored_borehole_pages_are_processed():
    # PRUP_BH Logs.pdf has both Borehole (soil) and Cored Borehole
    # sheets for the same holes - only the latter should appear here.
    resp = _upload("PRUP_BH Logs.pdf")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["pages_processed"]) > 0
    for page in data["pages_processed"]:
        assert page["header"]["log_type"] == "Cored Borehole"


def test_end_to_end_response_shape_and_is50_estimation():
    resp = _upload("WSM_ BH Logs FINAL.pdf")
    assert resp.status_code == 200
    data = resp.json()

    assert data["filename"] == "WSM_ BH Logs FINAL.pdf"
    assert len(data["holes"]) > 0

    classified = [
        sr
        for page in data["pages_processed"]
        for sr in page["strata_results"]
        if sr["classification"]["classified"]
    ]
    assert len(classified) > 50  # this file's real Is(50)-estimated coverage

    example = classified[0]
    assert example["classification"]["bucket_id"].startswith(("sandstone_class_", "shale_class_"))
    assert example["classification"]["strength"]["source"] == "is50_estimated"  # no direct UCS in this corpus
    assert example["classification"]["strength"]["confidence"] == "low"
    assert "not a direct UCS test" in example["classification"]["classification_basis"]

    parameters = example["parameters"]
    assert parameters["bucket_id"] == example["classification"]["bucket_id"]
    assert "design_table" in parameters and "hoek_brown_table" in parameters
    assert parameters["design_table"]["fields"]
    assert parameters["hoek_brown_table"]["fields"]


def test_unclassified_strata_have_null_parameters_and_a_flag():
    resp = _upload("PRUP_BH Logs.pdf")
    data = resp.json()
    unclassified = [
        sr
        for page in data["pages_processed"]
        for sr in page["strata_results"]
        if not sr["classification"]["classified"]
    ]
    assert unclassified
    assert all(sr["parameters"] is None for sr in unclassified)
    assert all(sr["classification"]["flag"] for sr in unclassified)


def test_source_note_reaches_lookup_for_the_endpoint_to_surface():
    # shale_class_5 is rare enough in this corpus that a live end-to-end
    # hit isn't guaranteed - this confirms the same lookup the endpoint
    # calls carries both source notes, matching the direct check done
    # before committing.
    from app.rock_parameters.lookup import lookup_rock_parameters

    result = lookup_rock_parameters("shale_class_5")
    assert result["design_table"]["fields"]["E_prime_MPa"]["source_note"]
    assert result["hoek_brown_table"]["fields"]["Emass_MPa"]["source_note"]
