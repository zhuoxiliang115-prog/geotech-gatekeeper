"""Stage 3: deterministic soil-type + consistency/relative-density
classification for one borehole stratum, feeding lookup.py's typical-
parameter table. Rules-only - no LLM judgment step (unlike judgment.py).
Anything that can't be confidently classified is flagged, never guessed.

Soil only (Fill, Clay, Sand) for this pass - Rock is a later phase and is
never reached here (Cored Borehole strata never carry a
consistency_relative_density field at all - see borehole_log.py).
"""

import re

CLAY_CONSISTENCY_CODES = {
    "VS": "clay_very_soft",
    "S": "clay_soft",
    "F": "clay_firm",
    "ST": "clay_stiff",
    "VST": "clay_very_stiff",
    "H": "clay_hard",
}

SAND_DENSITY_CODES = {
    "VL": "sand_very_loose",
    "L": "sand_loose",
    "MD": "sand_medium_dense",
    "D": "sand_dense",
    "VD": "sand_very_dense",
}

_SAND_BUCKET_LABELS = {
    "sand_very_loose": "Very loose",
    "sand_loose": "Loose",
    "sand_medium_dense": "Medium dense",
    "sand_dense": "Dense",
    "sand_very_dense": "Very dense",
}

_SAND_DENSITY_RANK = {bucket_id: i for i, bucket_id in enumerate(_SAND_BUCKET_LABELS)}

# §3.9 (reference/borehole-log-standard.md) SPT-N -> relative density bands
# - the commonly used Terzaghi & Peck figures. NOT independently verified
# against a real AS1726-2017 copy (the user's own caveat - their copy was
# copy-protected) - swap these if the standard or firm practice differs.
# Same boundary convention already used elsewhere in this codebase for an
# analogous ambiguity (rules.py's PLASTICITY_LL_BANDS): first band
# inclusive both ends, each subsequent band (prev_upper, this_upper].
SAND_SPT_N_BANDS = [
    ("sand_very_loose", 0, 4),
    ("sand_loose", 4, 10),
    ("sand_medium_dense", 10, 30),
    ("sand_dense", 30, 50),
    ("sand_very_dense", 50, float("inf")),
]

FILL_COMPACTED_KEYWORDS = ("well compacted", "engineered", "controlled")
FILL_UNCOMPACTED_KEYWORDS = ("uncompacted", "loose")

# AS1726 convention (already relied on by rules.py/judgment.py elsewhere in
# this project): the principal/major soil type is the capitalised noun
# right before the colon ("Gravelly SAND:", "Silty CLAY:") - modifiers
# ("Sandy", "Silty", "Clayey", "Gravelly") are not capitalised. Matching
# case-sensitively (no re.IGNORECASE) is what makes this work - it's the
# capitalisation itself that identifies the principal type, not just the
# word.
_PRINCIPAL_TYPE_RE = re.compile(r"\b(SAND|CLAY|SILT|GRAVEL)\b")
_CONNECTOR_WORDS = {"to", "or"}


def _classified(bucket_id, basis, warnings=None):
    return {
        "classified": True,
        "bucket_id": bucket_id,
        "flag": None,
        "classification_basis": basis,
        "warnings": warnings or [],
    }


def _not_classified(reason):
    return {
        "classified": False,
        "bucket_id": None,
        "flag": reason,
        "classification_basis": None,
        "warnings": [],
    }


def _find_principal_type(text: str):
    m = _PRINCIPAL_TYPE_RE.search(text)
    return m.group(1) if m else None


def _extract_codes(readings: list) -> list:
    """Joins a stratum's raw consistency/relative-density reading
    fragments and returns the distinct recognised codes found, in reading
    (depth) order. A printed transition like "St to VSt" prints across
    separate pdfplumber rows - ['St', 'to', 'VSt'] - so this also splits
    on whitespace/slashes/hyphens and drops connector words, rather than
    assuming one reading = one code."""
    codes = []
    seen = set()
    for text in readings:
        for token in re.split(r"[\s/\-]+", text.strip()):
            token = token.strip(".,").upper()
            if not token or token.lower() in _CONNECTOR_WORDS:
                continue
            if token not in seen:
                seen.add(token)
                codes.append(token)
    return codes


def _parse_n_value(raw):
    """SPT n_value is a free-text field (e.g. "16", or "R" for refusal
    per borehole_log.py's _SPT_DETAIL_RE) - only a clean leading integer
    is usable for the relative-density fallback; refusal/unparseable
    values correctly fall through to "no N-value available"."""
    if raw is None:
        return None
    m = re.match(r"^\d+", raw.strip())
    return int(m.group(0)) if m else None


def _nearest_spt_n(stratum: dict, field_test_entries: list):
    """Finds the SPT reading closest in depth to this stratum, among this
    page's field_test_entries. Returns the raw n_value string (or None if
    no usable SPT entry exists on this page)."""
    depth = stratum.get("depth_from_m")
    if depth is None:
        return None
    best, best_dist = None, None
    for entry in field_test_entries:
        if entry.get("type") != "SPT":
            continue
        entry_depth = entry.get("depth_from_m")
        if entry_depth is None:
            continue
        dist = abs(entry_depth - depth)
        if best_dist is None or dist < best_dist:
            best, best_dist = entry, dist
    return best.get("n_value") if best else None


def _bucket_from_spt_n(n_value: int):
    for bucket_id, lo, hi in SAND_SPT_N_BANDS:
        if (lo < n_value <= hi) or (lo == 0 and n_value <= hi):
            return bucket_id
    return None


def _classify_clay(stratum: dict, n_value):
    """Consistency term must be the printed CONSISTENCY column value -
    SPT-N/consistency correlation is explicitly not reliable enough to
    stake an automated classification on (per the user's own instruction),
    so N is only ever surfaced as a hint in the flag message, never used
    to assign a bucket."""
    codes = _extract_codes(stratum.get("consistency_relative_density") or [])
    matched = [c for c in codes if c in CLAY_CONSISTENCY_CODES]
    if not matched:
        hint = f" — nearby SPT N={n_value}, verify manually" if n_value is not None else ""
        return _not_classified(f"consistency not stated{hint}")

    bucket_id = CLAY_CONSISTENCY_CODES[matched[0]]
    warnings = []
    if len(matched) > 1:
        warnings.append(
            f"printed consistency term spans a transition ({'/'.join(matched)}) - "
            f"classified from the first (shallower) term, {matched[0]!r}"
        )
    return _classified(bucket_id, "printed consistency term", warnings)


def _classify_sand(stratum: dict, n_value):
    """Printed relative-density term is authoritative when present. Only
    falls back to the SPT-N bands when the column is genuinely missing -
    and cross-checks the two against each other when both exist, flagging
    (not blocking) a disagreement of more than one band."""
    codes = _extract_codes(stratum.get("consistency_relative_density") or [])
    matched = [c for c in codes if c in SAND_DENSITY_CODES]
    n_bucket = _bucket_from_spt_n(n_value) if n_value is not None else None

    if matched:
        bucket_id = SAND_DENSITY_CODES[matched[0]]
        warnings = []
        if len(matched) > 1:
            warnings.append(
                f"printed relative-density term spans a transition ({'/'.join(matched)}) - "
                f"classified from the first (shallower) term, {matched[0]!r}"
            )
        if n_bucket is not None and abs(_SAND_DENSITY_RANK[bucket_id] - _SAND_DENSITY_RANK[n_bucket]) > 1:
            warnings.append(
                f"printed term ({_SAND_BUCKET_LABELS[bucket_id]}) disagrees with nearby SPT N={n_value} "
                f"(implies {_SAND_BUCKET_LABELS[n_bucket]}) by more than one band - worth checking"
            )
        return _classified(bucket_id, "printed relative-density term", warnings)

    if n_bucket is not None:
        return _classified(
            n_bucket,
            f"SPT N={n_value} fallback (printed relative-density term missing; Terzaghi & Peck "
            "bands, not independently verified against AS1726-2017 - see SAND_SPT_N_BANDS)",
        )

    return _not_classified("relative density not stated, and no nearby SPT N-value to fall back on")


def _classify_fill(text: str):
    lower = text.lower()
    if any(kw in lower for kw in FILL_COMPACTED_KEYWORDS):
        return _classified("fill_well_compacted", "compaction descriptor (well compacted/engineered/controlled)")

    if any(kw in lower for kw in FILL_UNCOMPACTED_KEYWORDS):
        # Dominant type read from whatever follows "FILL -", same
        # principal-type convention used for Clay/Sand strata generally.
        after_fill = text.split("FILL", 1)[-1]
        principal = _find_principal_type(after_fill)
        if principal in ("CLAY", "SILT"):
            return _classified(
                "fill_uncompacted_cohesive", "compaction descriptor (uncompacted/loose) + cohesive dominant type"
            )
        if principal in ("SAND", "GRAVEL"):
            return _classified(
                "fill_uncompacted_non_cohesive",
                "compaction descriptor (uncompacted/loose) + granular dominant type",
            )
        return _not_classified(
            "compaction descriptor found (uncompacted/loose) but no clear dominant soil type "
            "to pick cohesive vs. non-cohesive"
        )

    return _not_classified(
        "no compaction descriptor found in the description (well compacted/engineered/controlled, "
        "or uncompacted/loose) - most fill descriptions won't have one; this is expected, not a bug"
    )


def classify_stratum(stratum: dict, field_test_entries: list) -> dict:
    """Classifies one stratum into a soil_typical_parameters.json bucket,
    or explains why it can't be. Returns:
        {"principal_soil_type": "Fill"|"Clay"|"Sand"|"Silt"|"Gravel"|None,
         "classified": bool, "bucket_id": str|None, "flag": str|None,
         "classification_basis": str|None, "warnings": [str, ...]}
    field_test_entries is the stratum's page's field_test_entries (for the
    clay/sand SPT-N lookup) - not scoped to this stratum alone, since SPT
    entries are matched to the nearest stratum by depth here, not the
    reverse."""
    text = stratum.get("text", "") or ""

    if text.lstrip().upper().startswith("FILL"):
        result = _classify_fill(text)
        result["principal_soil_type"] = "Fill"
        return result

    principal = _find_principal_type(text)

    if principal in ("CLAY", "SAND"):
        n_value = _parse_n_value(_nearest_spt_n(stratum, field_test_entries))
        result = _classify_clay(stratum, n_value) if principal == "CLAY" else _classify_sand(stratum, n_value)
        result["principal_soil_type"] = principal.capitalize()
        return result

    if principal in ("SILT", "GRAVEL"):
        result = _not_classified(
            f"{principal.capitalize()} has no typical-parameter bucket defined yet (Fill/Clay/Sand only, this pass)"
        )
        result["principal_soil_type"] = principal.capitalize()
        return result

    result = _not_classified("no recognisable principal soil type (SAND/CLAY/SILT/GRAVEL/FILL) found in the description")
    result["principal_soil_type"] = None
    return result
