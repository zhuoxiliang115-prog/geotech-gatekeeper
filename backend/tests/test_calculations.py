"""Unit tests for the pure calculation functions in app/calculations.py,
checked against the worked examples and threshold tables in
reference/charts-and-calculations-spec.md."""

from app.calculations import (
    a_line_pi,
    as2159_concrete_class,
    as2159_steel_class,
    ece_salinity,
    grading_curve_cu_cc,
    plasticity_index,
    point_load_is50,
    u_line_pi,
    uscs_fine_grained_zone,
)


def test_plasticity_index_worked_example():
    # spec: "PI = 54 - 20 = 34%"
    assert plasticity_index(54, 20) == 34


def test_point_load_is50_no_correction_at_reference_diameter():
    # De = 50mm is the reference size, so the correction factor is 1
    assert point_load_is50(1.3, 50) == 1.3


def test_point_load_is50_applies_size_correction():
    is50 = point_load_is50(2.0, 63.5)
    assert round(is50, 3) == round(2.0 * (63.5 / 50) ** 0.45, 3)
    assert is50 > 2.0  # a larger-than-reference core corrects upward


# ---------- AS 2159 Table 6.4.2(C): concrete ----------


def test_concrete_class_mild_condition_a():
    # sulfate-in-soil <5,000 -> band 0 -> "Mild" under Condition A
    assert as2159_concrete_class("A", sulfate_soil_ppm=4000) == "Mild"


def test_concrete_class_non_aggressive_condition_b():
    assert as2159_concrete_class("B", sulfate_soil_ppm=4000) == "Non-aggressive"


def test_concrete_class_pH_governs_low_ph_is_more_severe():
    # pH < 4 -> band 3 (most severe), regardless of sulfate being mild
    result = as2159_concrete_class("A", ph=3.5, sulfate_soil_ppm=1000)
    assert result == "Very severe"


def test_concrete_class_governing_parameter_is_the_worst_band():
    # sulfate-in-groundwater 5,000 -> band 2 (3,000-10,000); pH 8 -> band 0
    # governing = max(2, 0) = 2 -> "Severe" under Condition A
    result = as2159_concrete_class("A", ph=8.0, sulfate_gw_ppm=5000)
    assert result == "Severe"


def test_concrete_class_chloride_gw_included():
    # chloride-in-groundwater >30,000 -> band 3, most severe
    result = as2159_concrete_class("B", chloride_gw_ppm=35000)
    assert result == "Severe"


def test_concrete_class_no_data_returns_none():
    assert as2159_concrete_class("A") is None


# ---------- AS 2159 Table 6.5.2(C): steel ----------


def test_steel_class_non_aggressive_condition_a():
    assert as2159_steel_class("A", resistivity_ohm_cm=6000) == "Non-aggressive"


def test_steel_class_resistivity_lower_is_more_severe():
    # resistivity <1,000 -> band 3 -> "Severe" under Condition A
    assert as2159_steel_class("A", resistivity_ohm_cm=800) == "Severe"


def test_steel_class_condition_b_labels_shifted():
    # same band (2, resistivity 1,000-2,000) reads "Mild" under Condition B
    assert as2159_steel_class("B", resistivity_ohm_cm=1500) == "Mild"


def test_steel_class_governing_across_chloride_and_ph():
    # chloride-in-soil 60,000 -> band 3 (most severe); pH 6 -> band 0
    result = as2159_steel_class("A", ph=6.0, chloride_soil_ppm=60000)
    assert result == "Severe"


# ---------- ECe salinity (Richards 1954) ----------


def test_ece_salinity_conversion():
    # EC(1:5) = 90/1000 = 0.09 dS/m; MF=17 (sand) -> ECe = 1.53
    ece, label = ece_salinity(90, 17)
    assert round(ece, 2) == 1.53
    assert label == "Non-saline"


def test_ece_salinity_class_boundaries():
    assert ece_salinity(1000, 1)[1] == "Non-saline"  # ECe=1
    assert ece_salinity(2000, 1)[1] == "Slightly saline"  # ECe=2 (boundary is inclusive-up)
    assert ece_salinity(4000, 1)[1] == "Moderately saline"  # ECe=4
    assert ece_salinity(8000, 1)[1] == "Very saline"  # ECe=8
    assert ece_salinity(16000, 1)[1] == "Highly saline"  # ECe=16


def test_ece_salinity_highly_saline():
    ece, label = ece_salinity(3000, 8)
    assert ece == 24.0
    assert label == "Highly saline"


# ---------- AS1726 A-line / U-line / USCS zone (borehole log standard §3.11) ----------


def test_a_line_pi_matches_atterberg_chart_formula():
    # frontend/src/components/AtterbergChart.jsx: PI = 0.73 * (LL - 20)
    assert a_line_pi(40) == 0.73 * (40 - 20)


def test_u_line_pi_matches_atterberg_chart_formula():
    assert u_line_pi(40) == 0.9 * (40 - 8)


def test_uscs_zone_cl_ml_borderline():
    assert uscs_fine_grained_zone(30, 5) == "CL-ML"


def test_uscs_zone_above_a_line_low_ll():
    # LL=30, A-line PI at LL=30 is 0.73*10=7.3; PI=15 is above it, LL<35
    assert uscs_fine_grained_zone(30, 15) == "CL or OL"


def test_uscs_zone_above_a_line_intermediate_ll():
    assert uscs_fine_grained_zone(45, 25) == "CI or OI"


def test_uscs_zone_above_a_line_high_ll():
    assert uscs_fine_grained_zone(63, 37) == "CH or OH"


def test_uscs_zone_below_a_line_low_ll():
    assert uscs_fine_grained_zone(34, 3) == "ML or OL"


def test_uscs_zone_below_a_line_high_ll():
    assert uscs_fine_grained_zone(60, 9) == "MH or OH"


# ---------- Grading curve Cu/Cc ----------


def test_grading_curve_cu_cc_well_graded_sand():
    readings = [
        {"sieve_mm": 19.0, "passing_pct": 100},
        {"sieve_mm": 9.5, "passing_pct": 90},
        {"sieve_mm": 4.75, "passing_pct": 70},
        {"sieve_mm": 2.36, "passing_pct": 50},
        {"sieve_mm": 1.18, "passing_pct": 30},
        {"sieve_mm": 0.6, "passing_pct": 15},
        {"sieve_mm": 0.3, "passing_pct": 8},
        {"sieve_mm": 0.15, "passing_pct": 3},
        {"sieve_mm": 0.075, "passing_pct": 1},
    ]
    result = grading_curve_cu_cc(readings)
    assert result is not None
    assert result["cu"] > 6  # well-graded sand criterion
    assert 1 <= result["cc"] <= 3


def test_grading_curve_cu_cc_returns_none_when_out_of_range():
    # every reading passes >10%, so D10 can't be interpolated
    readings = [
        {"sieve_mm": 19.0, "passing_pct": 100},
        {"sieve_mm": 9.5, "passing_pct": 80},
        {"sieve_mm": 4.75, "passing_pct": 50},
    ]
    assert grading_curve_cu_cc(readings) is None
