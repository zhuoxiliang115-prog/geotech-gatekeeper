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

# Every rock-name word actually observed in the reference corpus (see
# Stage 3b's earlier investigation), not just Sandstone/Shale - so a
# Claystone/Siltstone/etc. stratum gets a specific "recognised, but no
# Table 9.1 bucket for it" flag instead of falling into the generic
# "nothing recognisable" one, mirroring how Silt/Gravel are handled in
# soil_parameters/classification.py.
_ROCK_TYPE_RE = re.compile(
    r"\b(SANDSTONE|SHALE|CLAYSTONE|SILTSTONE|CONGLOMERATE|LAMINITE|MUDSTONE|BRECCIA|LIMESTONE|COAL|TUFF|BASALT)\b"
)

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

# UCS ~ 20 x Is(50) - not an independently-sourced conversion factor, but
# the exact multiplier printed on the logs' own INFERRED STRENGTH column
# legend ("20 x Is(50)"), i.e. the convention the logger already used to
# plot Is(50) points on the same strength scale as direct UCS tests. No
# rock-type-specific variant - nothing available supports differentiating
# Sandstone vs Shale here (per explicit instruction), so it's applied
# uniformly. This is a real, material estimate, not a rounding
# convenience: Bertuzzi 2019's Table 9.3 (a real Sydney tunnelling
# drill-hole database, 1000+ tests per class in places) shows Is(50)
# ranges overlapping almost completely across all five classes for both
# rock types - an Is(50)-derived class is genuinely indicative, not a
# soft caveat on an otherwise-solid number. See STRENGTH_SOURCE_DIRECT_UCS
# / STRENGTH_SOURCE_IS50_ESTIMATED and classify_rock_stratum's "strength"
# output field, which exists specifically so this distinction is never
# buried in a routine note.
IS50_TO_UCS_MULTIPLIER = 20

STRENGTH_SOURCE_DIRECT_UCS = "direct_ucs"
STRENGTH_SOURCE_IS50_ESTIMATED = "is50_estimated"


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


def _resolve_strength(point_load_ucs_readings: list, depth_from: float, depth_to: float):
    """Finds the UCS value to classify against Table 9.1 within this
    window: a direct UCS reading always wins when one exists (real data,
    never estimated); otherwise the nearest Is(50) reading (axial or
    diametral - the log's own "20 x Is(50)" legend doesn't distinguish
    them either) is converted via IS50_TO_UCS_MULTIPLIER. Returns None if
    the window has no strength reading of either kind.

    Returns {"ucs_mpa": float, "source": STRENGTH_SOURCE_*,
    "is50_mpa": float|None} - is50_mpa is only set (and only meaningful)
    when source is STRENGTH_SOURCE_IS50_ESTIMATED, so the raw reading an
    engineer would need to re-derive with a different factor is always
    available, not just the converted number."""
    in_window = [
        r for r in point_load_ucs_readings if r.get("depth_m") is not None and depth_from <= r["depth_m"] < depth_to
    ]

    ucs_candidates = [r for r in in_window if r["type"] == "ucs"]
    if ucs_candidates:
        nearest = min(ucs_candidates, key=lambda r: abs(r["depth_m"] - depth_from))
        return {"ucs_mpa": nearest["value_mpa"], "source": STRENGTH_SOURCE_DIRECT_UCS, "is50_mpa": None}

    is50_candidates = [r for r in in_window if r["type"].startswith("point_load_is50")]
    if is50_candidates:
        nearest = min(is50_candidates, key=lambda r: abs(r["depth_m"] - depth_from))
        is50_mpa = nearest["value_mpa"]
        return {
            "ucs_mpa": round(is50_mpa * IS50_TO_UCS_MULTIPLIER, 2),
            "source": STRENGTH_SOURCE_IS50_ESTIMATED,
            "is50_mpa": is50_mpa,
        }

    return None


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

    A direct UCS reading in this window always wins when one exists.
    Otherwise the nearest Is(50) reading is converted via
    IS50_TO_UCS_MULTIPLIER (see its docstring) - a real, material
    estimate, not a routine caveat, so classification_basis says so
    explicitly and the returned "strength" field always carries both the
    raw Is(50) value and an explicit confidence marker alongside the
    estimated UCS, never just the converted number.
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

    strength = None
    if depth_from is not None and depth_to is not None:
        strength = _resolve_strength(point_load_ucs_readings, depth_from, depth_to)

    if strength is None:
        result = _not_classified("no UCS or Is(50) reading nearby to classify against Table 9.1.")
        result["rock_type"] = rock_type
        return result

    ucs_mpa = strength["ucs_mpa"]
    is_estimated = strength["source"] == STRENGTH_SOURCE_IS50_ESTIMATED
    strength["confidence"] = "low" if is_estimated else "high"

    def _ucs_description(class_number=None):
        class_suffix = f" (Class {_ROMAN[class_number]})" if class_number is not None else ""
        if is_estimated:
            return (
                f"estimated from Is(50)={strength['is50_mpa']} MPa via UCS ~ {IS50_TO_UCS_MULTIPLIER}x Is50 "
                f"(={ucs_mpa} MPa, not a direct UCS test) - indicative only{class_suffix}"
            )
        return f"UCS={ucs_mpa} MPa{class_suffix}"

    ucs_class, ucs_tied_with = _ucs_implied_class(rock_type, ucs_mpa)
    if ucs_class is None:
        floor = _SHALE_UCS_TIE_FLOOR if rock_type == "Shale" else 1
        result = _not_classified(
            f"{_ucs_description()} is below Table 9.1's lowest defined class threshold for {rock_type} "
            f"(Class V requires UCS>{floor} MPa) - not classified, verify against Table 9.1."
        )
        result["rock_type"] = rock_type
        return result

    warnings = []
    if is_estimated:
        warnings.append(
            f"strength is estimated from Is(50)={strength['is50_mpa']} MPa via UCS ~ "
            f"{IS50_TO_UCS_MULTIPLIER}x Is50, not a direct UCS test - Bertuzzi 2019's own drill-hole "
            "database shows Is(50) ranges overlapping heavily across classes, so treat this class as "
            "indicative only, not equivalent to a direct-UCS classification."
        )

    spacing_data = compute_defect_spacing(defect_entries, depth_from, depth_to)
    governing_spacing_mm = _governing_spacing_mm(spacing_data)

    if governing_spacing_mm is not None:
        spacing_class = _spacing_implied_class(rock_type, governing_spacing_mm)
        final_class = max(ucs_class, spacing_class)
        basis = (
            f"{_ucs_description(ucs_class)} + defect spacing={governing_spacing_mm} mm "
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
        basis = f"{_ucs_description(ucs_class)} only - spacing not assessed (insufficient defect data in this interval)"
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
    result["strength"] = strength
    return result
