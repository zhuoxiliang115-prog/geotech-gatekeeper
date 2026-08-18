"""Unit tests for the Phase 1 parsers (SMDD, CBR, Point Load, chemical
COA), checked against the real sample PDFs in reference/ - not synthetic
fixtures, since real reports were provided for this phase."""

from pathlib import Path

import pdfplumber

from app.parsers.cbr import parse_cbr_page
from app.parsers.chemical_coa import detect_format, parse_als_coa, parse_envirolab_coa
from app.parsers.point_load import parse_point_load_page
from app.parsers.smdd import parse_smdd_page

REFERENCE_DIR = Path(__file__).resolve().parents[2] / "reference"


def _page_text(filename, page=0):
    with pdfplumber.open(REFERENCE_DIR / filename) as pdf:
        return pdf.pages[page].extract_text()


# ---------- SMDD ----------


def test_parse_smdd_page_s116201():
    row = parse_smdd_page(_page_text("S116201-T_SMDD.pdf"))
    assert row["mg_sample_no"] == "S116201"
    assert row["sample_id"] == "ABH2_1.0-2.0"
    assert row["max_dry_density_t_m3"] == 1.91
    assert row["optimum_moisture_content_pct"] == 12.9
    assert row["oversize_retained_19mm_pct"] == 1.0
    assert row["oversize_retained_37_5mm_pct"] == 0.0
    assert row["mould_size_and_fraction"] == "1L Mould, -19 mm Test Fraction"
    assert row["notes"] is None


def test_parse_smdd_page_s116202():
    row = parse_smdd_page(_page_text("S116202-T_SMDD.pdf"))
    assert row["mg_sample_no"] == "S116202"
    assert row["max_dry_density_t_m3"] == 1.95
    assert row["optimum_moisture_content_pct"] == 10.3


# ---------- CBR ----------


def test_parse_cbr_page_governs_at_2_5mm():
    row = parse_cbr_page(_page_text("S116201-T_CBR.pdf"))
    assert row["mg_sample_no"] == "S116201"
    assert row["cbr_governing_penetration_mm"] == 2.5
    assert row["cbr_value_pct"] == 12.0
    assert row["achieved_target"]["lab_moisture_ratio_pct"] == {"achieved": 98.0, "target": 100.0}
    assert row["achieved_target"]["lab_density_ratio_pct"] == {"achieved": 100.0, "target": 100.0}
    assert row["achieved_target"]["dry_density_at_compaction_t_m3"] == {"achieved": 1.91, "target": 1.91}
    assert row["dry_density_after_soaking_t_m3"] == 1.90
    assert row["specimen_swell_pct"] == 0.7


def test_parse_cbr_page_governs_at_5mm():
    row = parse_cbr_page(_page_text("S116202-T_CBR.pdf"))
    assert row["mg_sample_no"] == "S116202"
    assert row["cbr_governing_penetration_mm"] == 5.0
    assert row["cbr_value_pct"] == 4.5
    assert row["curing_time"] == "74 hrs"


# ---------- Point Load ----------


def test_parse_point_load_page_first_sample():
    with pdfplumber.open(REFERENCE_DIR / "S116569-to-S116619-AS_PLT.pdf") as pdf:
        readings = parse_point_load_page(pdf.pages[0])

    assert readings[0] == {
        "mg_sample_no": "S116569",
        "sample_id": "ABH01 0.3-0.4m",
        "date_sampled": "Unknown",
        "date_tested": "27/05/2026",
        "lithology": "Rock Core",
        "moisture_condition": "Moist",
        "test_type": "Diametral",
        "failure_load_kn": 3.1,
        "uncorrected_is": 1.3,
        "corrected_is50": 1.3,
        "failure_mode": 1,
    }
    assert readings[1]["test_type"] == "Axial"
    assert readings[1]["mg_sample_no"] == "S116569"


def test_parse_point_load_skips_missing_test_type():
    # S116582 (page 2) has no Diametral test - the PDF prints a row of
    # dashes for it, which should be skipped rather than produce a
    # reading of dashes.
    with pdfplumber.open(REFERENCE_DIR / "S116569-to-S116619-AS_PLT.pdf") as pdf:
        readings = parse_point_load_page(pdf.pages[1])

    s116582_readings = [r for r in readings if r["mg_sample_no"] == "S116582"]
    assert len(s116582_readings) == 1
    assert s116582_readings[0]["test_type"] == "Axial"


def test_parse_point_load_total_across_document():
    total = 0
    with pdfplumber.open(REFERENCE_DIR / "S116569-to-S116619-AS_PLT.pdf") as pdf:
        for page in pdf.pages:
            total += len(parse_point_load_page(page))
    assert total == 115


# ---------- Chemical COA ----------


def test_detect_format_als():
    text = _page_text("ALS-COA-ES2604846.pdf")
    assert detect_format(text) == "als"


def test_detect_format_envirolab():
    text = _page_text("Envirolab-COA-409603.pdf")
    assert detect_format(text) == "envirolab"


def test_detect_format_none_for_unrelated_text():
    assert detect_format("Determination of Emerson class number of a soil") is None


def test_parse_als_coa():
    with pdfplumber.open(REFERENCE_DIR / "ALS-COA-ES2604846.pdf") as pdf:
        samples = parse_als_coa(pdf)

    assert len(samples) == 15

    first = samples[0]
    assert first["sample_id"] == "BH01-0-0.6"
    assert first["lab_reference"] == "ES2604846-001"
    assert first["ph"] == 7.9
    assert first["ec_us_cm"] == 53.0
    assert first["resistivity_ohm_cm"] == 18900.0
    assert first["chloride_mg_kg"] == 40.0
    # sample 1's sulfate was reported as "<10" (below limit of reporting)
    assert first["sulfate_mg_kg"] is None
    assert first["sulfate_mg_kg_below_lor"] == 10.0

    # sample 3 (BH02-1.8-2.5) had no results reported at all for this batch
    third = samples[2]
    assert third["sample_id"] == "BH02-1.8-2.5"
    assert third["ph"] is None


def test_parse_envirolab_coa():
    with pdfplumber.open(REFERENCE_DIR / "Envirolab-COA-409603.pdf") as pdf:
        samples = parse_envirolab_coa(pdf)

    assert len(samples) == 10

    by_mg_no = {s["mg_sample_no"]: s for s in samples}
    s116199 = by_mg_no["S116199"]
    assert s116199["sample_id"] == "HA2_0.4-0.8"
    assert s116199["ph"] == 4.9
    assert s116199["ec_us_cm"] == 90.0
    assert s116199["chloride_mg_kg"] == 28.0
    assert s116199["sulfate_mg_kg"] == 110.0
    # reported as 110 ohm*m in the PDF; normalized to ohm*cm (x100)
    assert s116199["resistivity_ohm_m"] == 110.0
    assert s116199["resistivity_ohm_cm"] == 11000.0

    # second block on the same page (samples 6-10) parses too
    s116204 = by_mg_no["S116204"]
    assert s116204["sample_id"] == "ABH2_2-3"
    assert s116204["ph"] == 5.2


def test_parse_envirolab_coa_ignores_quality_control_table():
    # page 4 is a QC (blank/duplicate/spike) table with the same analyte
    # row labels but no "Your Reference" sample block - must not leak
    # duplicate/blank QC numbers into the results as if they were samples.
    with pdfplumber.open(REFERENCE_DIR / "Envirolab-COA-409603.pdf") as pdf:
        samples = parse_envirolab_coa(pdf)

    assert all(s["page"] != 4 for s in samples)
