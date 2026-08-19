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
