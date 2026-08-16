"""Parser for "Determination of Emerson class number of a soil" reports.

Ported from reference/parse_reports.py's parse_emerson_page.
"""

import re

from .common import extract_common_fields

REPORT_TITLE_PREFIX = "Determination of Emerson class number"

EMERSON_DISPERSION = {
    1: "High",
    2: "High",
    3: "Medium - remoulded samples may be dispersive",
    4: "Low",
    5: "Low",
    6: "Low",
    7: "Very Low",
    8: "Very Low",
}


def parse_emerson_page(text: str) -> dict:
    fields = extract_common_fields(text)

    class_m = re.search(r"Emerson Class Number:\s*(\d+)", text)
    water_m = re.search(r"Type of Water Used:\s*([A-Za-z]+)", text)
    notes_section = re.search(r"\nNotes\n(.*?)\nAccredited", text, re.S)
    notes = notes_section.group(1).strip() if notes_section else ""

    emerson_class = int(class_m.group(1)) if class_m else None
    fields["emerson_class"] = emerson_class
    fields["water_type"] = water_m.group(1) if water_m else None
    fields["notes"] = notes if notes else None
    # Formula/lookup applied, per CLAUDE.md: show the raw value alongside
    # the classification it maps to, not just the final number.
    fields["dispersion_potential"] = EMERSON_DISPERSION.get(emerson_class)
    return fields
