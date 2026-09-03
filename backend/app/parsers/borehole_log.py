"""Parser for AECOM-template "Engineering Log" borehole / pavement dip /
test pit / cored borehole PDFs (reference/logs/).

This is a materially different document family from the Macquarie Geotech
lab reports the other parsers handle: it isn't one-title-per-page text with
labelled fields, it's a drafting-software (OpenGround) page layout with
narrow vertically-tiled columns (method, field tests/samples, RL, depth,
graphic log, classification symbol, material description) plus rotated
column headers that pdfplumber extracts as reversed character strings
(e.g. "DOHTEM" = "METHOD" backwards). Relying on extract_text()'s reading
order is not reliable here - it's noticeably column-major rather than
row-major - so this module works from extract_words() coordinates
directly: bucket words into columns by x-position, cluster into visual
rows by y-position, then read each column's own row order.

Per CLAUDE.md, borehole logs are "not 100% automatable - the realistic
goal is reliable extraction of depth/strata/SPT/sample-ID rows, with
anything unparseable flagged for manual entry." This parser follows that:
header metadata and SPT/sample entries carry their own explicit depth
values from the report text, but material-description depths are
interpolated from the depth-axis ticks and paragraph boundaries are
inferred from line-spacing gaps - both are estimates, not printed values,
and are marked as such for the review step.
"""

import re
import statistics

import pdfplumber

PAGE_TYPE_LOG = "log"
PAGE_TYPE_PHOTO_REPORT = "photo_report"
PAGE_TYPE_DESCRIPTION_SHEET = "description_sheet"
PAGE_TYPE_UNRECOGNIZED = "unrecognized"

_LOG_HEADER_RE = re.compile(
    r"Engineering Log (Cored Borehole|Borehole|Pavement Dip|Test Pit)\s+No\.\s*([A-Za-z0-9_\-]+)"
)
_PHOTO_REPORT_RE = re.compile(r"PHOTO REPORT ID NO\.", re.IGNORECASE)

# Columns are identified by horizontal position (points from the page's
# left edge), calibrated against the AECOM template samples in
# reference/logs/. All files sampled (PRUP/TfNSW, WSM/Sydney Water,
# Heathcote, Alex Canal) share this layout.
COLUMN_RANGES = {
    "field_tests": (60, 110),
    "rl": (122, 145),
    "depth": (145, 165),
    "description": (198, 429),
    "notes": (429, 600),
}

_ROW_CLUSTER_TOL = 3
_TICK_VALUE_RE = re.compile(r"^\d+(\.\d+)?$")
_ENTRY_LABEL_RE = re.compile(r"^(SPT|D|ES|U):\s*([\d.]+)\s*-\s*([\d.]+)\s*m")
_SPT_DETAIL_RE = re.compile(r"^(.*?)\s*N\s*=\s*(\S+)\s*$")
_PID_RE = re.compile(r"PID\s*=\s*([\d.]+)\s*PPM", re.IGNORECASE)
_IS50_RE = re.compile(r"Is\s*\(?50\)?\s*([DA])\s*=\s*([\d.]+)\s*MPa", re.IGNORECASE)
_UCS_RE = re.compile(r"UCS\s*=\s*([\d.]+)\s*MPa", re.IGNORECASE)
# DCP (Dynamic Cone Penetration) readings print as bare blow counts under
# the "(BLOWS DCP PER 100mm)" column caption - never as the word "DCP"
# next to a value, same pattern as SPT-N. A single blow exceeding the
# 100mm increment prints as "blows/mm" (e.g. "22/80"), the DCP equivalent
# of SPT's "10/50mm HB N=R" refusal notation. See
# reference/borehole-log-standard.md Part 1 item 5 for how this was
# originally missed (searched for the label instead of the data shape).
_DCP_PARTIAL_RE = re.compile(r"^(\d+)/(\d+)$")
_DCP_FULL_RE = re.compile(r"^\d+$")

# The DEPTH column's tick-value words sit at a different x-position on
# Cored Borehole and Test Pit pages than on Borehole/Pavement Dip pages -
# diagnosed in reference/borehole-log-standard.md §2.2/§2.4. Verified
# directly against real examples (Heathcote.pdf p2 for Cored Borehole,
# PRUP_TP Logs.pdf p1 for Test Pit) rather than assumed from the caption
# position alone.
#
# "Borehole" gets its own narrowed entry rather than falling through to
# COLUMN_RANGES["depth"] (145-165): on template variants that print an RL
# (Reduced Level) column next to DEPTH - PRUP_BH/PRUP_HA's every page, and
# a handful of Chowder Bay/Heathcote pages - RL's tick-like values (e.g.
# "311.0", "310.0", ... one whole metre apart, same as real depth ticks)
# render at x0=146.3, just 1pt outside COLUMN_RANGES["rl"]'s declared
# upper bound (145) and squarely inside the old depth range's lower bound
# (145) - so they got vacuumed up as depth ticks alongside the genuine
# ones at x0=164.3, corrupting the linear fit the same way the Cored
# Borehole "MC 450" bug did (a handful of wild outliers among the real
# ticks). Confirmed on PRUP_BH01 page 1: real depths 0-8m calibrated out
# to bogus 154-160m instead, silently breaking depth-sort order for that
# sheet - only surfaced once the Design Parameters UI's depth-sorted merge
# made the wrong ordering visible.
#
# Each log_type maps to a TUPLE OF (lo, hi) sub-ranges, not one - because
# "Borehole" genuinely needs two disjoint ones. A different Borehole
# template variant (Alex Canal, most of Heathcote/WSM - no RL column at
# all) prints its genuine ticks right-aligned, so a two-digit depth
# ("10.0"-"20.0"+) sits ~2.5-3pt further left (x0=144.5, one specific
# value - "11.0" - lands at 144.8, a font-kerning quirk, not a separate
# column) than a one-digit depth (x0=147.3). A single (147, 165) window
# excludes that left cluster entirely, so any sheet whose visible ticks
# are ALL two-digit (a continuation sheet covering, say, 11-20m, with the
# 0-10m sheet's single-digit ticks on the previous page) gets zero usable
# ticks and comes back uncalibrated - confirmed on 7 real pages (Alex
# Canal p11/15/34, Heathcote p43/52/60, WSM p12).
#
# The obvious fix - just lower (147,165)'s lower bound to ~144 - was
# checked and rejected: 144.5 sits only 1.8pt below the RL contaminant at
# 146.3, and a single contiguous range can't include one without the
# other. Measured directly: doing that would reintroduce RL contamination
# on 46 real Borehole pages across PRUP_BH/PRUP_HA/Chowder Bay HA*/
# Heathcote DTP* - each with 4-8 RL values simultaneously in-window, far
# past what _MAX_OUTLIER_REJECTIONS can trim, breaking pages that
# currently calibrate correctly. Two disjoint ranges - (144.0, 145.5) for
# the two-digit cluster, (147, 165) for everything already covered -
# capture the missing ticks while leaving the 0.8pt gap around 146.3
# (145.5 to 147.0) exactly where it needs to be to keep excluding RL.
_DEPTH_COLUMN_RANGES_BY_TYPE = {
    "Cored Borehole": ((125, 141),),
    "Test Pit": ((183, 197),),
    "Borehole": ((144.0, 145.5), (147, 165)),
}


def _depth_tick_ranges(log_type):
    return _DEPTH_COLUMN_RANGES_BY_TYPE.get(log_type, (COLUMN_RANGES["depth"],))

# Cored Borehole pages have no MOISTURE CONDITION / CONSISTENCY-RELATIVE
# DENSITY columns at all - they use WEATHERING/TCR/INFERRED STRENGTH/DEFECT
# SPACING instead, a different layout entirely (rock is a later phase, not
# touched here). These two columns only exist on soil pages.
_SOIL_LOG_TYPES = {"Borehole", "Pavement Dip", "Test Pit"}

# Calibrated directly against real words (both header captions and actual
# printed codes like "VS"/"MD"/"St"), not assumed from the caption alone:
# moisture codes ("D", "w < PL", ...) sit at x0 ~428-438, consistency/
# relative-density codes ("VS", "VL", "MD", "St", ...) at x0 ~446-455, on
# both Borehole (Alex Canal.pdf) and Test Pit (PRUP_TP Logs.pdf) samples.
# Pavement Dip's columns sit ~17pt further left - verified on two
# independent Pavement Dip files (PRUP_AC, PRUP_CC), not assumed from one.
_DEFAULT_CONSISTENCY_COLUMNS = {"moisture": (427, 442), "consistency_relative_density": (442, 461)}
_CONSISTENCY_COLUMN_RANGES_BY_TYPE = {
    "Pavement Dip": {"moisture": (410, 431), "consistency_relative_density": (431, 450)},
}

# The MATERIAL DESCRIPTION column sits at a different x-range on Cored
# Borehole pages than the shared soil range (COLUMN_RANGES["description"])
# handles: real text starts as low as x0~154-162 (e.g. "SANDSTONE:" itself
# prints at x0=162, below the soil range's 198 lower bound - the rock-type
# label was being dropped entirely), and the soil range's upper bound
# (429) reaches past the WEATHERING column and into ADDITIONAL
# OBSERVATIONS, pulling weathering codes and the formation name into the
# description text instead. Confirmed systematic across every Cored
# Borehole page in the corpus (PRUP_BH01, Heathcote, WSM, Chowder Bay),
# not assumed from one file - see the corpus-wide x0 histogram this was
# calibrated from.
_DESCRIPTION_COLUMN_RANGES_BY_TYPE = {
    "Cored Borehole": (150, 299),
}

# WEATHERING column codes (XW/HW/MW/SW/FR/RS/DW, or a printed transition
# like "MW to FR") sit at x0~301-318 - confirmed corpus-wide. The exact
# position drifts a little by project (PRUP~301-313, Heathcote/WSM~306-
# 317), but a clean, empty gap at x0=300 separates it from MATERIAL
# DESCRIPTION on one side, and another gap after ~318 separates it from
# the TCR/(SCR)/[RQD] triple (~321+) on the other, in every sampled file.
# Only meaningful on Cored Borehole pages - soil pages have no weathering
# concept (they use CONSISTENCY/RELATIVE DENSITY instead).
_WEATHERING_COLUMN_RANGE = (300, 318)

# ADDITIONAL OBSERVATIONS (rock defect descriptions, and the once-per-run
# formation name printed as that column's first line) sits at x0~417-428
# on Cored Borehole pages. The shared soil "notes" range's lower bound
# (429) was clipping the leading digit off the overwhelming majority
# (2866 of 2882 sampled) of defect-description depth prefixes, and
# dropping the formation name line entirely - both "BULGO SANDSTONE" and
# "HAWKESBURY SANDSTONE" start below 429 too.
_NOTES_COLUMN_RANGES_BY_TYPE = {
    "Cored Borehole": (410, 600),
}

# Every genuine defect-description line starts with its depth ("3.06 m:"
# or "3.10-3.18 m:") - the formation name line never does, and (per real
# data) only ever appears as the very first row of the ADDITIONAL
# OBSERVATIONS column, on whichever sheet starts the rock run. It does
# not repeat on that hole's later continuation sheets. Captures the depth
# range and the rest of the line so it can also drive
# _extract_defect_entries, not just the formation-name boolean check.
_DEFECT_DEPTH_PREFIX_RE = re.compile(
    r"^(?P<from>\d+(?:\.\d+)?)(?:-(?P<to>\d+(?:\.\d+)?))?\s*m:\s*(?P<rest>.*)$"
)

# The defect type is always the first token of the rest-of-line text
# ("P, 20°, RF, ..." / bare "DB" with nothing following) - per §3.15 of
# the standard (VALID_DEFECT_TYPES in rules.py). Matched loosely here
# (parsing, not validating) so an unrecognised type still comes through
# as a real value rather than None - see rock_parameters/defects.py for
# how natural-vs-artifact-vs-unrecognised is decided from it.
_DEFECT_TYPE_TOKEN_RE = re.compile(r"^([A-Za-z]{1,2})\b")


def classify_log_page(text: str) -> str:
    if _LOG_HEADER_RE.search(text):
        return PAGE_TYPE_LOG
    if _PHOTO_REPORT_RE.search(text):
        return PAGE_TYPE_PHOTO_REPORT
    if "logging description sheet" in text.lower() or "description sheets" in text.lower():
        return PAGE_TYPE_DESCRIPTION_SHEET
    return PAGE_TYPE_UNRECOGNIZED


def _search(pattern, text, flags=0):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def parse_log_header(text: str) -> dict:
    header = {}
    m = _LOG_HEADER_RE.search(text)
    header["log_type"] = m.group(1) if m else None
    header["hole_id"] = m.group(2) if m else None

    m = re.search(r"Sheet\s+(\d+)\s+of\s+(\d+)", text)
    header["sheet"] = int(m.group(1)) if m else None
    header["sheet_total"] = int(m.group(2)) if m else None

    header["client"] = _search(r"Client:\s*([^\n]+?)\s+Project No:", text)
    header["project_no"] = _search(r"Project No:\s*([A-Za-z0-9]+)", text)
    header["project"] = _search(r"Project:\s*([^\n]+?)\s+Logged by:", text)
    header["logged_by"] = _search(r"Logged by:\s*([^\n]+?)\s+Checked by:", text)
    header["checked_by"] = _search(
        r"Checked by:\s*([^\n]+?)\s*(?=Location:|Driller:|Operator:|\n|$)", text
    )
    header["location"] = _search(r"Location:\s*([^\n]+?)\s+Start Date:", text)
    header["start_date"] = _search(r"Start Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})", text)
    header["end_date"] = _search(r"End Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})", text)
    header["driller"] = _search(r"Driller:\s*([^\n]+?)\s+Hole Diameter:", text)
    header["operator"] = _search(r"Operator:\s*([^\n]+?)\s+Dimensions:", text)
    header["hole_diameter"] = _search(r"Hole Diameter:\s*([^\n]+?)\s+Easting:", text)
    header["easting"] = _search(r"Easting:\s*([\d.]+)", text)
    header["northing"] = _search(r"Northing:\s*([\d.]+)", text)
    header["rl_m"] = _search(r"\bRL:\s*([\d.]+)\s*m", text)
    header["total_depth_m"] = _search(r"Total Depth:\s*([\d.]+)\s*m", text)
    header["surface"] = _search(r"Surface:\s*([^\n]+?)(?:\n|Hor\.|$)", text)
    header["datum"] = _search(r"Hor\.?\s*Datum:\s*([A-Za-z0-9\-]+)", text)

    header["continued_from_previous"] = "continued from previous" in text.lower()
    header["continued_to_next"] = "continued on next" in text.lower()
    return header


def _cluster_rows(words):
    """Group words into visual rows by y-position (top), tolerant of the
    few points of jitter between characters printed on the same line."""
    rows = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        for row in rows:
            if abs(row["top"] - w["top"]) <= _ROW_CLUSTER_TOL:
                row["words"].append(w)
                break
        else:
            rows.append({"top": w["top"], "words": [w]})
    rows.sort(key=lambda r: r["top"])
    for row in rows:
        row["words"].sort(key=lambda w: w["x0"])
        row["text"] = " ".join(w["text"] for w in row["words"])
    return rows


def _column_words(words, key):
    lo, hi = COLUMN_RANGES[key]
    return [w for w in words if lo <= w["x0"] <= hi]


# --- _depth_calibration's outlier/validation thresholds ---
#
# Two real bugs so far both had the same shape: a stray non-depth numeric
# token (a drill rig model number; an adjacent RL column's values) landed
# inside the per-log-type x0 window and got fitted as if it were a genuine
# tick, badly distorting the line. Each was only caught because a symptom
# happened to be visible (garbage depths sorting to the wrong place) - the
# window itself has no way to notice contamination, and narrowing it is a
# per-incident patch, not a structural fix. These thresholds are the
# structural fix: they don't care which column the stray point came from
# or what log_type the page is, so Pavement Dip and Test Pit (never
# individually audited, unlike Cored Borehole/Borehole) get the same
# protection without needing their own incident first.
#
# The thresholds themselves come from measuring both failure modes
# directly against the reference corpus, not from guessing a number that
# feels safe:
#   - Every genuinely clean page's fit (all 408 log pages, all 4 types,
#     post both column-range fixes): R^2 >= 0.9999999999999755, max
#     |residual| <= 5.8e-7 m. These are vector-drawn PDF ticks - a clean
#     fit isn't "very good," it's exact to float precision, because the
#     axis really is perfectly linear.
#   - Re-running the historical PRUP_BH01 p1 RL-contamination case with
#     its pre-fix (wider) window: R^2 = 0.0034, max |residual| = 169 m.
#   - _MIN_R2 (0.999) and _MAX_RESIDUAL_M (0.5) both sit many orders of
#     magnitude from the clean noise floor and comfortably below the
#     contaminated case - there's no tuning-to-two-examples risk here,
#     the gap is enormous in both directions.
_MIN_R2 = 0.999
_MAX_RESIDUAL_M = 0.5
# Small and deliberate: this rejects a straggler or two that slips past a
# reasonably-scoped column window, it does not rescue a badly-scoped one.
# If more points than this are bad, the window (or the page) has a
# structural problem outlier-trimming shouldn't paper over - fail closed
# (return None -> the existing, already-correct "uncalibrated" fallback)
# rather than silently keep deleting data until something fits.
_MAX_OUTLIER_REJECTIONS = 2
# Slack beyond the header's own printed Total Depth. Not a small
# rounding allowance: the printed depth-axis GRID is a fixed template
# feature that isn't clipped to where the hole actually terminates, so on
# a hole's last (or a continuation) sheet the axis legitimately keeps
# printing ticks past total_depth_m - measured directly across the
# reference corpus, the worst real case overshoots by 7.9 m (Heathcote
# DBH01: total_depth_m=1.8, axis ticks run to 8.0). 15.0 clears that with
# real margin while staying two orders of magnitude below what actual
# contamination produces (the historical PRUP_BH01 case reached 160 m) -
# this check exists to catch "wildly implausible," not to be a tight
# bound, since R^2/residual rejection above already handles small-scale
# contamination whenever there are enough points to compute them; this is
# specifically the backstop for the <=2-tick case where residuals can't
# help at all (any two points fit a perfect line).
_TOTAL_DEPTH_MARGIN_M = 15.0


def _ols_fit(ticks):
    """Plain least-squares fit of depth (m) against page-y (top), plus the
    diagnostics (R^2, per-point residuals) _depth_calibration uses to
    decide whether to trust it. Returns None if the ticks are degenerate
    (all at the same top)."""
    n = len(ticks)
    mean_x = sum(t for t, _ in ticks) / n
    mean_y = sum(v for _, v in ticks) / n
    num = sum((t - mean_x) * (v - mean_y) for t, v in ticks)
    den = sum((t - mean_x) ** 2 for t, _ in ticks)
    if den == 0:
        return None
    slope = num / den
    intercept = mean_y - slope * mean_x
    residuals = [v - (slope * t + intercept) for t, v in ticks]
    ss_res = sum(r * r for r in residuals)
    ss_tot = sum((v - mean_y) ** 2 for _, v in ticks)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return {"slope": slope, "intercept": intercept, "residuals": residuals, "r2": r2}


def _depth_calibration(words, log_type, total_depth_m=None):
    """Fits a linear map from page-y (top) to borehole depth (m) using the
    depth-axis tick labels (0.0, 1.0, 2.0, ...). Falls back to None if
    fewer than two usable ticks are found, since a page can't be
    calibrated off a single point - or if no fit can be made to pass the
    validation below, since a page that can't be trusted should come back
    uncalibrated (depth_from_m: None throughout, already the existing,
    correct behaviour for "not enough ticks") rather than silently wrong.

    The DEPTH column sits at a different x-position per log_type - see
    _DEPTH_COLUMN_RANGES_BY_TYPE - which is a coarse first-pass filter,
    not a guarantee: it's exactly how both known contamination bugs got
    in (a drill rig model number on Cored Borehole pages; an adjacent RL
    column on Borehole pages), each only caught because its symptom
    happened to be visible. What follows is a second, page-type-agnostic
    layer that doesn't depend on knowing which column or page type is at
    fault:

    1. Input side - iterative outlier rejection. Fit the ticks collected
       so far; if the fit's R^2 or worst residual falls outside
       _MIN_R2/_MAX_RESIDUAL_M, drop the single worst-residual point and
       refit, up to _MAX_OUTLIER_REJECTIONS times.
    2. Output side - sanity-check the accepted fit itself: depth must
       increase down the page (positive slope), and every included
       tick's value must be non-decreasing in top order and within
       [-0.5, total_depth_m + _TOTAL_DEPTH_MARGIN_M] when the header's
       own printed Total Depth is available (it is on every page in the
       reference corpus). This catches what residuals alone can't: with
       only two ticks, any two points fit a perfect line (R^2=1,
       residual=0) whether or not either one is genuine - total_depth_m
       and monotonicity are the only signal left in that case.
    """
    ranges = _depth_tick_ranges(log_type)
    ticks = []
    for w in words:
        if (
            w["top"] > 200
            and any(lo <= w["x0"] <= hi for lo, hi in ranges)
            and _TICK_VALUE_RE.match(w["text"])
        ):
            ticks.append((w["top"], float(w["text"])))

    depth_bound = None
    if total_depth_m is not None:
        try:
            depth_bound = float(total_depth_m) + _TOTAL_DEPTH_MARGIN_M
        except ValueError:
            depth_bound = None

    for _ in range(_MAX_OUTLIER_REJECTIONS + 1):
        if len(ticks) < 2:
            return None
        fit = _ols_fit(ticks)
        if fit is None:
            return None

        ticks_by_top = sorted(ticks)
        monotonic = all(
            ticks_by_top[i][1] <= ticks_by_top[i + 1][1] for i in range(len(ticks_by_top) - 1)
        )
        in_bounds = depth_bound is None or all(-0.5 <= v <= depth_bound for _, v in ticks)

        if (
            fit["r2"] >= _MIN_R2
            and max(abs(r) for r in fit["residuals"]) <= _MAX_RESIDUAL_M
            and fit["slope"] > 0
            and monotonic
            and in_bounds
        ):
            slope, intercept = fit["slope"], fit["intercept"]
            return lambda top: round(slope * top + intercept, 2)

        worst_idx = max(range(len(ticks)), key=lambda i: abs(fit["residuals"][i]))
        ticks.pop(worst_idx)

    return None


def _paragraphs_by_gap(rows):
    """Splits a column's rows into paragraphs wherever the vertical gap to
    the next row is notably larger than the typical single-line gap - a
    blank line between strata descriptions prints as roughly double the
    spacing within one. This is a heuristic, not a printed boundary."""
    if not rows:
        return []
    gaps = [rows[i]["top"] - rows[i - 1]["top"] for i in range(1, len(rows))]
    normal_gap = statistics.median(gaps) if gaps else 7
    threshold = max(10, normal_gap * 1.5)

    paragraphs = [[rows[0]]]
    for i in range(1, len(rows)):
        gap = rows[i]["top"] - rows[i - 1]["top"]
        if gap > threshold:
            paragraphs.append([])
        paragraphs[-1].append(rows[i])
    return paragraphs


def _extract_strata(words, depth_of, log_type=None):
    lo, hi = _DESCRIPTION_COLUMN_RANGES_BY_TYPE.get(log_type, COLUMN_RANGES["description"])
    rows = _cluster_rows([w for w in words if lo <= w["x0"] <= hi])
    # Drop the printed column caption and any header/footer text that
    # shares the description column's x-range but sits above/below the
    # actual log body.
    rows = [r for r in rows if not r["text"].startswith("MATERIAL DESCRIPTION")]
    rows = [r for r in rows if "Log continued" not in r["text"]]
    rows = [r for r in rows if "logging description" not in r["text"].lower()]
    # On Cored Borehole pages, the widened range that reaches "SANDSTONE:"
    # (see _DESCRIPTION_COLUMN_RANGES_BY_TYPE) also reaches the start of
    # the page footer sentence ("...log should be read in conjunction
    # with AECOM...") - confirmed the only fragment that lands in this
    # range, corpus-wide, is "log should be read in conjunction with".
    rows = [r for r in rows if "conjunction with" not in r["text"]]
    rows = [r for r in rows if r["top"] > 200]

    strata = []
    for para in _paragraphs_by_gap(rows):
        text = " ".join(r["text"] for r in para)
        entry = {"text": text, "depth_from_m": None, "depth_estimated": True}
        if depth_of is not None:
            entry["depth_from_m"] = depth_of(para[0]["top"])
        strata.append(entry)
    return strata


def _extract_field_test_entries(words):
    rows = _cluster_rows(_column_words(words, "field_tests"))
    entries = []
    current = None
    for row in rows:
        m = _ENTRY_LABEL_RE.match(row["text"])
        if m:
            if current is not None:
                entries.append(current)
            current = {
                "type": m.group(1),
                "depth_from_m": float(m.group(2)),
                "depth_to_m": float(m.group(3)),
                "detail": [],
            }
        elif current is not None:
            current["detail"].append(row["text"])
    if current is not None:
        entries.append(current)

    for entry in entries:
        detail_text = " ".join(entry.pop("detail"))
        if entry["type"] == "SPT":
            m = _SPT_DETAIL_RE.match(detail_text)
            if m:
                entry["blows"] = m.group(1).strip() or None
                entry["n_value"] = m.group(2)
            else:
                entry["blows"] = detail_text or None
                entry["n_value"] = None
        else:
            pid = _PID_RE.search(detail_text)
            entry["pid_ppm"] = float(pid.group(1)) if pid else None
    return entries


def _extract_defect_entries(words, log_type):
    """Structured, depth-tagged rock-defect records from the ADDITIONAL
    OBSERVATIONS column - the same label-driven state machine
    _extract_field_test_entries uses (a depth-prefixed row starts a new
    entry; a row without one continues the previous entry's wrapped
    text), keyed on _DEFECT_DEPTH_PREFIX_RE instead of _ENTRY_LABEL_RE.
    Real data confirms the same wrapping problem SPT/D/ES/U already
    handle: ~5% of defect lines split across two printed rows (e.g.
    "...40-60 mm" / "spacing, x 3" - one defect, not two). A row that
    isn't depth-prefixed and doesn't follow an open entry (the formation
    name, or a rare free-text remark like a water-loss note) is silently
    dropped here rather than guessed into a defect - same as the
    formation-name handling in _extract_notes.

    Every entry is kept regardless of its type - including drilling
    artifacts (MB/DB/DL/HB) and anything unrecognised - so nothing is
    silently lost; deciding which types count toward defect spacing is
    rock_parameters/defects.py's job, not this function's."""
    if log_type != "Cored Borehole":
        return []
    lo, hi = _NOTES_COLUMN_RANGES_BY_TYPE.get(log_type, COLUMN_RANGES["notes"])
    note_words = [w for w in words if lo <= w["x0"] <= hi]
    rows = _cluster_rows(note_words)
    rows = [r for r in rows if r["top"] > 200]
    rows = [r for r in rows if "description sheets" not in r["text"].lower()]
    rows.sort(key=lambda r: r["top"])

    entries = []
    current = None
    for row in rows:
        m = _DEFECT_DEPTH_PREFIX_RE.match(row["text"])
        if m:
            if current is not None:
                entries.append(current)
            depth_from = float(m.group("from"))
            current = {
                "depth_from_m": depth_from,
                "depth_to_m": float(m.group("to")) if m.group("to") else depth_from,
                "text": m.group("rest"),
            }
        elif current is not None:
            current["text"] = f"{current['text']} {row['text']}"
    if current is not None:
        entries.append(current)

    for entry in entries:
        type_m = _DEFECT_TYPE_TOKEN_RE.match(entry["text"])
        entry["type"] = type_m.group(1).upper() if type_m else None
    return entries


def _extract_dcp_readings(words, depth_of):
    """DCP readings have no "LABEL:" prefix (unlike SPT/D/ES/U), so they're
    a separate scan over the field-tests column rather than a branch of
    _extract_field_test_entries's label-driven state machine. Depth comes
    from the row's own y-position via the calibrated depth axis, the same
    technique _extract_point_load_readings uses, since DCP rows don't
    print an explicit depth range of their own."""
    rows = _cluster_rows(_column_words(words, "field_tests"))
    readings = []
    for row in rows:
        if row["top"] <= 200:
            continue
        text = row["text"].strip()
        depth_m = depth_of(row["top"]) if depth_of else None

        m = _DCP_PARTIAL_RE.match(text)
        if m:
            readings.append(
                {
                    "blows": int(m.group(1)),
                    "penetration_mm": int(m.group(2)),
                    "partial_penetration": True,
                    "depth_m": depth_m,
                }
            )
            continue

        if _DCP_FULL_RE.match(text):
            readings.append(
                {
                    "blows": int(text),
                    "penetration_mm": 100,
                    "partial_penetration": False,
                    "depth_m": depth_m,
                }
            )
    return readings


def _extract_consistency_readings(words, depth_of, log_type):
    """Moisture-condition and consistency/relative-density codes (e.g.
    "D", "St", "MD") print in their own narrow columns, distinct from the
    material description - previously both fell into the generic notes
    catch-all unlabelled and with no stratum association at all. Returns
    raw (text, depth) readings per column; attaching a reading to the
    stratum it describes is _attach_readings_to_strata's job, since
    depth_of() gives a continuous depth estimate, not a stratum boundary.
    Only called for soil log types - see _SOIL_LOG_TYPES."""
    ranges = _CONSISTENCY_COLUMN_RANGES_BY_TYPE.get(log_type, _DEFAULT_CONSISTENCY_COLUMNS)
    readings = {}
    for key, (lo, hi) in ranges.items():
        rows = _cluster_rows([w for w in words if lo <= w["x0"] <= hi])
        readings[key] = []
        for row in rows:
            if row["top"] <= 200:
                continue
            text = row["text"].strip()
            if not text:
                continue
            readings[key].append({"text": text, "depth_m": depth_of(row["top"]) if depth_of else None})
    return readings


def _extract_weathering_readings(words, depth_of):
    """WEATHERING column codes (e.g. "XW", or a printed transition like
    "MW to FR") - see _WEATHERING_COLUMN_RANGE. Only called for Cored
    Borehole pages. The page footer's "...AECOM soil and rock logging..."
    sentence has one word ("AECOM") that lands in this x-range too -
    filtered out by content, the same defensive style already used for
    "Log continued"/"logging description" elsewhere in this module."""
    lo, hi = _WEATHERING_COLUMN_RANGE
    rows = _cluster_rows([w for w in words if lo <= w["x0"] <= hi])
    readings = []
    for row in rows:
        if row["top"] <= 200:
            continue
        text = row["text"].strip()
        if not text or "AECOM" in text:
            continue
        readings.append({"text": text, "depth_m": depth_of(row["top"]) if depth_of else None})
    return readings


def _attach_readings_to_strata(strata, readings, field_name):
    """Attaches each reading to the stratum whose depth range contains it.
    A stratum is treated as spanning from its own depth to the next
    stratum's depth - one consistency/moisture code describes the whole
    layer it's printed within, not just the specific row it happens to
    print on. A reading with no depth estimate (calibration failed) is
    dropped rather than guessed onto a stratum."""
    for stratum in strata:
        stratum[field_name] = []
    if not strata:
        return
    for reading in readings:
        depth_m = reading["depth_m"]
        if depth_m is None:
            continue
        owner = None
        for stratum in strata:
            if stratum["depth_from_m"] is not None and stratum["depth_from_m"] <= depth_m:
                owner = stratum
            else:
                break
        if owner is not None:
            owner[field_name].append(reading["text"])


def _extract_point_load_readings(rows):
    """"Is(50) D=1.1 MPa" (etc.) wraps across two or three of this narrow
    column's visual rows ("Is(50)" / "D=1.1 MPa" printed on separate
    lines), so each candidate row is matched against a short window of
    itself plus the next couple of rows rather than against its own text
    alone."""
    readings = []
    for i, row in enumerate(rows):
        if "Is(50)" not in row["text"] and "Is₍₅₀₎" not in row["text"]:
            continue
        window_text = " ".join(r["text"] for r in rows[i : i + 3])
        for m in _IS50_RE.finditer(window_text):
            readings.append(
                {
                    "type": f"point_load_is50_{m.group(1).lower()}",
                    "value_mpa": float(m.group(2)),
                    "depth_m": row["depth_m"],
                }
            )
    for row in rows:
        for m in _UCS_RE.finditer(row["text"]):
            readings.append({"type": "ucs", "value_mpa": float(m.group(1)), "depth_m": row["depth_m"]})
    return readings


def _extract_notes(words, depth_of, log_type=None):
    # Point load / UCS readings on rock-core pages print in the same field
    # tests column soil samples use (SPT: etc), not the geological-origin
    # remarks column - so both are scanned for either kind of content.
    field_test_rows = _cluster_rows(_column_words(words, "field_tests"))
    notes_lo, notes_hi = _NOTES_COLUMN_RANGES_BY_TYPE.get(log_type, COLUMN_RANGES["notes"])
    note_words = [w for w in words if notes_lo <= w["x0"] <= notes_hi]
    if log_type in _SOIL_LOG_TYPES:
        # Moisture/consistency codes are extracted separately (see
        # _extract_consistency_readings) and attached to their owning
        # stratum - excluded here at the word level (not by dropping whole
        # rows) so they stop showing up as unlabelled remarks fragments
        # without risking dropping a genuine note that happens to share a
        # row with one. Cored Borehole is never in _SOIL_LOG_TYPES, so its
        # existing point-load/UCS extraction (which also runs through this
        # function) is completely unaffected.
        cols = _CONSISTENCY_COLUMN_RANGES_BY_TYPE.get(log_type, _DEFAULT_CONSISTENCY_COLUMNS)
        lo, hi = cols["moisture"][0], cols["consistency_relative_density"][1]
        note_words = [w for w in note_words if not (lo <= w["x0"] <= hi)]
    note_rows = _cluster_rows(note_words)
    for row in field_test_rows + note_rows:
        row["depth_m"] = depth_of(row["top"]) if depth_of else None

    combined_rows = [r for r in field_test_rows + note_rows if r["top"] > 200]
    combined_rows.sort(key=lambda r: r["top"])
    readings = _extract_point_load_readings(combined_rows)

    note_rows = [r for r in note_rows if r["top"] > 200]
    # Widening the Cored Borehole notes range to reach real defect text
    # (see _NOTES_COLUMN_RANGES_BY_TYPE) also reaches the tail end of the
    # page footer ("...in conjunction with AECOM soil and rock logging
    # description sheets.") - confirmed the only fragment that lands
    # in-range, corpus-wide, is "description sheets." itself.
    note_rows = [r for r in note_rows if "description sheets" not in r["text"].lower()]

    # The formation name (e.g. "BULGO SANDSTONE") prints as the first line
    # of this column on whichever sheet starts a rock run, and doesn't
    # repeat on that hole's later continuation sheets - identified here as
    # "the first row that isn't a depth-prefixed defect description",
    # rather than by position relative to other columns, since real data
    # shows it isn't reliably on its own separate visual row from the
    # first defect line.
    rock_formation = None
    if log_type == "Cored Borehole" and note_rows:
        note_rows.sort(key=lambda r: r["top"])
        first = note_rows[0]
        if not _DEFECT_DEPTH_PREFIX_RE.match(first["text"]):
            rock_formation = first["text"]
            note_rows = note_rows[1:]

    remarks = [
        r["text"] for r in note_rows if not _IS50_RE.search(r["text"]) and not _UCS_RE.search(r["text"])
    ]
    return readings, remarks, rock_formation


def parse_log_page(page) -> dict:
    text = page.extract_text() or ""
    page_type = classify_log_page(text)

    result = {"page_type": page_type}
    if page_type != PAGE_TYPE_LOG:
        return result

    words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
    header = parse_log_header(text)
    depth_of = _depth_calibration(words, header["log_type"], header.get("total_depth_m"))

    result["header"] = header
    result["depth_axis_calibrated"] = depth_of is not None
    result["strata"] = _extract_strata(words, depth_of, header["log_type"])
    result["field_test_entries"] = _extract_field_test_entries(words)
    result["dcp_readings"] = _extract_dcp_readings(words, depth_of)
    result["defect_entries"] = _extract_defect_entries(words, header["log_type"])
    readings, remarks, rock_formation = _extract_notes(words, depth_of, header["log_type"])
    result["point_load_ucs_readings"] = readings
    result["notes"] = remarks
    result["rock_formation"] = rock_formation

    if header["log_type"] in _SOIL_LOG_TYPES:
        consistency_readings = _extract_consistency_readings(words, depth_of, header["log_type"])
        _attach_readings_to_strata(
            result["strata"], consistency_readings["consistency_relative_density"], "consistency_relative_density"
        )
        _attach_readings_to_strata(result["strata"], consistency_readings["moisture"], "moisture_condition")
        for stratum in result["strata"]:
            stratum["weathering"] = []
    elif header["log_type"] == "Cored Borehole":
        weathering_readings = _extract_weathering_readings(words, depth_of)
        _attach_readings_to_strata(result["strata"], weathering_readings, "weathering")
        for stratum in result["strata"]:
            stratum["consistency_relative_density"] = []
            stratum["moisture_condition"] = []
    else:
        # Unrecognised log type - every field is still present so
        # downstream code (soil_parameters) never has to special-case a
        # missing key.
        for stratum in result["strata"]:
            stratum["consistency_relative_density"] = []
            stratum["moisture_condition"] = []
            stratum["weathering"] = []
    return result


def process_log_pdf(file) -> dict:
    """Parses every page of a borehole/pavement-dip/test-pit log PDF.

    Unlike the lab-report dispatch (one page = one independent sample),
    log pages are a hole's SHEET 1 OF N, so pages are grouped by hole_id
    for the caller's convenience in addition to the flat per-page list."""
    pages = []
    with pdfplumber.open(file) as pdf:
        total_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            row = parse_log_page(page)
            row["page"] = i + 1
            pages.append(row)

    holes = {}
    for row in pages:
        header = row.get("header")
        hole_id = header["hole_id"] if header else None
        if hole_id is None:
            continue
        holes.setdefault(hole_id, []).append(row)

    return {
        "pages": pages,
        "holes": holes,
        "total_pages": total_pages,
    }
