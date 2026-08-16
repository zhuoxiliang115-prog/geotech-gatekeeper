"""Parser for "Determination of the particle size distribution..." reports.

Ported from reference/parse_reports.py's parse_psd_page. Unlike the other
report types this one reads a table (sieve size vs. % passing), not just
label/value text pairs, so it takes a pdfplumber page rather than raw text.
"""

import re

from .common import extract_common_fields

REPORT_TITLE_PREFIX = "Determination of the particle size distribution"


def parse_psd_page(page) -> dict:
    text = page.extract_text() or ""
    fields = extract_common_fields(text)

    sieve_sizes, passing_pct = [], []
    for table in page.extract_tables():
        for row in table:
            if not row or row[0] is None:
                continue
            cell0 = str(row[0])
            # The sieve-size column renders as one cell containing every
            # size stacked on its own line, e.g. "200\n75\n63\n37.5\n...".
            if re.match(r"^\d", cell0.strip()) and "\n" in cell0:
                sizes = [float(x) for x in cell0.split("\n") if x.strip()]
                pct = [float(x) for x in str(row[1]).split("\n") if x.strip()]
                if len(sizes) == len(pct) and len(sizes) > 5:
                    sieve_sizes, passing_pct = sizes, pct

    fields["sieve_sizes_mm"] = sieve_sizes
    fields["passing_pct"] = passing_pct
    fields["readings"] = [
        {"sieve_mm": size, "passing_pct": pct}
        for size, pct in zip(sieve_sizes, passing_pct)
    ]
    return fields
