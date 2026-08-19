"""Parser for "California bearing ratio of remoulded specimens..." (CBR)
reports.

Like smdd.py, the load/penetration curve itself renders as a continuous
vector-drawn line in the PDF with no discrete data points at all (unlike
SMDD's individual test-point markers) - there's nothing to extract there.
This parser captures the summary values the lab PDF actually reports: the
CBR value and its governing penetration, and the Achieved/Target
density-moisture comparison table.
"""

import re

from .common import extract_common_fields

REPORT_TITLE_PREFIX = "California bearing ratio of remoulded specimens"


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _search_float(pattern, text):
    m = re.search(pattern, text)
    return _to_float(m.group(1)) if m else None


def _search_text(pattern, text):
    m = re.search(pattern, text)
    return m.group(1).strip() if m else None


def parse_cbr_page(text: str) -> dict:
    fields = extract_common_fields(text)

    cbr_m = re.search(r"CBR Value \(%\) at ([\d.]+)\s*mm Penetration\s+([\d.]+)", text)
    fields["cbr_governing_penetration_mm"] = _to_float(cbr_m.group(1)) if cbr_m else None
    fields["cbr_value_pct"] = _to_float(cbr_m.group(2)) if cbr_m else None

    fields["material_retained_19mm_pct"] = _search_float(
        r"Material Retained on 19\.0\s*mm Sieve \(%\)\s*([\d.]+)", text
    )
    fields["plasticity_level_method"] = _search_text(
        r"Method of Establishing Plasticity Level\s+(.+?)\s+Lab Density Ratio", text
    )
    fields["curing_time"] = _search_text(
        r"Sample Curing Time \(hrs\)\s+(.+?)\s+Dry Density - At Compaction", text
    )
    fields["compaction_hammer"] = _search_text(
        r"Compaction Hammer Used\s+(.+?)\s+Dry Density - After Soaking", text
    )
    fields["surcharge_mass_kg"] = _search_float(r"Surcharge Mass Applied \(kg\)\s*([\d.]+)", text)
    fields["soaking_period_days"] = _search_float(r"Period of Soaking \(days\)\s*([\d.]+)", text)
    fields["max_dry_density_t_m3"] = _search_float(r"Maximum Dry Density \(t/m3\)\s*([\d.]+)", text)
    fields["optimum_moisture_content_pct"] = _search_float(
        r"Optimum Moisture Content \(%\)\s*([\d.]+)", text
    )
    fields["dry_density_after_soaking_t_m3"] = _search_float(
        r"Dry Density - After Soaking \(t/m3\)\s*([\d.]+)", text
    )
    fields["specimen_swell_pct"] = _search_float(r"Specimen Swell \(%\)\s*([\d.]+)", text)
    fields["moisture_at_compaction_pct"] = _search_float(
        r"Moisture Content - At Compaction \(%\)\s*([\d.]+)", text
    )
    fields["moisture_top_30mm_pct"] = _search_float(
        r"Moisture Content - Top 30\s*mm \(%\)\s*([\d.]+)", text
    )
    fields["moisture_full_depth_pct"] = _search_float(
        r"Moisture Content - Full Depth \(%\)\s*([\d.]+)", text
    )

    lmr_m = re.search(r"Lab Moisture Ratio - LMR \(%\)\s*([\d.]+)\s+([\d.]+)", text)
    ldr_m = re.search(r"Lab Density Ratio - LDR \(%\)\s*([\d.]+)\s+([\d.]+)", text)
    density_at_compaction_m = re.search(
        r"Dry Density - At Compaction \(t/m3\)\s*([\d.]+)\s+([\d.]+)", text
    )

    fields["achieved_target"] = {
        "lab_moisture_ratio_pct": {
            "achieved": _to_float(lmr_m.group(1)) if lmr_m else None,
            "target": _to_float(lmr_m.group(2)) if lmr_m else None,
        },
        "lab_density_ratio_pct": {
            "achieved": _to_float(ldr_m.group(1)) if ldr_m else None,
            "target": _to_float(ldr_m.group(2)) if ldr_m else None,
        },
        "dry_density_at_compaction_t_m3": {
            "achieved": _to_float(density_at_compaction_m.group(1)) if density_at_compaction_m else None,
            "target": _to_float(density_at_compaction_m.group(2)) if density_at_compaction_m else None,
        },
    }

    notes_section = re.search(r"\nNotes\n(.*?)\nAccredited", text, re.S)
    notes = notes_section.group(1).strip() if notes_section else ""
    fields["notes"] = notes if notes else None

    return fields
