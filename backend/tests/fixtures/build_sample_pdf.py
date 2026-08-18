"""Builds a synthetic multi-page PDF fixture for integration-testing the
/upload pipeline end to end, since no real Macquarie Geotech sample PDFs
ship in this repo (only their parsed CSV/PNG outputs do, under reference/).

Produces 4 pages: an Emerson report, an Atterberg report, a PSD report
(with a real ruled table so pdfplumber's table extraction is exercised,
not mocked), and one page with an unrecognized report title.
"""

import io

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 72
LINE_HEIGHT = 16


def _draw_lines(c, lines, top=PAGE_HEIGHT - 72):
    y = top
    for line in lines:
        c.drawString(LEFT_MARGIN, y, line)
        y -= LINE_HEIGHT
    return y


def _emerson_page(c):
    _draw_lines(
        c,
        [
            "Macquarie Geotech Pty Ltd",
            "Determination of Emerson class number of a soil",
            "Client Chowder Bay Developer MG Sample No. S116199",
            "Project Chowder Bay DFI (60740478) Date Sampled 24/03/2026",
            "Sample ID HA2_0.4-0.8 Date Received 26/03/2026",
            "Date Tested 28/05/2026",
            "Report No. S26240-1",
            "Sample Description Sandy Silty CLAY, trace of gravel",
            "Emerson Class Number: 5",
            "Type of Water Used: Distilled",
            "Notes",
            "Accredited for compliance with ISO/IEC 17025",
        ],
    )


def _atterberg_page(c):
    _draw_lines(
        c,
        [
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
        ],
    )


PSD_SIEVE_SIZES = [200, 75, 63, 37.5, 19, 9.5, 4.75, 2.36, 1.18, 0.6]
PSD_PASSING_PCT = [100, 100, 100, 98, 95, 90, 85, 80, 75, 70]


def _psd_page(c):
    _draw_lines(
        c,
        [
            "Macquarie Geotech Pty Ltd",
            "Determination of the particle size distribution of a soil",
            "Client Chowder Bay Developer MG Sample No. S116199",
            "Project Chowder Bay DFI (60740478) Date Sampled 24/03/2026",
            "Sample ID HA2_0.4-0.8 Date Received 26/03/2026",
            "Date Tested 28/05/2026",
            "Report No. S26240-1",
            "Sample Description Sandy Silty CLAY, trace of gravel",
        ],
    )

    # A minimal ruled 2-column, 2-row table: header row + one data row
    # whose cells stack every reading on its own line, matching how the
    # real reports' sieve-size / % passing columns come out of pdfplumber.
    table_top = PAGE_HEIGHT - 72 - (9 * LINE_HEIGHT)
    col0_x, col1_x, col2_x = LEFT_MARGIN, LEFT_MARGIN + 150, LEFT_MARGIN + 300
    header_height = LINE_HEIGHT + 6
    data_height = LINE_HEIGHT * len(PSD_SIEVE_SIZES) + 10
    table_bottom = table_top - header_height - data_height

    c.line(col0_x, table_top, col2_x, table_top)
    c.line(col0_x, table_top - header_height, col2_x, table_top - header_height)
    c.line(col0_x, table_bottom, col2_x, table_bottom)
    c.line(col0_x, table_top, col0_x, table_bottom)
    c.line(col1_x, table_top, col1_x, table_bottom)
    c.line(col2_x, table_top, col2_x, table_bottom)

    c.drawString(col0_x + 4, table_top - header_height + 6, "Sieve Size (mm)")
    c.drawString(col1_x + 4, table_top - header_height + 6, "% Passing")

    y = table_top - header_height - LINE_HEIGHT
    for size, pct in zip(PSD_SIEVE_SIZES, PSD_PASSING_PCT):
        c.drawString(col0_x + 4, y, str(size))
        c.drawString(col1_x + 4, y, str(pct))
        y -= LINE_HEIGHT


def _unrecognized_page(c):
    _draw_lines(
        c,
        [
            "Macquarie Geotech Pty Ltd",
            "Determination of the California Bearing Ratio of a soil",
            "Client Chowder Bay Developer MG Sample No. S116250",
            "Project Chowder Bay DFI (60740478) Date Sampled 24/03/2026",
        ],
    )


def build_sample_pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    for page_fn in (_emerson_page, _atterberg_page, _psd_page, _unrecognized_page):
        page_fn(c)
        c.showPage()

    c.save()
    return buf.getvalue()


if __name__ == "__main__":
    import pathlib

    out = pathlib.Path(__file__).with_name("sample_report.pdf")
    out.write_bytes(build_sample_pdf())
    print(f"Wrote {out}")
