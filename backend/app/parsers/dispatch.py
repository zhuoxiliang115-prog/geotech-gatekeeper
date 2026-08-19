"""Routes each PDF page to the parser for its report type.

Ported from reference/parse_reports.py's process_pdf. Each page is one
report; the report type is detected from its title line and routed to a
type-specific extractor. Pages whose title doesn't match a known report
type are flagged as unrecognized rather than silently dropped, so they can
be surfaced for manual entry per CLAUDE.md's review-step convention.

Chemical COA reports (chemical_coa.py) are the one exception to the
per-page-title pattern: a COA isn't one-sample-per-page, it's a wide table
that can span the whole PDF, so it's detected once up front from the first
page and handled as a single whole-document unit instead of being routed
through the per-page loop below.
"""

import pdfplumber

from .atterberg import REPORT_TITLE_PREFIX as ATTERBERG_PREFIX
from .atterberg import parse_atterberg_page
from .cbr import REPORT_TITLE_PREFIX as CBR_PREFIX
from .cbr import parse_cbr_page
from .chemical_coa import detect_format as detect_chemical_coa_format
from .chemical_coa import parse_chemical_coa
from .common import get_report_title
from .emerson import REPORT_TITLE_PREFIX as EMERSON_PREFIX
from .emerson import parse_emerson_page
from .point_load import REPORT_TITLE_PREFIX as POINT_LOAD_PREFIX
from .point_load import parse_point_load_page
from .psd import REPORT_TITLE_PREFIX as PSD_PREFIX
from .psd import parse_psd_page
from .smdd import REPORT_TITLE_PREFIX as SMDD_PREFIX
from .smdd import parse_smdd_page


def process_pdf(file) -> dict:
    emerson_rows, psd_rows, atterberg_rows = [], [], []
    smdd_rows, cbr_rows, point_load_rows, chemical_coa_rows = [], [], [], []
    unrecognized = []

    with pdfplumber.open(file) as pdf:
        total_pages = len(pdf.pages)
        first_page_text = pdf.pages[0].extract_text() or "" if pdf.pages else ""
        coa_format = detect_chemical_coa_format(first_page_text)

        if coa_format is not None:
            chemical_coa_rows = parse_chemical_coa(pdf, coa_format)
            return {
                "emerson_results": emerson_rows,
                "psd_results": psd_rows,
                "atterberg_results": atterberg_rows,
                "smdd_results": smdd_rows,
                "cbr_results": cbr_rows,
                "point_load_results": point_load_rows,
                "chemical_coa_results": chemical_coa_rows,
                "unrecognized_pages": unrecognized,
                "total_pages": total_pages,
            }

        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            title = get_report_title(text)
            page_num = i + 1

            if title.startswith(EMERSON_PREFIX):
                row = parse_emerson_page(text)
                row["page"] = page_num
                row["report_title"] = title
                emerson_rows.append(row)
            elif title.startswith(PSD_PREFIX):
                row = parse_psd_page(page)
                row["page"] = page_num
                row["report_title"] = title
                psd_rows.append(row)
            elif title.startswith(ATTERBERG_PREFIX):
                row = parse_atterberg_page(text)
                row["page"] = page_num
                row["report_title"] = title
                atterberg_rows.append(row)
            elif title.startswith(SMDD_PREFIX):
                row = parse_smdd_page(text)
                row["page"] = page_num
                row["report_title"] = title
                smdd_rows.append(row)
            elif title.startswith(CBR_PREFIX):
                row = parse_cbr_page(text)
                row["page"] = page_num
                row["report_title"] = title
                cbr_rows.append(row)
            elif title.startswith(POINT_LOAD_PREFIX):
                readings = parse_point_load_page(page)
                for reading in readings:
                    reading["page"] = page_num
                    reading["report_title"] = title
                point_load_rows.extend(readings)
            else:
                unrecognized.append({"page": page_num, "title": title})

    return {
        "emerson_results": emerson_rows,
        "psd_results": psd_rows,
        "atterberg_results": atterberg_rows,
        "smdd_results": smdd_rows,
        "cbr_results": cbr_rows,
        "point_load_results": point_load_rows,
        "chemical_coa_results": chemical_coa_rows,
        "unrecognized_pages": unrecognized,
        "total_pages": len(pdf.pages),
    }
