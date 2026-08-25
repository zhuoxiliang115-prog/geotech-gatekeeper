"""Pure calculation functions for geotech lab result interpretation.

No PDF parsing here - these take already-parsed numeric inputs and apply
the formulas/threshold tables from reference/charts-and-calculations-spec.md
(AS 2159-2009 Tables 6.4.2(C)/6.5.2(C), and the Richards 1954 ECe salinity
tables 6.1/6.2). Each function is independently testable against the
spec's worked examples and table boundaries.

Threshold bands below are treated as half-open intervals matching how the
spec's tables read left-to-right (e.g. "5,000-10,000" is [5000, 10000)),
with the lowest/highest bands open-ended at the stated boundary.
"""

import math

# ---------- Plasticity Index ----------


def plasticity_index(ll: float, pl: float) -> float:
    """PI = LL - PL"""
    return ll - pl


# ---------- Point Load size correction (AS 4133.4.1) ----------


def point_load_is50(is_value: float, de: float) -> float:
    """Is50 = Is x (De / 50)^0.45 - corrects Is to a reference 50mm
    equivalent core diameter."""
    return is_value * (de / 50) ** 0.45


# ---------- AS 2159-2009 Table 6.4.2(C): concrete piles in soil ----------

# Each table row's numeric bands, ordered from least to most severe (index
# 0..3), independently per parameter. sulfate_soil/sulfate_gw/chloride_gw
# are in ppm (mg/kg or mg/L); pH is unitless. Note: the phase brief's
# sketch of this function's signature omitted chloride_gw, but the spec's
# Table 6.4.2(C) has it as a fourth governing parameter alongside
# sulfate-in-soil, sulfate-in-groundwater and pH, so it's included here to
# match the table faithfully.
CONCRETE_LABELS = {
    "A": ["Mild", "Moderate", "Severe", "Very severe"],
    "B": ["Non-aggressive", "Mild", "Moderate", "Severe"],
}


def _band_index(value, thresholds, higher_is_worse=True):
    """thresholds is the list of 3 boundaries separating the 4 bands.
    Returns 0..3, the severity index for `value`."""
    if higher_is_worse:
        for i, t in enumerate(thresholds):
            if value < t:
                return i
        return len(thresholds)
    for i, t in enumerate(thresholds):
        if value > t:
            return i
    return len(thresholds)


def as2159_concrete_class(
    soil_condition: str,
    ph: float = None,
    sulfate_soil_ppm: float = None,
    sulfate_gw_ppm: float = None,
    chloride_gw_ppm: float = None,
) -> str:
    """Governing (most severe) exposure classification across whichever
    parameters have data, per AS 2159-2009 Table 6.4.2(C)."""
    band_indices = []
    if sulfate_soil_ppm is not None:
        band_indices.append(_band_index(sulfate_soil_ppm, [5000, 10000, 20000]))
    if sulfate_gw_ppm is not None:
        band_indices.append(_band_index(sulfate_gw_ppm, [1000, 3000, 10000]))
    if ph is not None:
        band_indices.append(_band_index(ph, [5.5, 4.5, 4], higher_is_worse=False))
    if chloride_gw_ppm is not None:
        band_indices.append(_band_index(chloride_gw_ppm, [6000, 12000, 30000]))

    if not band_indices:
        return None

    governing = max(band_indices)
    return CONCRETE_LABELS[soil_condition][governing]


# ---------- AS 2159-2009 Table 6.5.2(C): steel piles in soil ----------

STEEL_LABELS = {
    "A": ["Non-aggressive", "Mild", "Moderate", "Severe"],
    "B": ["Non-aggressive", "Non-aggressive", "Mild", "Moderate"],
}


def as2159_steel_class(
    soil_condition: str,
    ph: float = None,
    chloride_soil_ppm: float = None,
    chloride_gw_ppm: float = None,
    resistivity_ohm_cm: float = None,
) -> str:
    """Governing (most severe) exposure classification across whichever
    parameters have data, per AS 2159-2009 Table 6.5.2(C)."""
    band_indices = []
    if ph is not None:
        band_indices.append(_band_index(ph, [5, 4, 3], higher_is_worse=False))
    if chloride_soil_ppm is not None:
        band_indices.append(_band_index(chloride_soil_ppm, [5000, 20000, 50000]))
    if chloride_gw_ppm is not None:
        band_indices.append(_band_index(chloride_gw_ppm, [1000, 10000, 20000]))
    if resistivity_ohm_cm is not None:
        band_indices.append(_band_index(resistivity_ohm_cm, [5000, 2000, 1000], higher_is_worse=False))

    if not band_indices:
        return None

    governing = max(band_indices)
    return STEEL_LABELS[soil_condition][governing]


# ---------- ECe soil salinity (Richards 1954, Tables 6.1/6.2) ----------

ECE_CLASS_BANDS = [
    (2, "Non-saline"),
    (4, "Slightly saline"),
    (8, "Moderately saline"),
    (16, "Very saline"),
]
ECE_CLASS_ABOVE_TOP_BAND = "Highly saline"


def _ece_class(ece: float) -> str:
    for upper_bound, label in ECE_CLASS_BANDS:
        if ece < upper_bound:
            return label
    return ECE_CLASS_ABOVE_TOP_BAND


def ece_salinity(ec_us_cm: float, mf: float) -> tuple:
    """EC(1:5) [dS/m] = EC [uS/cm] / 1000; ECe [dS/m] = EC(1:5) x MF.
    Returns (ECe, salinity class) per Table 6.2."""
    ec_1_5_ds_m = ec_us_cm / 1000
    ece = ec_1_5_ds_m * mf
    return ece, _ece_class(ece)


# ---------- AS1726 Atterberg A-line / U-line (Modified Casagrande Chart) ----------

# Ported from frontend/src/components/AtterbergChart.jsx (not
# frontend/src/calculations.js - that file doesn't have these constants,
# despite the phase brief naming it) so the borehole-log rule engine and
# the lab-report Atterberg chart agree on the same formula. See
# reference/borehole-log-standard.md §3.11.
A_LINE_SLOPE = 0.73
A_LINE_INTERCEPT = -20  # PI = 0.73 * (LL - 20)
U_LINE_SLOPE = 0.9
U_LINE_INTERCEPT = -8  # PI = 0.9 * (LL - 8)


def a_line_pi(ll: float) -> float:
    """A-line PI at a given Liquid Limit."""
    return A_LINE_SLOPE * (ll + A_LINE_INTERCEPT)


def u_line_pi(ll: float) -> float:
    """U-line PI at a given Liquid Limit - the practical upper bound for
    natural soils (AS1726 note, added in the 28/10/2025 description-sheet
    revision - see the standard doc §3.11)."""
    return U_LINE_SLOPE * (ll + U_LINE_INTERCEPT)


def uscs_fine_grained_zone(ll: float, pi: float) -> str:
    """The fine-grained USCS zone implied by a sample's LL/PI position on
    the Modified Casagrande Chart (reference/borehole-log-standard.md
    §3.11). Organic vs. inorganic (the C/O ambiguity) can't be determined
    from LL/PI alone - AS1726 resolves it from lab/field observation, not
    the chart position - so ambiguous zones return the dual "X or OX" form,
    matching AtterbergChart.jsx's region labels. "CL-ML" is the borderline
    box (LL<=35, 4<=PI<=7)."""
    if ll <= 35 and 4 <= pi <= 7:
        return "CL-ML"
    above_a_line = pi > a_line_pi(ll)
    if above_a_line:
        if ll < 35:
            return "CL or OL"
        if ll < 50:
            return "CI or OI"
        return "CH or OH"
    if ll < 50:
        return "ML or OL"
    return "MH or OH"


# ---------- Grading curve Cu/Cc (AS1726 GW/GP/SW/SP criteria) ----------


def _interpolate_diameter(readings: list, target_pct: float):
    """Log-linear interpolation of particle diameter (mm) at a given
    percent-passing, from a PSD reading list ({sieve_mm, passing_pct}).
    Returns None if target_pct falls outside the tested range."""
    points = sorted(((r["sieve_mm"], r["passing_pct"]) for r in readings), key=lambda p: p[0])
    for (d0, p0), (d1, p1) in zip(points, points[1:]):
        lo, hi = (p0, p1) if p0 <= p1 else (p1, p0)
        if not (lo <= target_pct <= hi):
            continue
        if p1 == p0:
            return d1
        frac = (target_pct - p0) / (p1 - p0)
        log_d = math.log10(d0) + frac * (math.log10(d1) - math.log10(d0))
        return 10**log_d
    return None


def grading_curve_cu_cc(readings: list):
    """Cu = D60/D10, Cc = D30^2/(D10*D60), per AS1726's GW/SW gradation
    criteria (reference/borehole-log-standard.md §3.11). Returns None if
    D10/D30/D60 can't all be interpolated from the given readings (e.g. the
    tested sieve range doesn't reach down to 10% passing)."""
    d10 = _interpolate_diameter(readings, 10)
    d30 = _interpolate_diameter(readings, 30)
    d60 = _interpolate_diameter(readings, 60)
    if not (d10 and d30 and d60):
        return None
    return {
        "d10_mm": d10,
        "d30_mm": d30,
        "d60_mm": d60,
        "cu": d60 / d10,
        "cc": (d30**2) / (d10 * d60),
    }
