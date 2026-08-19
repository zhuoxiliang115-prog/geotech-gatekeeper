"""Parser for "Dry density/moisture relationship..." (Standard Compaction /
SMDD) reports.

Field layout matches the other Macquarie Geotech single-sample reports
(extract_common_fields applies), plus SMDD-specific summary fields. The
underlying test points used to plot the compaction curve are rendered as
chart markers/axis graphics in the PDF, not as text or a table, so they
aren't extractable the way the PSD sieve table is - this parser reports the
summary values the lab PDF prints (MDD, OMC, oversize %), matching how
every other parser here only extracts real reported numbers.
"""

import re

from .common import extract_common_fields

REPORT_TITLE_PREFIX = "Dry density/moisture relationship"


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_smdd_page(text: str) -> dict:
    fields = extract_common_fields(text)

    mdd_m = re.search(r"Standard Maximum Dry Density \(t/m\S?\)\s*([\d.]+)", text)
    omc_m = re.search(r"Standard Optimum Moisture Content \(%\)\s*([\d.]+)", text)
    oversize_19_m = re.search(r"Oversize Retained on 19\s*mm Sieve \(%\)\s*([\d.]+)", text)
    oversize_37_m = re.search(r"Oversize Retained on 37\.5\s*mm Sieve \(%\)\s*([\d.]+)", text)
    mould_m = re.search(r"Nominal Mould Size & Fraction Tested\s+([^\n]+)", text)
    method_m = re.search(r"Method of Determining MDD/OMC\s+([^\n]+)", text)
    notes_section = re.search(r"\nNotes\n(.*?)\nAccredited", text, re.S)
    notes = notes_section.group(1).strip() if notes_section else ""

    fields["max_dry_density_t_m3"] = _to_float(mdd_m.group(1)) if mdd_m else None
    fields["optimum_moisture_content_pct"] = _to_float(omc_m.group(1)) if omc_m else None
    fields["oversize_retained_19mm_pct"] = _to_float(oversize_19_m.group(1)) if oversize_19_m else None
    fields["oversize_retained_37_5mm_pct"] = _to_float(oversize_37_m.group(1)) if oversize_37_m else None
    fields["mould_size_and_fraction"] = mould_m.group(1).strip() if mould_m else None
    fields["mdd_omc_method"] = method_m.group(1).strip() if method_m else None
    fields["notes"] = notes if notes else None

    return fields
