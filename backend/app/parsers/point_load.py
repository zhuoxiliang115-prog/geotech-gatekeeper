"""Parser for "Determination of point load strength index" (Point Load)
reports.

Unlike the other Macquarie Geotech report types, one PDF page here holds a
table of *multiple* samples (each with a Diametral and/or Axial test row),
not one sample per page. So this parser returns a list of readings per
page rather than a single dict, and dispatch.py extends its results list
with that instead of appending one row.

The lab already reports both the uncorrected Is and the size-corrected
Is50 directly - there's no equivalent core diameter (De) printed on this
report, so calculations.point_load_is50 can't be re-derived from this
PDF's data; the parser just carries the lab's own reported values through.
"""

REPORT_TITLE_PREFIX = "Determination of point load strength index"

_HEADER_SAMPLE_NO_LABEL = "MG\nSample\nNo."
_HEADER_SAMPLE_ID_LABEL = "Sample ID"


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _find_results_rows(page):
    """Returns the data rows following the column-header row, wherever it
    falls within the page's table (the report's preamble fields and the
    results table are all one pdfplumber table on these pages)."""
    for table in page.extract_tables():
        for i, row in enumerate(table):
            if len(row) >= 2 and row[0] == _HEADER_SAMPLE_NO_LABEL and row[1] == _HEADER_SAMPLE_ID_LABEL:
                return table[i + 1 :]
    return []


def parse_point_load_page(page) -> list:
    rows = _find_results_rows(page)

    readings = []
    current_sample = None

    for row in rows:
        (
            mg_sample_no,
            sample_id,
            date_sampled,
            date_tested,
            lithology,
            moisture_condition,
            test_type,
            failure_load_kn,
            uncorrected_is,
            corrected_is50,
            failure_mode,
        ) = (row + [None] * 11)[:11]

        if mg_sample_no is not None:
            current_sample = {
                "mg_sample_no": mg_sample_no,
                "sample_id": sample_id,
                "date_sampled": date_sampled,
                "date_tested": date_tested,
                "lithology": lithology,
                "moisture_condition": moisture_condition,
            }

        if current_sample is None or test_type in (None, "-"):
            continue

        readings.append(
            {
                **current_sample,
                "test_type": test_type,
                "failure_load_kn": _to_float(failure_load_kn),
                "uncorrected_is": _to_float(uncorrected_is),
                "corrected_is50": _to_float(corrected_is50),
                "failure_mode": _to_int(failure_mode),
            }
        )

    return readings
