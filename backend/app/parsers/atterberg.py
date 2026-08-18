"""Parser for "Determination of the liquid limit, plastic limit..." reports.

Ported from reference/parse_reports.py's parse_atterberg_page.
"""

import re

from .common import extract_common_fields

REPORT_TITLE_PREFIX = "Determination of the liquid limit"


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_atterberg_page(text: str) -> dict:
    fields = extract_common_fields(text)

    def grab(label: str):
        m = re.search(re.escape(label) + r"\s*\(%\)\s*([\d.]+|Non-Plastic|Unobtainable)", text)
        return m.group(1) if m else None

    ll_raw = grab("Liquid Limit")
    pl_raw = grab("Plastic Limit")
    pi_raw = grab("Plasticity Index")
    ls_m = re.search(r"Linear Shrinkage \(%\)\s*([\d.]+|Unobtainable)", text)

    fields["liquid_limit"] = _to_float(ll_raw)
    fields["plastic_limit"] = _to_float(pl_raw)
    fields["plasticity_index"] = _to_float(pi_raw)
    fields["linear_shrinkage_pct"] = _to_float(ls_m.group(1)) if ls_m else None
    fields["non_plastic"] = ll_raw == "Non-Plastic"

    # A-line classification (AS1726 / Casagrande): PI = 0.73(LL-20).
    # Show the formula's output alongside the raw PI so the review step
    # can compare "what we measured" against "what the lookup says".
    if fields["liquid_limit"] is not None and fields["plasticity_index"] is not None:
        a_line_pi = 0.73 * (fields["liquid_limit"] - 20)
        fields["a_line_pi_at_this_ll"] = round(a_line_pi, 1)
        fields["above_a_line"] = fields["plasticity_index"] > a_line_pi
        fields["classification_zone"] = "CLAY" if fields["above_a_line"] else "SILT"
    else:
        fields["a_line_pi_at_this_ll"] = None
        fields["above_a_line"] = None
        fields["classification_zone"] = "Non-Plastic" if fields["non_plastic"] else None

    return fields
