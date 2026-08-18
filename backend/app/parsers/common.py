"""Fields and helpers shared by every report-type parser.

Ported from reference/parse_reports.py's extract_common_fields /
get_report_title. Every Macquarie Geotech report page carries the same
header fields regardless of test type, and the report type itself is
identified from the second line of the page's extracted text.
"""

import re

FIELD_PATTERNS = {
    "mg_sample_no": r"MG Sample No\.\s*([A-Za-z0-9\-]+)",
    "mg_project_no": r"MG Project No\.\s*([A-Za-z0-9\-]+)",
    "client": r"Client\s+([^\n]+?)\s+MG Sample No",
    "project": r"Project\s+([^\n]+?)\s+Date Sampled",
    "sample_id": r"Sample ID\s+([^\n]+?)\s+Date Received",
    "date_sampled": r"Date Sampled\s+(\d{1,2}/\d{1,2}/\d{4})",
    "date_received": r"Date Received\s+(\d{1,2}/\d{1,2}/\d{4})",
    "date_tested": r"Date Tested\s+(\d{1,2}/\d{1,2}/\d{4})",
    "report_no": r"Report No\.\s+([A-Za-z0-9\-_]+)",
    "sample_description": r"Sample Description\s+([^\n]+)",
}


def extract_common_fields(text: str) -> dict:
    fields = {}
    for key, pattern in FIELD_PATTERNS.items():
        m = re.search(pattern, text)
        fields[key] = m.group(1).strip() if m else None
    return fields


def get_report_title(text: str) -> str:
    lines = text.split("\n")
    return lines[1].strip() if len(lines) > 1 else ""
