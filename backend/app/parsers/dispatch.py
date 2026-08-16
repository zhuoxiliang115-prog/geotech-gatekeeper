"""Routes each PDF page to the parser for its report type.

Ported from reference/parse_reports.py's process_pdf. Each page is one
report; the report type is detected from its title line and routed to a
type-specific extractor. Pages whose title doesn't match a known report
type are flagged as unrecognized rather than silently dropped, so they can
be surfaced for manual entry per CLAUDE.md's review-step convention.
"""

import pdfplumber

from .atterberg import REPORT_TITLE_PREFIX as ATTERBERG_PREFIX
from .atterberg import parse_atterberg_page
from .common import get_report_title
from .emerson import REPORT_TITLE_PREFIX as EMERSON_PREFIX
from .emerson import parse_emerson_page
from .psd import REPORT_TITLE_PREFIX as PSD_PREFIX
from .psd import parse_psd_page


def process_pdf(file) -> dict:
    emerson_rows, psd_rows, atterberg_rows, unrecognized = [], [], [], []

    with pdfplumber.open(file) as pdf:
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
            else:
                unrecognized.append({"page": page_num, "title": title})

    return {
        "emerson_results": emerson_rows,
        "psd_results": psd_rows,
        "atterberg_results": atterberg_rows,
        "unrecognized_pages": unrecognized,
    }
