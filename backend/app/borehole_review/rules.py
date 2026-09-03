"""Deterministic rule-checking engine for borehole log review (Phase 2a).

Implements every check listed in reference/borehole-log-standard.md's
Part 4.1 "Rule-checkable" breakdown - no more, no less. Judgment-based
(Part 4.2) checks live in judgment.py; Part 4.3 (not checkable at all) is
never attempted here.

Each check returns one or more Findings: a structured result carrying the
specific data compared and a plain-language explanation, not just a
pass/fail flag - the same "show your work" principle calculations.py
already follows for lab results. Every finding is tagged
category="rule_checked" so the review endpoint (and, later, Phase 2b's UI)
can separate these from judgment.py's category="judgment_based" findings.

Works directly off backend/app/parsers/borehole_log.py's parsed output
(and, for the column-caption check, the same pdfplumber word list the
parser itself extracts) plus optionally-matched lab report results parsed
by the other report parsers (atterberg.py, psd.py) for cross-referencing
against the log's field-logged descriptions.
"""

import re

from .. import calculations

CATEGORY = "rule_checked"

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_SKIPPED = "skipped"


def _finding(check, section, status, explanation, compared=None):
    return {
        "check": check,
        "standard_section": section,
        "status": status,
        "category": CATEGORY,
        "compared": compared or {},
        "explanation": explanation,
    }


# ---------------------------------------------------------------------------
# Section 2: required header fields
# ---------------------------------------------------------------------------

# Fields borehole_log.py's parse_log_header() actually extracts, per log
# type, matched against reference/borehole-log-standard.md's per-type
# "required header fields" tables (§2.1-§2.4).
_COMMON_REQUIRED_HEADER_FIELDS = [
    "hole_id",
    "sheet",
    "sheet_total",
    "client",
    "project_no",
    "project",
    "logged_by",
    "checked_by",
    "location",
    "start_date",
    "end_date",
    "easting",
    "northing",
    "rl_m",
    "total_depth_m",
    "surface",
    "datum",
]

REQUIRED_HEADER_FIELDS_BY_TYPE = {
    "Borehole": _COMMON_REQUIRED_HEADER_FIELDS + ["driller", "hole_diameter"],
    "Cored Borehole": _COMMON_REQUIRED_HEADER_FIELDS + ["driller", "hole_diameter"],
    "Pavement Dip": _COMMON_REQUIRED_HEADER_FIELDS + ["driller", "hole_diameter"],
    "Test Pit": _COMMON_REQUIRED_HEADER_FIELDS + ["operator"],
}

# The standard also requires these per type, but borehole_log.py doesn't
# extract them into the header dict yet (they're not part of Phase 2a's
# parser-gap scope - see reference/borehole-log-standard.md §2) - so they
# can't be rule-checked. Surfaced explicitly rather than silently ignored.
_HEADER_FIELDS_NOT_YET_EXTRACTED = {
    "Borehole": ["Drill Rig", "Inclination", "Vertical Datum", "Bearing"],
    "Cored Borehole": ["Drill Rig", "Inclination", "Vertical Datum", "Bearing"],
    "Pavement Dip": ["Drill Rig", "Inclination", "Vertical Datum", "Bearing", "Location Meth."],
    "Test Pit": ["Plant", "Orientation", "Vertical Datum", "Dimensions"],
}


def check_required_header_fields(header: dict) -> list:
    log_type = header.get("log_type")
    required = REQUIRED_HEADER_FIELDS_BY_TYPE.get(log_type)
    if required is None:
        return [
            _finding(
                "required_header_fields",
                "§2",
                STATUS_SKIPPED,
                f"Log type {log_type!r} isn't Borehole/Cored Borehole/Pavement Dip/Test Pit - "
                "can't determine which header fields the standard requires.",
            )
        ]

    missing = [f for f in required if not header.get(f)]
    status = STATUS_PASS if not missing else STATUS_FAIL
    findings = [
        _finding(
            "required_header_fields",
            f"§2 ({log_type})",
            status,
            (
                f"All {len(required)} extractable required header fields for {log_type} are present."
                if status == STATUS_PASS
                else f"Missing required header field(s) for {log_type}: {', '.join(missing)}."
            ),
            compared={"log_type": log_type, "required": required, "missing": missing},
        )
    ]

    not_extracted = _HEADER_FIELDS_NOT_YET_EXTRACTED.get(log_type)
    if not_extracted:
        findings.append(
            _finding(
                "required_header_fields_coverage",
                f"§2 ({log_type})",
                STATUS_SKIPPED,
                f"The standard also requires {', '.join(not_extracted)} for {log_type} logs, but the "
                "parser doesn't extract these fields yet, so they can't be checked.",
                compared={"log_type": log_type, "not_yet_extracted": not_extracted},
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Section 2: required table-column captions
# ---------------------------------------------------------------------------

# Column captions print either normally (wide columns like MATERIAL
# DESCRIPTION) or as individually-reversed rotated words (narrow columns
# like METHOD/DEPTH/GRAPHIC LOG) - see borehole_log.py's module docstring.
# Checked as single keywords rather than full multi-word phrases, since
# each rotated word is an independent token in the extracted word list.
_CAPTION_HEADER_TOP_RANGE = (160, 220)

EXPECTED_CAPTION_WORDS_BY_TYPE = {
    "Borehole": [
        "METHOD", "SUPPORT", "DEPTH", "GRAPHIC", "CLASSIFICATION", "SYMBOL",
        "MATERIAL", "DESCRIPTION", "MOISTURE", "CONSISTENCY", "OBSERVATIONS",
    ],
    "Cored Borehole": [
        "METHOD", "CORE", "RUN", "DEPTH", "GRAPHIC", "MATERIAL", "DESCRIPTION",
        "WEATHERING", "STRENGTH", "TCR", "DEFECT", "SPACING", "OBSERVATIONS",
    ],
    "Pavement Dip": [
        "METHOD", "SUPPORT", "DCP", "GROUND", "WATER", "DEPTH", "GRAPHIC",
        "CLASSIFICATION", "SYMBOL", "MATERIAL", "DESCRIPTION", "OBSERVATIONS",
    ],
    "Test Pit": [
        "METHOD", "SUPPORT", "GROUND", "WATER", "DCP", "DEPTH", "GRAPHIC",
        "CLASSIFICATION", "SYMBOL", "MATERIAL", "DESCRIPTION", "OBSERVATIONS",
    ],
}


def _header_caption_tokens(words) -> set:
    tokens = set()
    lo, hi = _CAPTION_HEADER_TOP_RANGE
    for w in words:
        if lo <= w["top"] <= hi:
            t = w["text"].upper()
            tokens.add(t)
            tokens.add(t[::-1])
    return tokens


def check_required_columns(words, log_type: str) -> list:
    expected = EXPECTED_CAPTION_WORDS_BY_TYPE.get(log_type)
    if expected is None:
        return [
            _finding(
                "required_table_columns",
                "§2",
                STATUS_SKIPPED,
                f"Log type {log_type!r} isn't a recognised type - can't determine which "
                "table columns the standard requires.",
            )
        ]

    tokens = _header_caption_tokens(words)
    missing = [c for c in expected if c not in tokens]
    status = STATUS_PASS if not missing else STATUS_FAIL
    return [
        _finding(
            "required_table_columns",
            f"§2 ({log_type})",
            status,
            (
                f"All {len(expected)} expected column-caption keywords for {log_type} were found."
                if status == STATUS_PASS
                else f"Expected column-caption keyword(s) not found for {log_type}: {', '.join(missing)}."
            ),
            compared={"log_type": log_type, "expected": expected, "missing": missing},
        )
    ]


# ---------------------------------------------------------------------------
# §3.11: USCS group symbol validity + boundary-symbol format
# ---------------------------------------------------------------------------

VALID_USCS_SYMBOLS = {
    "GW", "GP", "GM", "GC", "SW", "SP", "SM", "SC",
    "MH", "ML", "OL", "CH", "CI", "CL", "OH", "PT",
}
_LEADING_SYMBOL_RE = re.compile(r"^([A-Z]{1,2}(?:-[A-Z]{1,2})?)\b")
_BOUNDARY_SYMBOL_RE = re.compile(r"^[A-Z]{1,2}-[A-Z]{1,2}$")


def _leading_symbol(text: str):
    m = _LEADING_SYMBOL_RE.match(text.strip())
    return m.group(1) if m else None


def check_valid_uscs_symbols(strata: list) -> list:
    """A stratum's USCS symbol is read from the leading token of its
    description text (e.g. "CI-CH Sandy CLAY: ..."), matching how the
    example logs actually print it - AS1726 nominally puts the group
    symbol in its own column, but in practice it prefixes the description
    in this template. Words like "TOPSOIL"/"FILL" that aren't USCS symbols
    are excluded by checking against the known symbol set, not just
    "looks like an all-caps token"."""
    findings = []
    for stratum in strata:
        symbol = _leading_symbol(stratum.get("text", ""))
        if symbol is None:
            continue

        if _BOUNDARY_SYMBOL_RE.match(symbol):
            parts = symbol.split("-")
            # CL-ML is the one boundary symbol that isn't "two valid group
            # symbols joined" - it's its own named borderline zone (§3.11).
            if symbol == "CL-ML" or all(p in VALID_USCS_SYMBOLS for p in parts):
                findings.append(
                    _finding(
                        "valid_uscs_symbol",
                        "§3.11",
                        STATUS_PASS,
                        f"Boundary symbol {symbol!r} follows the XX-YY format with valid group symbols.",
                        compared={"symbol": symbol, "stratum_text": stratum["text"][:80]},
                    )
                )
            else:
                findings.append(
                    _finding(
                        "valid_uscs_symbol",
                        "§3.11",
                        STATUS_FAIL,
                        f"{symbol!r} isn't a recognised USCS boundary symbol (not two valid group "
                        "symbols joined, and not the CL-ML borderline zone).",
                        compared={"symbol": symbol, "stratum_text": stratum["text"][:80]},
                    )
                )
            continue

        if symbol in VALID_USCS_SYMBOLS:
            findings.append(
                _finding(
                    "valid_uscs_symbol",
                    "§3.11",
                    STATUS_PASS,
                    f"{symbol!r} is a valid USCS group symbol.",
                    compared={"symbol": symbol, "stratum_text": stratum["text"][:80]},
                )
            )
        # A leading token that isn't in the valid set (e.g. "TOPSOIL",
        # "FILL") is not a USCS symbol at all - not a failure, just not
        # applicable to this check.
    return findings


# ---------------------------------------------------------------------------
# §3.14: weathering/alteration symbol validity
# ---------------------------------------------------------------------------

VALID_WEATHERING_SYMBOLS = {"RS", "XW", "XA", "HW", "HA", "DW", "DA", "MW", "MA", "SW", "SA", "FR"}
_WEATHERING_TOKEN_RE = re.compile(r"\b(RS|XW|XA|HW|HA|DW|DA|MW|MA|SW|SA|FR)\b")
# Tokens that look like weathering symbols but are common English words or
# other abbreviations in this document family - excluded to avoid false
# positives (e.g. "SW" is also the log type "Pavement Dip"... no; more
# concretely "SA" could appear in unrelated text).
_WEATHERING_FALSE_FRIENDS = set()


def check_weathering_symbols(strata: list) -> list:
    """Scans strata description text for weathering/alteration symbols
    and confirms each is one of §3.14's defined codes. This is a "does the
    token look right" check, not a check on whether the weathering grade
    is geologically apt (that's judgment.py's job, per §4.2)."""
    findings = []
    seen = set()
    for stratum in strata:
        text = stratum.get("text", "")
        for m in _WEATHERING_TOKEN_RE.finditer(text):
            token = m.group(1)
            key = (token, text[:40])
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                _finding(
                    "valid_weathering_symbol",
                    "§3.14",
                    STATUS_PASS if token in VALID_WEATHERING_SYMBOLS else STATUS_FAIL,
                    f"{token!r} is a valid weathering/alteration symbol." if token in VALID_WEATHERING_SYMBOLS
                    else f"{token!r} is not one of §3.14's defined weathering/alteration symbols.",
                    compared={"symbol": token, "stratum_text": text[:80]},
                )
            )
    return findings


# ---------------------------------------------------------------------------
# §3.1 / §3.15: defect description field order/format + defect symbols
# ---------------------------------------------------------------------------

# "CZ" (Crushed Zone) isn't in the AECOM §3.15 table captured in
# reference/borehole-log-standard.md - confirmed by the corpus sweep
# (2 real instances, Heathcote.pdf DBH39: "CZ, 30 mm thick") as a genuine,
# undocumented-here code, left unrecognised (safely excluded from spacing/
# seam-content, not guessed at) until confirmed. Meaning since confirmed:
# Crushed Zone, natural rock-mass damage - the same family as CS (Crushed
# Seam), just describing a zone rather than a discrete seam - grouped with
# it accordingly below and in classification.py's _SEAM_TYPE_CODES.
VALID_DEFECT_TYPES = {"P", "J", "S", "SZ", "MB", "DL", "DB", "HB", "SS", "CS", "CZ", "IS", "EW"}
VALID_PLANARITY = {"PR", "CU", "UN", "ST", "IR"}
VALID_ROUGHNESS = {"VR", "RF", "SM", "PO", "SL"}
VALID_INFILL = {"CN", "SN", "VN", "CT", "OP", "CA", "FE", "CH", "QZ"}

# Type; dip/direction; planarity; roughness; infill/coating; other
# descriptors (§3.1, 28/10/2025 revision). Dip/direction is "NN/NNN°" or
# similar; the remaining fields are comma-separated abbreviation tokens.
_DEFECT_DESC_RE = re.compile(
    r"^\s*(?:healed\s+)?"
    r"(?P<type>[A-Z]{1,2})\s*,\s*"
    r"(?P<dip>\d{1,3}\s*/\s*\d{1,3}\s*°?)\s*,\s*"
    r"(?P<planarity>[A-Z]{2})\s*,\s*"
    r"(?P<roughness>[A-Z]{2})\s*,\s*"
    r"(?P<infill>[A-Za-z]{2,4})",
    re.IGNORECASE,
)


def check_defect_descriptions(notes: list) -> list:
    """Syntactic check only - does a defect description follow §3.1's
    Type;dip/direction;planarity;roughness;infill order with valid
    symbols in each slot - not a check on whether the description is
    geologically apt (§4.1 is explicit about that boundary)."""
    findings = []
    for text in notes:
        m = _DEFECT_DESC_RE.match(text)
        if not m:
            continue  # not a defect-description-shaped line; not applicable
        parts = m.groupdict()
        bad = []
        if parts["type"].upper() not in VALID_DEFECT_TYPES:
            bad.append(f"type {parts['type']!r}")
        if parts["planarity"].upper() not in VALID_PLANARITY:
            bad.append(f"planarity {parts['planarity']!r}")
        if parts["roughness"].upper() not in VALID_ROUGHNESS:
            bad.append(f"roughness {parts['roughness']!r}")
        if parts["infill"].upper() not in VALID_INFILL:
            bad.append(f"infill/coating {parts['infill']!r}")

        status = STATUS_FAIL if bad else STATUS_PASS
        findings.append(
            _finding(
                "defect_description_format",
                "§3.1 / §3.15",
                status,
                (
                    "Defect description follows Type;dip/direction;planarity;roughness;infill "
                    f"order with valid symbols in each slot: {text!r}."
                    if status == STATUS_PASS
                    else f"Defect description {text!r} has invalid symbol(s): {', '.join(bad)}."
                ),
                compared={"text": text, **{k: v for k, v in parts.items()}},
            )
        )
    return findings


# ---------------------------------------------------------------------------
# §3.16: field-test/sample type validity, with HB context disambiguation
# ---------------------------------------------------------------------------

# The parser (borehole_log.py's _ENTRY_LABEL_RE) currently only ever
# produces these types - this check mostly guards against a future parser
# change introducing an unrecognised one, since C/B (Core/Bulk Sample) and
# others aren't parsed into field_test_entries yet.
VALID_FIELD_TEST_TYPES = {"SPT", "D", "ES", "U"}


def check_field_test_types(field_test_entries: list) -> list:
    findings = []
    for entry in field_test_entries:
        t = entry.get("type")
        status = STATUS_PASS if t in VALID_FIELD_TEST_TYPES else STATUS_FAIL
        findings.append(
            _finding(
                "valid_field_test_type",
                "§3.16",
                status,
                f"{t!r} is a recognised field-test/sample type." if status == STATUS_PASS
                else f"{t!r} is not one of §3.16's field-test/sample abbreviations.",
                compared={"type": t, "depth_from_m": entry.get("depth_from_m")},
            )
        )
    return findings


def check_hb_context(field_test_entries: list, notes: list) -> list:
    """HB is context-dependent: SPT Hammer Bouncing in a field-test entry
    (§3.16) vs. Handling Break in a defect-type description (§3.15) - same
    two letters, unrelated meanings. This check demonstrates the
    disambiguation explicitly (per reference/borehole-log-standard.md's
    §4.1 callout) rather than bare-matching the symbol: each occurrence is
    resolved by which field it came from, not flagged as ambiguous."""
    findings = []
    for entry in field_test_entries:
        blows = entry.get("blows") or ""
        if "HB" in blows.upper():
            findings.append(
                _finding(
                    "hb_context_disambiguation",
                    "§3.16 vs §3.15",
                    STATUS_PASS,
                    "'HB' found in an SPT field-test entry - resolved as 'SPT Hammer Bouncing' "
                    "(§3.16), not 'Handling Break' (§3.15), because of its column context.",
                    compared={"context": "field_test_entry", "blows": blows},
                )
            )
    for text in notes:
        if re.search(r"\bHB\b", text):
            findings.append(
                _finding(
                    "hb_context_disambiguation",
                    "§3.16 vs §3.15",
                    STATUS_PASS,
                    "'HB' found in a defect-type/notes context - resolved as 'Handling Break' "
                    "(§3.15), not 'SPT Hammer Bouncing' (§3.16), because of its column context.",
                    compared={"context": "notes", "text": text[:80]},
                )
            )
    return findings


# ---------------------------------------------------------------------------
# §3.13: rock strength band consistency
# ---------------------------------------------------------------------------

_ROCK_STRENGTH_BANDS = [
    ("Very Low", 0.6, 2, 0.03, 0.1),
    ("Low", 2, 6, 0.1, 0.3),
    ("Medium", 6, 20, 0.3, 1),
    ("High", 20, 60, 1, 3),
    ("Very High", 60, 200, 3, 10),
    ("Extremely High", 200, float("inf"), 10, float("inf")),
]


def _strength_term_from_ucs(ucs_mpa: float):
    for name, lo, hi, _, _ in _ROCK_STRENGTH_BANDS:
        if lo < ucs_mpa <= hi:
            return name
    return "Very Low" if ucs_mpa <= 0.6 else None


def _strength_term_from_is50(is50_mpa: float):
    for name, _, _, lo, hi in _ROCK_STRENGTH_BANDS:
        if lo < is50_mpa <= hi:
            return name
    return None


_STRENGTH_TERM_TOKEN_RE = re.compile(
    r"\b(Very Low|Low|Medium|High|Very High|Extremely High)\b", re.IGNORECASE
)


def check_rock_strength_band(point_load_ucs_readings: list, strata: list, notes: list) -> list:
    """Given a UCS or Is(50) reading, computes the strength term §3.13
    implies and compares it against a strength term word found in the
    same page's strata/notes text, when one is present. Skips (not fail)
    when no logged strength term is found to compare against."""
    findings = []
    logged_text = " ".join([s.get("text", "") for s in strata] + list(notes))
    logged_terms = {m.group(1).title() for m in _STRENGTH_TERM_TOKEN_RE.finditer(logged_text)}

    for reading in point_load_ucs_readings:
        if reading["type"] == "ucs":
            implied = _strength_term_from_ucs(reading["value_mpa"])
            source = f"UCS={reading['value_mpa']} MPa"
        elif reading["type"].startswith("point_load_is50"):
            implied = _strength_term_from_is50(reading["value_mpa"])
            source = f"Is(50)={reading['value_mpa']} MPa"
        else:
            continue

        if implied is None:
            continue

        if not logged_terms:
            findings.append(
                _finding(
                    "rock_strength_band_consistency",
                    "§3.13",
                    STATUS_SKIPPED,
                    f"{source} implies strength term {implied!r}, but no strength term word was "
                    "found on this page to compare it against.",
                    compared={"source": source, "implied_term": implied},
                )
            )
            continue

        status = STATUS_PASS if implied in logged_terms else STATUS_FAIL
        findings.append(
            _finding(
                "rock_strength_band_consistency",
                "§3.13",
                status,
                (
                    f"{source} implies strength term {implied!r}, consistent with the logged term(s) "
                    f"{sorted(logged_terms)}."
                    if status == STATUS_PASS
                    else f"{source} implies strength term {implied!r}, but logged term(s) are "
                    f"{sorted(logged_terms)} - inconsistent."
                ),
                compared={"source": source, "implied_term": implied, "logged_terms": sorted(logged_terms)},
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Cross-referencing against lab report results
# ---------------------------------------------------------------------------

_SAMPLE_ID_RE = re.compile(r"^(?P<hole_ref>.+?)_?(?P<from>\d+(?:\.\d+)?)-(?P<to>\d+(?:\.\d+)?)$")
_PLASTICITY_TERM_RE = re.compile(r"\b(low|medium|high)\s+plasticity\b", re.IGNORECASE)

PLASTICITY_LL_BANDS = [
    ("low", 0, 35),
    ("medium", 35, 50),
    ("high", 50, float("inf")),
]


def match_lab_samples_to_log(hole_id: str, field_test_entries: list, strata: list, lab_results: list) -> list:
    """Matches lab report rows (Atterberg/PSD; sample_id like
    "HA2_0.4-0.8") to this log's hole by name and to a strata/field-test
    depth by range overlap. This is the stateless, request-scoped matching
    the phase brief calls for - no database, matched fresh per request
    from whatever lab PDFs were uploaded alongside the log."""
    matches = []
    if not hole_id:
        return matches

    for lab in lab_results:
        sample_id = lab.get("sample_id") or ""
        m = _SAMPLE_ID_RE.match(sample_id.strip())
        if not m:
            continue
        hole_ref = m.group("hole_ref").strip("_- ")
        depth_from, depth_to = float(m.group("from")), float(m.group("to"))

        if hole_ref.upper() not in hole_id.upper() and hole_id.upper() not in hole_ref.upper():
            continue

        matched_stratum = None
        for stratum in strata:
            d = stratum.get("depth_from_m")
            if d is not None and depth_from - 0.5 <= d <= depth_to + 0.5:
                matched_stratum = stratum
                break

        matches.append(
            {
                "lab_result": lab,
                "matched_stratum": matched_stratum,
                "depth_from_m": depth_from,
                "depth_to_m": depth_to,
            }
        )
    return matches


def _plasticity_band(ll: float) -> str:
    for name, lo, hi in PLASTICITY_LL_BANDS:
        if lo < ll <= hi or (lo == 0 and ll <= hi):
            return name
    return "high"


def check_plasticity_vs_lab(matches: list) -> list:
    """§3.2: does the logged plasticity term (low/medium/high) match the
    band implied by the lab's own LL%? When they disagree, the field
    description is what should change (per the user's explicit reasoning
    logged in the phase brief) - so the finding states the corrected
    wording, not just pass/fail."""
    findings = []
    for match in matches:
        lab = match["lab_result"]
        ll = lab.get("liquid_limit")
        stratum = match["matched_stratum"]
        if ll is None:
            continue
        if stratum is None:
            findings.append(
                _finding(
                    "plasticity_term_vs_lab_ll",
                    "§3.2",
                    STATUS_SKIPPED,
                    f"Lab sample {lab.get('sample_id')!r} (LL={ll}%) has no matching depth range "
                    "in this log's extracted strata, so its logged plasticity term couldn't be found.",
                    compared={"sample_id": lab.get("sample_id"), "liquid_limit": ll},
                )
            )
            continue

        text = stratum["text"]
        m = _PLASTICITY_TERM_RE.search(text)
        implied_band = _plasticity_band(ll)
        if m is None:
            findings.append(
                _finding(
                    "plasticity_term_vs_lab_ll",
                    "§3.2",
                    STATUS_SKIPPED,
                    f"No plasticity term (low/medium/high) found in the logged description at "
                    f"{match['depth_from_m']}-{match['depth_to_m']}m to compare against lab LL={ll}%.",
                    compared={"sample_id": lab.get("sample_id"), "liquid_limit": ll, "stratum_text": text[:80]},
                )
            )
            continue

        logged_band = m.group(1).lower()
        status = STATUS_PASS if logged_band == implied_band else STATUS_FAIL
        explanation = (
            f"Logged '{logged_band} plasticity' matches lab LL={ll}% ({implied_band} plasticity band, §3.2)."
            if status == STATUS_PASS
            else (
                f"Lab LL={ll}% classifies as {implied_band} plasticity (§3.2), but the log says "
                f"'{logged_band} plasticity' - consider updating the description to "
                f"'{implied_band} plasticity' to match the lab result."
            )
        )
        findings.append(
            _finding(
                "plasticity_term_vs_lab_ll",
                "§3.2",
                status,
                explanation,
                compared={
                    "sample_id": lab.get("sample_id"),
                    "liquid_limit": ll,
                    "logged_term": logged_band,
                    "implied_term": implied_band,
                },
            )
        )
    return findings


def check_uscs_symbol_vs_lab(matches: list) -> list:
    """§3.11: does the logged USCS symbol match the zone implied by the
    lab's LL/PI position on the A-line? Suggests the corrected symbol
    when they disagree, per the same "lab is authoritative" reasoning as
    the plasticity-term check."""
    findings = []
    for match in matches:
        lab = match["lab_result"]
        ll, pi = lab.get("liquid_limit"), lab.get("plasticity_index")
        stratum = match["matched_stratum"]
        if ll is None or pi is None:
            continue
        if stratum is None:
            continue  # already reported by check_plasticity_vs_lab

        logged_symbol = _leading_symbol(stratum["text"])
        implied_zone = calculations.uscs_fine_grained_zone(ll, pi)
        implied_symbols = set(implied_zone.replace(" or ", "|").split("|"))

        if logged_symbol is None:
            findings.append(
                _finding(
                    "uscs_symbol_vs_lab_a_line",
                    "§3.11",
                    STATUS_SKIPPED,
                    f"Lab LL={ll}%/PI={pi}% implies zone {implied_zone!r}, but no USCS symbol was "
                    "found at the start of the logged description to compare it against.",
                    compared={"sample_id": lab.get("sample_id"), "liquid_limit": ll, "plasticity_index": pi},
                )
            )
            continue

        # A boundary symbol (e.g. CI-CH) matches if either half is in the
        # implied set - it's a legitimate straddle between two zones.
        logged_parts = logged_symbol.split("-")
        match_ok = any(p in implied_symbols for p in logged_parts) or logged_symbol in implied_symbols
        status = STATUS_PASS if match_ok else STATUS_FAIL
        explanation = (
            f"Logged symbol {logged_symbol!r} is consistent with the zone implied by lab "
            f"LL={ll}%/PI={pi}% ({implied_zone}, §3.11)."
            if status == STATUS_PASS
            else (
                f"Lab LL={ll}%/PI={pi}% plots in the {implied_zone} zone (§3.11's A-line, "
                f"PI={calculations.a_line_pi(ll):.1f} at this LL), but the log says {logged_symbol!r} - "
                f"consider updating the classification to match {implied_zone}."
            )
        )
        findings.append(
            _finding(
                "uscs_symbol_vs_lab_a_line",
                "§3.11",
                status,
                explanation,
                compared={
                    "sample_id": lab.get("sample_id"),
                    "liquid_limit": ll,
                    "plasticity_index": pi,
                    "logged_symbol": logged_symbol,
                    "implied_zone": implied_zone,
                },
            )
        )
    return findings


def check_grading_symbol_vs_lab(hole_id: str, strata: list, psd_results: list) -> list:
    """§3.11: for a logged clean-gravel/clean-sand symbol (GW/GP/SW/SP),
    checks the Cu/Cc criteria against a matched PSD lab result's grading
    curve. Skipped when D10/D30/D60 can't be interpolated (e.g. the tested
    sieve range doesn't reach 10% passing) or when the logged symbol isn't
    one this criterion applies to."""
    findings = []
    matches = match_lab_samples_to_log(hole_id, [], strata, psd_results)
    applicable = {"GW", "GP", "SW", "SP"}
    for match in matches:
        lab = match["lab_result"]
        stratum = match["matched_stratum"]
        if stratum is None:
            continue
        logged_symbol = _leading_symbol(stratum["text"])
        if logged_symbol not in applicable:
            continue

        readings = lab.get("readings") or []
        curve = calculations.grading_curve_cu_cc(readings) if readings else None
        if curve is None:
            findings.append(
                _finding(
                    "grading_curve_symbol_vs_lab",
                    "§3.11",
                    STATUS_SKIPPED,
                    f"Logged symbol {logged_symbol!r} needs Cu/Cc to verify, but D10/D30/D60 "
                    f"couldn't be interpolated from PSD sample {lab.get('sample_id')!r}'s tested range.",
                    compared={"sample_id": lab.get("sample_id"), "logged_symbol": logged_symbol},
                )
            )
            continue

        cu, cc = curve["cu"], curve["cc"]
        well_graded = logged_symbol in ("GW", "SW")
        cu_threshold = 4 if logged_symbol == "GW" else 6
        cu_ok = cu >= cu_threshold
        cc_ok = 1 <= cc <= 3
        meets_well_graded_criteria = cu_ok and cc_ok

        if well_graded:
            status = STATUS_PASS if meets_well_graded_criteria else STATUS_FAIL
            explanation = (
                f"Logged {logged_symbol!r} (well graded): Cu={cu:.1f} (>= {cu_threshold} required) and "
                f"Cc={cc:.1f} (1-3 required) both meet the criteria."
                if status == STATUS_PASS
                else f"Logged {logged_symbol!r} (well graded) requires Cu>={cu_threshold} and Cc in "
                f"1-3, but the grading curve gives Cu={cu:.1f}, Cc={cc:.1f} - doesn't meet the "
                f"criteria for {logged_symbol}; consider {logged_symbol[0]}P (poorly graded)."
            )
        else:
            # GP/SP (poorly graded): correct precisely when the well-graded
            # criteria are NOT met.
            status = STATUS_PASS if not meets_well_graded_criteria else STATUS_FAIL
            explanation = (
                f"Logged {logged_symbol!r} (poorly graded): Cu={cu:.1f}, Cc={cc:.1f} correctly fail "
                f"the well-graded criteria (Cu>={cu_threshold}, Cc 1-3)."
                if status == STATUS_PASS
                else f"Logged {logged_symbol!r} (poorly graded), but Cu={cu:.1f}, Cc={cc:.1f} actually "
                f"meet the well-graded criteria (Cu>={cu_threshold}, Cc 1-3) - consider "
                f"{logged_symbol[0]}W (well graded)."
            )

        findings.append(
            _finding(
                "grading_curve_symbol_vs_lab",
                "§3.11",
                status,
                explanation,
                compared={
                    "sample_id": lab.get("sample_id"),
                    "logged_symbol": logged_symbol,
                    "cu": cu,
                    "cc": cc,
                    "d10_mm": curve["d10_mm"],
                    "d30_mm": curve["d30_mm"],
                    "d60_mm": curve["d60_mm"],
                },
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_all_checks(parsed_page: dict, words: list, lab_results: dict = None) -> list:
    """Runs every §4.1 rule check against one parsed log page.

    lab_results, if given: {"atterberg": [...], "psd": [...]} - the output
    of the existing Atterberg/PSD parsers for any lab report PDFs uploaded
    alongside the log in the same request. Cross-referencing checks are
    skipped per-sample (not the whole page) when no lab result matches."""
    header = parsed_page.get("header") or {}
    log_type = header.get("log_type")
    strata = parsed_page.get("strata") or []
    field_test_entries = parsed_page.get("field_test_entries") or []
    point_load_ucs_readings = parsed_page.get("point_load_ucs_readings") or []
    notes = parsed_page.get("notes") or []
    hole_id = header.get("hole_id")

    findings = []
    findings += check_required_header_fields(header)
    findings += check_required_columns(words, log_type)
    findings += check_valid_uscs_symbols(strata)
    findings += check_weathering_symbols(strata)
    findings += check_defect_descriptions(notes)
    findings += check_field_test_types(field_test_entries)
    findings += check_hb_context(field_test_entries, notes)
    findings += check_rock_strength_band(point_load_ucs_readings, strata, notes)

    lab_results = lab_results or {}
    atterberg_results = lab_results.get("atterberg") or []
    psd_results = lab_results.get("psd") or []

    if atterberg_results:
        matches = match_lab_samples_to_log(hole_id, field_test_entries, strata, atterberg_results)
        findings += check_plasticity_vs_lab(matches)
        findings += check_uscs_symbol_vs_lab(matches)
    else:
        findings.append(
            _finding(
                "plasticity_term_vs_lab_ll",
                "§3.2",
                STATUS_SKIPPED,
                "No Atterberg lab report was provided with this review - plasticity-term and "
                "USCS-symbol-vs-lab checks are skipped, not passed.",
            )
        )

    if psd_results:
        findings += check_grading_symbol_vs_lab(hole_id, strata, psd_results)
    else:
        findings.append(
            _finding(
                "grading_curve_symbol_vs_lab",
                "§3.11",
                STATUS_SKIPPED,
                "No PSD lab report was provided with this review - grading-curve-vs-symbol "
                "checks are skipped, not passed.",
            )
        )

    return findings
