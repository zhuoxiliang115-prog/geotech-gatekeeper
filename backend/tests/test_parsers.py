"""Unit tests for the report-type parsers.

The synthetic text blocks below mirror the label/value layout the regex
patterns in app/parsers expect (same shape pdfplumber's extract_text would
produce for a real Macquarie Geotech report page). The expected values are
taken from reference/emerson_results.csv and reference/atterberg_results.csv
(real parsed output from reference/parse_reports.py), so a passing test
also confirms the port didn't change parsing behavior.
"""

from app.parsers.atterberg import parse_atterberg_page
from app.parsers.common import extract_common_fields, get_report_title
from app.parsers.emerson import parse_emerson_page
from app.parsers.psd import parse_psd_page

EMERSON_TEXT = """Macquarie Geotech Pty Ltd
Determination of Emerson class number of a soil
Client Chowder Bay Developer MG Sample No. S116199
Project Chowder Bay DFI (60740478) Date Sampled 24/03/2026
Sample ID HA2_0.4-0.8 Date Received 26/03/2026
Date Tested 28/05/2026
Report No. S26240-1
Sample Description Sandy Silty CLAY, trace of gravel
Emerson Class Number: 5
Type of Water Used: Distilled
Notes
Accredited for compliance with ISO/IEC 17025
"""

EMERSON_TEXT_WITH_NOTES = """Macquarie Geotech Pty Ltd
Determination of Emerson class number of a soil
Client Chowder Bay Developer MG Sample No. S116201
Project Chowder Bay DFI (60740478) Date Sampled 24/03/2026
Sample ID ABH2_1.0-2.0 Date Received 26/03/2026
Date Tested 2/06/2026
Report No. S26240-1
Sample Description Silty Clayey SAND, trace of gravel
Emerson Class Number: 4
Type of Water Used: Distilled
Notes
Reaction with acid, calcite is present
Accredited for compliance with ISO/IEC 17025
"""

ATTERBERG_TEXT = """Macquarie Geotech Pty Ltd
Determination of the liquid limit, plastic limit and plasticity index of a soil
Client Chowder Bay Developer MG Sample No. S116199
Project Chowder Bay DFI (60740478) Date Sampled 24/03/2026
Sample ID HA2_0.4-0.8 Date Received 26/03/2026
Date Tested 28/05/2026
Report No. S26240-1
Sample Description Sandy Silty CLAY, trace of gravel
Liquid Limit (%) 54.0
Plastic Limit (%) 20.0
Plasticity Index (%) 34.0
Linear Shrinkage (%) 13.5
"""

ATTERBERG_TEXT_NON_PLASTIC = """Macquarie Geotech Pty Ltd
Determination of the liquid limit, plastic limit and plasticity index of a soil
Client Chowder Bay Developer MG Sample No. S116300
Project Chowder Bay DFI (60740478) Date Sampled 24/03/2026
Sample ID ABH9_2.0-2.5 Date Received 26/03/2026
Date Tested 28/05/2026
Report No. S26240-1
Sample Description Poorly graded SAND
Liquid Limit (%) Non-Plastic
Plastic Limit (%) Non-Plastic
Plasticity Index (%) Non-Plastic
Linear Shrinkage (%) Unobtainable
"""


def test_get_report_title():
    assert get_report_title(EMERSON_TEXT) == "Determination of Emerson class number of a soil"


def test_extract_common_fields():
    fields = extract_common_fields(EMERSON_TEXT)
    assert fields["mg_sample_no"] == "S116199"
    assert fields["client"] == "Chowder Bay Developer"
    assert fields["project"] == "Chowder Bay DFI (60740478)"
    assert fields["sample_id"] == "HA2_0.4-0.8"
    assert fields["date_sampled"] == "24/03/2026"
    assert fields["date_tested"] == "28/05/2026"
    assert fields["sample_description"] == "Sandy Silty CLAY, trace of gravel"


def test_parse_emerson_page_matches_reference_output():
    row = parse_emerson_page(EMERSON_TEXT)
    assert row["mg_sample_no"] == "S116199"
    assert row["emerson_class"] == 5
    assert row["dispersion_potential"] == "Low"
    assert row["water_type"] == "Distilled"
    assert row["notes"] is None


def test_parse_emerson_page_captures_notes():
    row = parse_emerson_page(EMERSON_TEXT_WITH_NOTES)
    assert row["emerson_class"] == 4
    assert row["dispersion_potential"] == "Low"
    assert row["notes"] == "Reaction with acid, calcite is present"


def test_parse_atterberg_page_matches_reference_output():
    row = parse_atterberg_page(ATTERBERG_TEXT)
    assert row["liquid_limit"] == 54.0
    assert row["plastic_limit"] == 20.0
    assert row["plasticity_index"] == 34.0
    assert row["linear_shrinkage_pct"] == 13.5
    assert row["non_plastic"] is False
    # A-line: PI = 0.73*(LL-20) = 0.73*34 = 24.82 -> rounds to 24.8
    assert row["a_line_pi_at_this_ll"] == 24.8
    assert row["above_a_line"] is True
    assert row["classification_zone"] == "CLAY"


def test_parse_atterberg_page_non_plastic():
    row = parse_atterberg_page(ATTERBERG_TEXT_NON_PLASTIC)
    assert row["non_plastic"] is True
    assert row["liquid_limit"] is None
    assert row["plasticity_index"] is None
    assert row["a_line_pi_at_this_ll"] is None
    assert row["classification_zone"] == "Non-Plastic"


class FakePSDPage:
    """Stand-in for a pdfplumber.Page: PSD parsing reads a table, not just
    text, so this fake reproduces the multi-line-per-cell table shape a
    real report page's extract_tables() returns."""

    def __init__(self, text, table):
        self._text = text
        self._table = table

    def extract_text(self):
        return self._text

    def extract_tables(self):
        return [self._table]


def test_parse_psd_page():
    text = "Macquarie Geotech Pty Ltd\nDetermination of the particle size distribution of a soil\nMG Sample No. S116199\n"
    table = [
        ["Sieve Size (mm)", "% Passing"],
        ["200\n75\n63\n37.5\n19\n9.5\n4.75\n2.36\n1.18\n0.6", "100\n100\n100\n98\n95\n90\n85\n80\n75\n70"],
    ]
    page = FakePSDPage(text, table)

    row = parse_psd_page(page)

    assert row["mg_sample_no"] == "S116199"
    assert row["sieve_sizes_mm"][:3] == [200.0, 75.0, 63.0]
    assert row["passing_pct"][:3] == [100.0, 100.0, 100.0]
    assert len(row["readings"]) == 10
    assert row["readings"][0] == {"sieve_mm": 200.0, "passing_pct": 100.0}
