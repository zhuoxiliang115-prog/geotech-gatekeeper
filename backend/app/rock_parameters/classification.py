"""Stage 3b: Sandstone/Shale Class I-V classification per Table 9.1 of
the Sydney Classification System (Pells, Mostyn & Walker 1998, "Foundations
on Sandstone and Shale in the Sydney Region", as summarised in Bertuzzi
2019 "Estimating Rock Mass Properties"). Rules-only - no LLM judgment
step, same convention as soil_parameters/classification.py.

Class needs three factors satisfied together: UCS, defect spacing, and
allowable-seam % (clay-filled/fragmented/highly-weathered zones as a
percentage of the interval). Seam % is NOT computed here - the source
material itself warns judging which defects count as "seams" and what
fraction of the interval they affect is easy to get wrong, so this stays
a flag for manual review (per explicit instruction) rather than a real
number: any seam-type defect nearby sets a provisional-verification
warning, classification proceeds on UCS + spacing regardless.

Table 9.1 thresholds below are transcribed verbatim from the user's own
spec, not independently re-derived or re-verified against Bertuzzi 2019
directly (that PDF was in the chat sandbox, not this repo - see
reference/sydney-classification-system.md, once that exists, for the
citable source instead of this docstring).
"""

import re

from .defects import compute_defect_spacing

_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}

_ROCK_TYPE_RE = re.compile(r"\b(SANDSTONE|SHALE)\b")

# Table 9.1 - "UCS > threshold (MPa)" per class, descending, first match
# wins. Class V's floor (UCS>1) is the lowest the table defines; UCS at
# or below it is below Table 9.1 entirely, not Class V by default.
#
# Shale's Class IV and Class V share the same UCS floor (UCS>1) - UCS
# alone cannot distinguish them for Shale (unlike Sandstone, where every
# class has a distinct UCS floor: 24/12/7/2/1). This isn't treated as a
# transcription slip: it reads as the table's own design - once Shale's
# UCS drops into that shared low band, spacing is Table 9.1's intended
# tiebreaker, not UCS. Handled explicitly wherever it's hit (see
# _ucs_implied_class), not silently resolved to one or the other.
_SANDSTONE_UCS_BANDS = [(1, 24), (2, 12), (3, 7), (4, 2), (5, 1)]
_SHALE_UCS_BANDS = [(1, 16), (2, 7), (3, 2)]
_SHALE_UCS_TIE_FLOOR = 1  # Class IV and Class V both require UCS > this

# Table 9.1 - "defect spacing > threshold (mm)" per class, descending.
# Sandstone's Class I and Class II share the same spacing floor (>600mm) -
# the mirror image of Shale's UCS tie above (UCS, not spacing, is what
# distinguishes I from II for Sandstone). Since spacing is only ever used
# here alongside a UCS-implied class (never alone), that tie resolves
# naturally through the UCS side and needs no special-casing.
_SANDSTONE_SPACING_BANDS = [(1, 600), (2, 600), (3, 200), (4, 60)]
_SHALE_SPACING_BANDS = [(1, 600), (2, 200), (3, 60), (4, 20)]

# "...Seam" defect types (Crushed/Sheared/Infilled/Extremely-weathered
# Seam, per the AECOM standard's own §3.15 naming) plus any defect -
# regardless of type - whose infill/coating text indicates clay, are
# treated as seam content worth flagging. This is a deliberately
# inclusive heuristic (false positives just mean an unnecessary manual
# check; false negatives mean a real seam gets missed) - not a percentage
# computation, which is explicitly deferred.
_SEAM_TYPE_CODES = {"CS", "SS", "IS", "EW"}
_CLAY_INFILL_RE = re.compile(r"\bCT\b|\bclay\b", re.IGNORECASE)


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


def _find_rock_type(text: str):
    m = _ROCK_TYPE_RE.search(text)
    return m.group(1).capitalize() if m else None


def _ucs_implied_class(rock_type: str, ucs_mpa: float):
    """Returns (class_number, tied_with_class_number). tied_with is only
    ever set for Shale UCS in Class IV/V's shared band - see the module
    docstring."""
    if rock_type == "Sandstone":
        for cls, floor in _SANDSTONE_UCS_BANDS:
            if ucs_mpa > floor:
                return cls, None
        return None, None
    if rock_type == "Shale":
        for cls, floor in _SHALE_UCS_BANDS:
            if ucs_mpa > floor:
                return cls, None
        if ucs_mpa > _SHALE_UCS_TIE_FLOOR:
            return 4, 5
        return None, None
    return None, None


def _spacing_implied_class(rock_type: str, spacing_mm: float):
    bands = _SANDSTONE_SPACING_BANDS if rock_type == "Sandstone" else _SHALE_SPACING_BANDS
    for cls, floor in bands:
        if spacing_mm > floor:
            return cls
    return 5


def _governing_spacing_mm(spacing_data: dict):
    """Stated spacing wins over computed gaps when a window has both -
    it's the log's own direct declaration for that defect set, more
    authoritative than an inferred gap between unrelated entries (per
    explicit instruction). Within whichever source wins, the minimum
    (most conservative - the closest-spaced defect governs the interval's
    behaviour) is the governing value; a stated range's low end is used
    for the same reason. Returns None when neither source has anything."""
    if spacing_data["stated_spacings_mm"]:
        return min(lo for lo, _hi in spacing_data["stated_spacings_mm"])
    if spacing_data["computed_gaps_mm"]:
        return min(spacing_data["computed_gaps_mm"])
    return None


def _has_seam_content(natural_defects: list):
    for e in natural_defects:
        if e["type"] in _SEAM_TYPE_CODES:
            return True
        if _CLAY_INFILL_RE.search(e.get("text") or ""):
            return True
    return False


def classify_rock_stratum(
    stratum: dict, next_stratum_depth_m, point_load_ucs_readings: list, defect_entries: list
) -> dict:
    """Classifies one Cored Borehole stratum into a Class I-V bucket per
    Table 9.1, or explains why it can't be. Returns:
        {"rock_type": "Sandstone"|"Shale"|str|None,
         "classified": bool, "bucket_id": str|None, "flag": str|None,
         "classification_basis": str|None, "warnings": [str, ...]}

    next_stratum_depth_m bounds the candidate interval (this stratum's
    own depth to the next stratum's, or open-ended for the last stratum
    on a page) - the same window convention already used for
    _attach_readings_to_strata and compute_defect_spacing, so UCS
    readings, defect spacing, and seam content are all evaluated over the
    identical span of the borehole.

    point_load_ucs_readings and defect_entries are the page's full lists
    (not pre-scoped to this stratum) - both get windowed here, the same
    "caller passes the page's list, this function does the matching"
    convention soil_parameters/classification.py already uses for
    field_test_entries.

    UCS only ever comes from a direct type=="ucs" reading in this
    window - an Is(50) reading alone does not satisfy the strength gate.
    AS1726-2017's own Is(50)->UCS multiplier is explicitly not fixed (it
    "varies widely by rock type" per the AECOM standard), so converting
    one to compare against Table 9.1's UCS-denominated thresholds isn't
    done here; a stratum with only a nearby Is(50) reading is flagged
    with that distinction rather than silently converted or lumped in
    with "nothing nearby at all".
    """
    text = stratum.get("text", "") or ""
    rock_type = _find_rock_type(text)

    if rock_type not in ("Sandstone", "Shale"):
        if rock_type is None:
            result = _not_classified("no recognisable rock type (SANDSTONE/SHALE) found in the description")
        else:
            result = _not_classified(
                f"{rock_type} has no Table 9.1 classification defined (Sandstone/Shale only, this pass)"
            )
        result["rock_type"] = rock_type
        return result

    depth_from = stratum.get("depth_from_m")
    depth_to = next_stratum_depth_m if next_stratum_depth_m is not None else None
    if depth_from is not None and depth_to is None:
        depth_to = depth_from + 1000  # last stratum on a page - effectively open-ended

    ucs_reading = None
    is50_nearby = False
    if depth_from is not None and depth_to is not None:
        in_window = [
            r for r in point_load_ucs_readings if r.get("depth_m") is not None and depth_from <= r["depth_m"] < depth_to
        ]
        ucs_candidates = [r for r in in_window if r["type"] == "ucs"]
        if ucs_candidates:
            ucs_reading = min(ucs_candidates, key=lambda r: abs(r["depth_m"] - depth_from))
        is50_nearby = any(r["type"].startswith("point_load_is50") for r in in_window)

    if ucs_reading is None:
        if is50_nearby:
            reason = (
                "an Is(50) reading is nearby but no direct UCS reading - Is(50)->UCS conversion isn't "
                "reliable enough (the multiplier varies by rock type per AS1726-2017) to classify against "
                "Table 9.1 from it; not classified, verify against Table 9.1 manually"
            )
        else:
            reason = "no strength reading nearby to classify against Table 9.1."
        result = _not_classified(reason)
        result["rock_type"] = rock_type
        return result

    ucs_mpa = ucs_reading["value_mpa"]
    ucs_class, ucs_tied_with = _ucs_implied_class(rock_type, ucs_mpa)
    if ucs_class is None:
        result = _not_classified(
            f"UCS={ucs_mpa} MPa is below Table 9.1's lowest defined class threshold for {rock_type} "
            f"(Class V requires UCS>{_SHALE_UCS_TIE_FLOOR if rock_type == 'Shale' else 1} MPa) - "
            "not classified, verify against Table 9.1."
        )
        result["rock_type"] = rock_type
        return result

    spacing_data = compute_defect_spacing(defect_entries, depth_from, depth_to)
    governing_spacing_mm = _governing_spacing_mm(spacing_data)
    warnings = []

    if governing_spacing_mm is not None:
        spacing_class = _spacing_implied_class(rock_type, governing_spacing_mm)
        final_class = max(ucs_class, spacing_class)
        basis = (
            f"UCS={ucs_mpa} MPa (Class {_ROMAN[ucs_class]}) + defect spacing={governing_spacing_mm} mm "
            f"(Class {_ROMAN[spacing_class]}) -> Class {_ROMAN[final_class]} (more conservative of the two, "
            "per Table 9.1)"
        )
        if abs(ucs_class - spacing_class) > 1:
            warnings.append(
                f"UCS implies Class {_ROMAN[ucs_class]}, defect spacing implies Class {_ROMAN[spacing_class]} "
                "- differ by more than one class, worth checking"
            )
    else:
        final_class = ucs_class
        basis = (
            f"UCS={ucs_mpa} MPa (Class {_ROMAN[ucs_class]}) only - spacing not assessed "
            "(insufficient defect data in this interval)"
        )
        warnings.append(
            "spacing not assessed (insufficient defect data in this interval) - verify against Table 9.1."
        )

    if ucs_tied_with is not None and final_class == ucs_class:
        warnings.append(
            f"UCS={ucs_mpa} MPa sits on a shared Table 9.1 threshold for {rock_type} (Class "
            f"{_ROMAN[ucs_class]}/{_ROMAN[ucs_tied_with]} both require UCS>{_SHALE_UCS_TIE_FLOOR} MPa) - "
            "defect spacing is Table 9.1's own tiebreaker for this case; verify against Table 9.1 if "
            "spacing wasn't assessed above."
        )

    if _has_seam_content(spacing_data["natural_defects"]):
        warnings.append(
            "seam content present, allowable-seam percentage not computed - verify against Table 9.1."
        )

    bucket_id = f"{rock_type.lower()}_class_{final_class}"
    result = _classified(bucket_id, basis, warnings)
    result["rock_type"] = rock_type
    return result
