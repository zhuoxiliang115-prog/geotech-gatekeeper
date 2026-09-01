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
_DEPTH_COLUMN_RANGES_BY_TYPE = {
    "Cored Borehole": (125, 141),
    "Test Pit": (183, 197),
}

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


def _depth_calibration(words, log_type):
    """Fits a linear map from page-y (top) to borehole depth (m) using the
    depth-axis tick labels (0.0, 1.0, 2.0, ...). Falls back to None if
    fewer than two usable ticks are found, since a page can't be
    calibrated off a single point.

    The DEPTH column sits at a different x-position for Cored Borehole and
    Test Pit pages than for Borehole/Pavement Dip - see
    _DEPTH_COLUMN_RANGES_BY_TYPE."""
    lo, hi = _DEPTH_COLUMN_RANGES_BY_TYPE.get(log_type, COLUMN_RANGES["depth"])
    ticks = []
    for w in words:
        if lo <= w["x0"] <= hi and _TICK_VALUE_RE.match(w["text"]):
            ticks.append((w["top"], float(w["text"])))
    if len(ticks) < 2:
        return None

    n = len(ticks)
    mean_x = sum(t for t, _ in ticks) / n
    mean_y = sum(v for _, v in ticks) / n
    num = sum((t - mean_x) * (v - mean_y) for t, v in ticks)
    den = sum((t - mean_x) ** 2 for t, _ in ticks)
    if den == 0:
        return None
    slope = num / den
    intercept = mean_y - slope * mean_x
    return lambda top: round(slope * top + intercept, 2)


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


def _extract_strata(words, depth_of):
    rows = _cluster_rows(_column_words(words, "description"))
    # Drop the printed column caption and any header/footer text that
    # shares the description column's x-range but sits above/below the
    # actual log body.
    rows = [r for r in rows if not r["text"].startswith("MATERIAL DESCRIPTION")]
    rows = [r for r in rows if "Log continued" not in r["text"]]
    rows = [r for r in rows if "logging description" not in r["text"].lower()]
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
    note_words = _column_words(words, "notes")
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
    remarks = [
        r["text"] for r in note_rows if not _IS50_RE.search(r["text"]) and not _UCS_RE.search(r["text"])
    ]
    return readings, remarks


def parse_log_page(page) -> dict:
    text = page.extract_text() or ""
    page_type = classify_log_page(text)

    result = {"page_type": page_type}
    if page_type != PAGE_TYPE_LOG:
        return result

    words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
    header = parse_log_header(text)
    depth_of = _depth_calibration(words, header["log_type"])

    result["header"] = header
    result["depth_axis_calibrated"] = depth_of is not None
    result["strata"] = _extract_strata(words, depth_of)
    result["field_test_entries"] = _extract_field_test_entries(words)
    result["dcp_readings"] = _extract_dcp_readings(words, depth_of)
    readings, remarks = _extract_notes(words, depth_of, header["log_type"])
    result["point_load_ucs_readings"] = readings
    result["notes"] = remarks

    if header["log_type"] in _SOIL_LOG_TYPES:
        consistency_readings = _extract_consistency_readings(words, depth_of, header["log_type"])
        _attach_readings_to_strata(
            result["strata"], consistency_readings["consistency_relative_density"], "consistency_relative_density"
        )
        _attach_readings_to_strata(result["strata"], consistency_readings["moisture"], "moisture_condition")
    else:
        # Cored Borehole (rock) - the columns don't exist on this layout;
        # the field is still present so downstream code (soil_parameters)
        # never has to special-case a missing key.
        for stratum in result["strata"]:
            stratum["consistency_relative_density"] = []
            stratum["moisture_condition"] = []
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
