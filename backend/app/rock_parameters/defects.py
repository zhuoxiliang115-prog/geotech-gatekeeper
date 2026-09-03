"""Stage 3b prep: defect-spacing derivation from borehole_log.py's
structured defect_entries, feeding the Sydney Classification System
(Pells et al. 1998, via Bertuzzi 2019) - Class I-V for Sandstone/Shale
needs UCS, defect spacing, and allowable-seam % all satisfied together.
This module handles spacing only; seam-% is still deferred (see the
classification module's own docstring once that exists).

Deliberately returns raw components (which defects were natural vs
excluded, every stated spacing, every computed gap) rather than one
collapsed "the spacing" number - a candidate interval can carry both a
generalised defect set's own stated spacing AND individually-logged
defects needing a computed gap, and deciding how those combine into one
governing value for the Class I-V lookup is a classification-design
call, not something to bake in silently here.
"""

import re

from ..borehole_review.rules import VALID_DEFECT_TYPES

# "Break[s] in rock mass not caused by natural effects" (AECOM standard
# §3.15) - drilling/handling artifacts, not real rock-mass discontinuities.
# Excluded from spacing: counting them would inflate defect density and
# understate the natural defect spacing the Sydney Classification
# System's spacing criterion is actually about.
DRILLING_ARTIFACT_TYPES = {"MB", "DL", "DB", "HB"}

# Every other defect type in rules.py's VALID_DEFECT_TYPES - real
# geological discontinuities. Derived from VALID_DEFECT_TYPES rather than
# listed by hand, so the two sets can't silently drift apart if a type is
# ever added there.
NATURAL_DEFECT_TYPES = VALID_DEFECT_TYPES - DRILLING_ARTIFACT_TYPES

# A "generalised defect set" (the AECOM standard's own convention for
# grouping similar defects) states its spacing directly in the
# description, e.g. "...80 mm spacing, x 5" - real corpus data shows
# roughly 1 in 8 natural-defect entries carries one of these. Anchored on
# the literal word "spacing" (not just "NN mm" anywhere in the text) so
# it can't be confused with an aperture value printed earlier in the
# same entry, e.g. "5 mm aperture, up to 80 mm spacing" - only "80 mm
# spacing" is a spacing value.
_STATED_SPACING_RE = re.compile(r"(\d+)\s*(?:-\s*(\d+))?\s*(?:mm)?\s*spacing", re.IGNORECASE)


def _stated_spacing_mm(text):
    m = _STATED_SPACING_RE.search(text)
    if not m:
        return None
    lo = int(m.group(1))
    hi = int(m.group(2)) if m.group(2) else lo
    return (lo, hi)


def compute_defect_spacing(defect_entries: list, depth_from_m: float, depth_to_m: float) -> dict:
    """Given one page's defect_entries (borehole_log.py's
    _extract_defect_entries) and a candidate depth window
    [depth_from_m, depth_to_m), returns the raw evidence for defect
    spacing within it:

        {
            "natural_defects": [...],           # in-window, natural type
            "artifact_count_excluded": int,     # MB/DL/DB/HB, excluded
            "unrecognised_types": [str, ...],   # a genuinely unknown code - excluded, flagged
            "stated_spacings_mm": [(lo, hi), ...],
            "computed_gaps_mm": [int, ...],
        }

    stated_spacings_mm comes from generalised-set entries that print
    their own spacing - authoritative for that entry, not recomputed.
    computed_gaps_mm is the depth gap (mm) between consecutive natural
    defects that have no stated spacing of their own, sorted by depth.
    Neither list is reduced to a single number - see the module
    docstring for why.
    """
    window = [e for e in defect_entries if depth_from_m <= e["depth_from_m"] < depth_to_m]

    natural = [e for e in window if e["type"] in NATURAL_DEFECT_TYPES]
    artifact_count = sum(1 for e in window if e["type"] in DRILLING_ARTIFACT_TYPES)
    unrecognised = sorted(
        {
            e["type"]
            for e in window
            if e["type"] is not None
            and e["type"] not in NATURAL_DEFECT_TYPES
            and e["type"] not in DRILLING_ARTIFACT_TYPES
        }
    )

    stated_spacings_mm = []
    diffable_depths = []
    for e in natural:
        stated = _stated_spacing_mm(e["text"])
        if stated is not None:
            stated_spacings_mm.append(stated)
        else:
            diffable_depths.append(e["depth_from_m"])

    diffable_depths.sort()
    computed_gaps_mm = [
        round((diffable_depths[i + 1] - diffable_depths[i]) * 1000) for i in range(len(diffable_depths) - 1)
    ]

    return {
        "natural_defects": natural,
        "artifact_count_excluded": artifact_count,
        "unrecognised_types": unrecognised,
        "stated_spacings_mm": stated_spacings_mm,
        "computed_gaps_mm": computed_gaps_mm,
    }
