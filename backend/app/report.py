"""Formats an already-fetched /review-log, /soil-parameters, and/or
/rock-parameters response into a single PDF, so a review can be handed to
a client instead of only viewed as a live web page.

Flat, top-level module (not nested under a feature package) - same
placement as calculations.py, the existing precedent for something used
directly by main.py that isn't owned by one feature. This module doesn't
parse or classify anything itself: build_report_pdf() takes exactly the
dicts the three existing endpoints already return and formats them, so a
future persistence layer (saving/revisiting a review) could hand this
function the same saved data with no changes here.

No database, no re-computation - purely presentational.
"""

import datetime
import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# reportlab's built-in fonts (Helvetica etc.) are the standard 14 PDF fonts,
# which don't cover Greek letters or the ⚠/₀/³/° symbols used throughout
# the design-parameter field labels and warning text (γ, φ', ν, K₀, ⚠) -
# they silently render as the wrong glyph (e.g. γ becomes "g") rather than
# erroring, so this is easy to miss without actually opening a generated
# PDF. DejaVu Sans has full coverage and its license (Bitstream Vera-based)
# permits redistribution, so it's bundled here rather than relying on a
# system font path - a hardcoded path would work on this Linux sandbox but
# not on a contributor's Windows machine, where no equivalent path exists.
_FONT_DIR = Path(__file__).parent / "fonts"
pdfmetrics.registerFont(TTFont("DejaVuSans", str(_FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(_FONT_DIR / "DejaVuSans-Bold.ttf")))

# The three check names rules.py's cross-reference checks use
# (match_lab_samples_to_log-based) vs. every other, self-contained check -
# mirrors frontend/src/components/boreholeReviewChecks.js's
# LAB_CROSS_REF_CHECKS exactly, so the report's Rule-checked/Lab
# cross-reference split matches what the live page shows. Keep these two
# lists in sync if rules.py ever adds another cross-reference check.
_LAB_CROSS_REF_CHECKS = {
    "plasticity_term_vs_lab_ll",
    "uscs_symbol_vs_lab_a_line",
    "grading_curve_symbol_vs_lab",
}

# Mirrors boreholeReviewChecks.js's JUDGMENT_CATEGORY_LABELS.
_JUDGMENT_CATEGORY_LABELS = {
    "field_id_vs_uscs_symbol": "Field ID vs. USCS symbol",
    "secondary_minor_component_wording": "Secondary/minor component wording",
    "spt_consistency_correlation": "SPT vs. consistency/density correlation",
    "geological_origin_plausibility": "Geological origin plausibility",
    "cross_sheet_continuity": "Cross-sheet continuity",
    "colour_term_plausibility": "Colour-term plausibility",
}

# Mirrors frontend/src/components/designParameterDisplay.js's
# DESIGN_TABLE_FIELD_LABELS exactly - shared by soil_parameters' single
# table and rock_parameters' design_table (rock's table has every field
# name soil's has, plus two pile/anchor-specific ones). Keep in sync with
# that file if either changes; see report.py's module docstring / the
# build plan for why this is a deliberate, commented duplication rather
# than a shared file both sides read (Vite's dev-server fs.allow boundary
# makes that real added plumbing for ~25 short strings that rarely change).
_DESIGN_TABLE_FIELD_LABELS = {
    "gamma_kNm3": "Unit weight (γ)",
    "cu_kPa": "Undrained shear strength (cu)",
    "c_prime_kPa": "Effective cohesion (c')",
    "phi_prime_deg": "Effective friction angle (φ')",
    "K0": "K₀ (at-rest earth pressure)",
    "Kp": "Kp (passive earth pressure)",
    "reduced_phi_deg": "Reduced φ' (factored)",
    "reduced_c_kPa": "Reduced c' (factored)",
    "E_prime_MPa": "Drained modulus (E')",
    "poissons_ratio": "Poisson's ratio (ν)",
    "end_bearing_ult_MPa": "End bearing, ultimate",
    "end_bearing_serv_MPa": "End bearing, serviceability",
    "shaft_adhesion_ult_kPa": "Shaft adhesion, ultimate",
    "anchor_bond_ult_kPa": "Anchor bond, ultimate",
    "active_wedge_angle_deg": "Active wedge angle",
}

# Mirrors frontend/src/components/rockParameterDisplay.js's
# HOEK_BROWN_FIELD_LABELS - rock-only, no soil equivalent. sti_MPa is
# deliberately left unlabelled here too (falls back to the raw key), same
# reason as the frontend: no citation in rock_typical_parameters.json for
# what it stands for, and guessing would be worse than the raw key.
_HOEK_BROWN_FIELD_LABELS = {
    "gamma_kNm3": "Unit weight (γ)",
    "min_ucs_MPa": "Minimum UCS for this class",
    "poissons_ratio": "Poisson's ratio (ν)",
    "hoek_brown_mi": "Hoek-Brown mᵢ (intact rock constant)",
    "Emass_MPa": "Rock mass modulus (Emass)",
    "c_star_kPa": "Equivalent cohesion (c*), at σ₃=500 kPa",
    "phi_star_deg": "Equivalent friction angle (φ*), at σ₃=500 kPa",
    "GSI": "Geological Strength Index (GSI)",
    "hoek_brown_s": "Hoek-Brown s",
    "mb": "Hoek-Brown mb",
}

# Mirrors boreholeReviewChecks.js's getRuleFindingLocation() switch - per
# rule-check "where" hints beyond the bare standard_section, for whichever
# checks have a more specific one in their `compared` payload.
def _rule_finding_location(finding):
    check = finding.get("check")
    compared = finding.get("compared") or {}
    if check in ("valid_uscs_symbol", "valid_weathering_symbol"):
        text = compared.get("stratum_text")
        return _truncate(text, 55) if text else None
    if check == "defect_description_format":
        return compared.get("text")
    if check == "valid_field_test_type":
        depth = compared.get("depth_from_m")
        return f"{depth:.2f} m depth" if depth is not None else None
    if check == "hb_context_disambiguation":
        return compared.get("blows") if compared.get("context") == "field_test_entry" else compared.get("text")
    if check == "rock_strength_band_consistency":
        return compared.get("source")
    return None


def _truncate(text, max_len):
    text = (text or "").strip()
    return f"{text[:max_len].rstrip()}…" if len(text) > max_len else text


_styles = getSampleStyleSheet()
_STYLE_TITLE = _styles["Title"]
_STYLE_H1 = _styles["Heading1"]
_STYLE_H2 = _styles["Heading2"]
_STYLE_BODY = _styles["BodyText"]
for _style in (_STYLE_TITLE, _STYLE_H1, _STYLE_H2):
    _style.fontName = "DejaVuSans-Bold"
_STYLE_BODY.fontName = "DejaVuSans"
_STYLE_SMALL = ParagraphStyle("Small", parent=_STYLE_BODY, fontName="DejaVuSans", fontSize=8.5, leading=11)
_STYLE_SMALL_MUTED = ParagraphStyle("SmallMuted", parent=_STYLE_SMALL, textColor=colors.HexColor("#52514e"))

_TABLE_STYLE = TableStyle(
    [
        ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7d6cd")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef4fc")),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVuSans-Bold"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
)


def _p(text, style=_STYLE_BODY):
    return Paragraph(text, style)


def _all_hole_ids(*result_dicts):
    ids = set()
    for result in result_dicts:
        if result:
            ids.update(result.get("holes", {}).keys())
    return sorted(ids)


def _review_log_section(story, hole_pages):
    for page in hole_pages:
        rule_findings = page.get("rule_findings") or []
        lab_findings = [f for f in rule_findings if f.get("check") in _LAB_CROSS_REF_CHECKS]
        rule_only_findings = [f for f in rule_findings if f.get("check") not in _LAB_CROSS_REF_CHECKS]
        judgment_findings = page.get("judgment_findings") or []

        story.append(_p(f"Sheet - page {page.get('page')}", _STYLE_H2))

        for title, findings in (
            ("Rule-checked findings", rule_only_findings),
            ("Lab cross-reference findings", lab_findings),
        ):
            if not findings:
                continue
            story.append(_p(title, ParagraphStyle("h3", parent=_STYLE_BODY, fontSize=10, fontName="DejaVuSans-Bold")))
            items = []
            for f in findings:
                where = _rule_finding_location(f)
                where_text = f" — {where}" if where else ""
                status = (f.get("status") or "").upper()
                items.append(
                    ListItem(
                        _p(
                            f"<b>[{status}]</b> {f.get('standard_section', '')}{where_text}: "
                            f"{f.get('explanation', '')}",
                            _STYLE_SMALL,
                        )
                    )
                )
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=12))
            story.append(Spacer(1, 4))

        if judgment_findings:
            story.append(
                _p("Judgment-based findings", ParagraphStyle("h3j", parent=_STYLE_BODY, fontSize=10, fontName="DejaVuSans-Bold"))
            )
            items = []
            for f in judgment_findings:
                category = _JUDGMENT_CATEGORY_LABELS.get(f.get("judgment_category"), f.get("judgment_category"))
                ref = f.get("stratum_reference")
                ref_text = f" — {ref}" if ref else ""
                items.append(
                    ListItem(
                        _p(
                            f"<b>{category}</b> ({f.get('confidence', '')} confidence){ref_text}: "
                            f"{f.get('finding', '')} <i>{f.get('uncertainty_note', '')}</i>",
                            _STYLE_SMALL,
                        )
                    )
                )
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=12))
            story.append(Spacer(1, 4))

        if not rule_findings and not judgment_findings:
            story.append(_p("No findings recorded for this sheet.", _STYLE_SMALL_MUTED))

        story.append(Spacer(1, 6))


def _fields_table(fields, labels):
    rows = [["Parameter", "Value"]]
    for key, field in fields.items():
        label = labels.get(key, key)
        value = field.get("value")
        unit = field.get("unit")
        value_text = "—" if value is None else str(value)
        if value is not None and unit and unit != "-":
            value_text = f"{value_text} {unit}"
        if field.get("source_note"):
            value_text += " (provisional)"
        rows.append([label, value_text])
    table = Table(rows, colWidths=[65 * mm, 90 * mm])
    table.setStyle(_TABLE_STYLE)
    return table


def _design_parameters_section(story, hole_pages, is_rock):
    for page in hole_pages:
        for sr in page.get("strata_results") or []:
            stratum = sr.get("stratum") or {}
            classification = sr.get("classification") or {}
            parameters = sr.get("parameters")

            depth = stratum.get("depth_from_m")
            depth_text = f"{depth:.2f} m" if depth is not None else "depth unknown"
            excerpt = _truncate(stratum.get("text"), 90)
            header = _p(f"<b>{depth_text}</b> — {excerpt}", ParagraphStyle("stratum_h", parent=_STYLE_BODY, fontSize=9.5))

            block = [header]
            if not classification.get("classified"):
                block.append(_p(f"Not classified: {classification.get('flag', '')}", _STYLE_SMALL_MUTED))
            else:
                block.append(_p(f"Classified as: {classification.get('classification_basis', '')}", _STYLE_SMALL))
                spacing_basis = classification.get("spacing_basis")
                if spacing_basis:
                    block.append(_p(f"Spacing: {spacing_basis}", _STYLE_SMALL))
                for warning in classification.get("warnings") or []:
                    block.append(_p(f"⚠ {warning}", ParagraphStyle("warn", parent=_STYLE_SMALL, textColor=colors.HexColor("#a15c00"))))

                if parameters:
                    if is_rock:
                        design_table = parameters.get("design_table") or {}
                        hb_table = parameters.get("hoek_brown_table") or {}
                        block.append(_p("Design Parameters", ParagraphStyle("dp", parent=_STYLE_SMALL, fontName="DejaVuSans-Bold")))
                        block.append(_fields_table(design_table.get("fields", {}), _DESIGN_TABLE_FIELD_LABELS))
                        block.append(_p("Rock Mass (Hoek-Brown)", ParagraphStyle("hb", parent=_STYLE_SMALL, fontName="DejaVuSans-Bold")))
                        block.append(_fields_table(hb_table.get("fields", {}), _HOEK_BROWN_FIELD_LABELS))
                    else:
                        block.append(_fields_table(parameters.get("fields", {}), _DESIGN_TABLE_FIELD_LABELS))

            story.append(KeepTogether(block))
            story.append(Spacer(1, 6))


def build_report_pdf(filename, review_log_result=None, soil_parameters_result=None, rock_parameters_result=None):
    """Renders a combined PDF from whichever of the three existing
    endpoints' responses are passed in (any/all may be None). Pure
    formatting - no parsing, no classification, no database. Returns the
    PDF as bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=f"Geotech report - {filename}",
    )

    story = [
        _p("Geotech Review Report", _STYLE_TITLE),
        _p(f"{filename} — generated {datetime.date.today().isoformat()}", _STYLE_BODY),
        Spacer(1, 10),
    ]

    hole_ids = _all_hole_ids(review_log_result, soil_parameters_result, rock_parameters_result)
    if not hole_ids:
        story.append(_p("No holes with a recognisable hole ID were found in this file.", _STYLE_BODY))

    for hole_id in hole_ids:
        story.append(_p(hole_id, _STYLE_H1))

        if review_log_result and hole_id in review_log_result.get("holes", {}):
            _review_log_section(story, review_log_result["holes"][hole_id])

        if soil_parameters_result and hole_id in soil_parameters_result.get("holes", {}):
            story.append(_p("Soil Parameters", _STYLE_H2))
            _design_parameters_section(story, soil_parameters_result["holes"][hole_id], is_rock=False)

        if rock_parameters_result and hole_id in rock_parameters_result.get("holes", {}):
            story.append(_p("Rock Parameters", _STYLE_H2))
            _design_parameters_section(story, rock_parameters_result["holes"][hole_id], is_rock=True)

        story.append(Spacer(1, 10))

    doc.build(story)
    return buffer.getvalue()
