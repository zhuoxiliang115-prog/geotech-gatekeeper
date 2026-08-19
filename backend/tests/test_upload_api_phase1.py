"""Integration tests for POST /upload with the Phase 1 report types,
uploading the real sample PDFs in reference/ end to end through the actual
FastAPI app (not mocked) - same approach as test_upload_api.py's synthetic
fixture, but using real reports since real samples were provided this
phase."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "reference"


def _upload(filename):
    path = REFERENCE_DIR / filename
    with open(path, "rb") as f:
        return client.post(
            "/upload",
            files={"file": (filename, f, "application/pdf")},
        )


def test_upload_smdd_report():
    resp = _upload("S116201-T_SMDD.pdf")
    assert resp.status_code == 200
    body = resp.json()

    assert body["pages_parsed"] == 1
    assert len(body["smdd_results"]) == 1
    smdd = body["smdd_results"][0]
    assert smdd["mg_sample_no"] == "S116201"
    assert smdd["max_dry_density_t_m3"] == 1.91
    assert smdd["optimum_moisture_content_pct"] == 12.9
    assert body["unrecognized_pages"] == []


def test_upload_cbr_report():
    resp = _upload("S116201-T_CBR.pdf")
    assert resp.status_code == 200
    body = resp.json()

    assert len(body["cbr_results"]) == 1
    cbr = body["cbr_results"][0]
    assert cbr["cbr_value_pct"] == 12.0
    assert cbr["cbr_governing_penetration_mm"] == 2.5


def test_upload_point_load_report():
    resp = _upload("S116569-to-S116619-AS_PLT.pdf")
    assert resp.status_code == 200
    body = resp.json()

    assert body["pages_parsed"] == 6
    assert len(body["point_load_results"]) == 115
    first = body["point_load_results"][0]
    assert first["mg_sample_no"] == "S116569"
    assert first["test_type"] == "Diametral"
    assert first["corrected_is50"] == 1.3


def test_upload_als_chemical_coa():
    resp = _upload("ALS-COA-ES2604846.pdf")
    assert resp.status_code == 200
    body = resp.json()

    assert len(body["chemical_coa_results"]) == 15
    first = body["chemical_coa_results"][0]
    assert first["lab_format"] == "ALS"
    assert first["ph"] == 7.9
    assert first["resistivity_ohm_cm"] == 18900.0
    # nothing routed through the normal per-page dispatch for a COA
    assert body["emerson_results"] == []
    assert body["unrecognized_pages"] == []


def test_upload_envirolab_chemical_coa():
    resp = _upload("Envirolab-COA-409603.pdf")
    assert resp.status_code == 200
    body = resp.json()

    assert len(body["chemical_coa_results"]) == 10
    by_mg_no = {s["mg_sample_no"]: s for s in body["chemical_coa_results"]}
    assert by_mg_no["S116199"]["ph"] == 4.9
    assert by_mg_no["S116199"]["resistivity_ohm_cm"] == 11000.0


def test_upload_atterberg_report_includes_calculations_block():
    # regression check: the Phase 0 synthetic-PDF path still works, and
    # now also carries the new calculations block from Step 4.
    resp = client.post(
        "/upload",
        files={
            "file": (
                "sample.pdf",
                _synthetic_atterberg_pdf(),
                "application/pdf",
            )
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    row = body["atterberg_results"][0]
    assert row["calculations"]["plasticity_index"] == {
        "formula": "PI = LL - PL",
        "inputs": {"ll": 54.0, "pl": 20.0},
        "output": 34.0,
    }


def _synthetic_atterberg_pdf():
    import io

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    lines = [
        "Macquarie Geotech Pty Ltd",
        "Determination of the liquid limit, plastic limit and plasticity index of a soil",
        "Client Chowder Bay Developer MG Sample No. S116199",
        "Project Chowder Bay DFI (60740478) Date Sampled 24/03/2026",
        "Sample ID HA2_0.4-0.8 Date Received 26/03/2026",
        "Date Tested 28/05/2026",
        "Report No. S26240-1",
        "Sample Description Sandy Silty CLAY, trace of gravel",
        "Liquid Limit (%) 54.0",
        "Plastic Limit (%) 20.0",
        "Plasticity Index (%) 34.0",
        "Linear Shrinkage (%) 13.5",
    ]
    y = 800
    for line in lines:
        c.drawString(72, y, line)
        y -= 16
    c.showPage()
    c.save()
    return io.BytesIO(buf.getvalue())
