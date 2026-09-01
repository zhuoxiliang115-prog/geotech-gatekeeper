"""Unit tests for the typical-parameter table lookup
(app/soil_parameters/lookup.py): resolving a bucket_id to its reference
row, surfacing every field (including whichever ones happen to carry a
*_source_note - currently clay_very_soft.gamma_kNm3 and
sand_dense.poissons_ratio, but the test checks this generically rather
than hardcoding those two), and the Stage-1 measured-value override
(always unused in production today - see lookup.py's module docstring -
but exercised directly here since it's real, callable logic)."""

from app.soil_parameters.lookup import get_bucket, lookup_parameters


def test_get_bucket_known_id():
    bucket = get_bucket("clay_stiff")
    assert bucket["geological_unit"] == "Clay"
    assert bucket["label"] == "Stiff"


def test_get_bucket_unknown_id_returns_none():
    assert get_bucket("not_a_real_bucket") is None


def test_lookup_parameters_unknown_bucket_returns_none():
    assert lookup_parameters("not_a_real_bucket") is None


def test_lookup_parameters_basic_shape_and_units():
    result = lookup_parameters("sand_medium_dense")
    assert result["bucket_id"] == "sand_medium_dense"
    assert result["geological_unit"] == "Sand"
    assert result["label"] == "Medium dense"
    assert result["table_source"]

    fields = result["fields"]
    assert fields["phi_prime_deg"] == {"value": 35, "unit": "degrees", "source": "typical"}
    assert fields["gamma_kNm3"]["unit"] == "kN/m3"
    # calculated fields (K0/Kp/reduced_*) carried over as-is, no unit defined
    assert fields["K0"]["unit"] is None
    assert "source_note" not in fields["K0"]


def test_lookup_parameters_all_fourteen_buckets_resolve():
    bucket_ids = [
        "fill_uncompacted_cohesive", "fill_uncompacted_non_cohesive", "fill_well_compacted",
        "clay_very_soft", "clay_soft", "clay_firm", "clay_stiff", "clay_very_stiff", "clay_hard",
        "sand_very_loose", "sand_loose", "sand_medium_dense", "sand_dense", "sand_very_dense",
    ]
    assert len(bucket_ids) == 14
    for bucket_id in bucket_ids:
        result = lookup_parameters(bucket_id)
        assert result is not None, bucket_id
        assert result["fields"], bucket_id


def test_source_note_surfaced_generically_not_hardcoded():
    """Any field with a *_source_note in the reference JSON should carry
    it in the lookup result - checked by scanning every bucket for one,
    rather than hardcoding "clay_very_soft"/"gamma_kNm3" into the test, so
    this keeps working if the provisional values get corrected and the
    notes move (or disappear) later."""
    from app.soil_parameters.lookup import _BUCKETS_BY_ID

    found_any = False
    for bucket_id, raw_bucket in _BUCKETS_BY_ID.items():
        note_fields = [k[: -len("_source_note")] for k in raw_bucket if k.endswith("_source_note")]
        for field_name in note_fields:
            found_any = True
            result = lookup_parameters(bucket_id)
            assert "source_note" in result["fields"][field_name], (bucket_id, field_name)
            assert result["fields"][field_name]["source_note"] == raw_bucket[field_name + "_source_note"]
    assert found_any, "expected at least one *_source_note field in the reference table"


def test_fields_without_a_source_note_dont_get_one():
    result = lookup_parameters("clay_stiff")
    assert "source_note" not in result["fields"]["cu_kPa"]


def test_measured_value_override_replaces_value_and_keeps_typical():
    result = lookup_parameters("clay_stiff", measured_values={"cu_kPa": 73.5})
    field = result["fields"]["cu_kPa"]
    assert field["value"] == 73.5
    assert field["source"] == "measured"
    assert field["typical_value"] == "50-100"
    # untouched fields stay at their typical value
    assert result["fields"]["gamma_kNm3"]["source"] == "typical"


def test_measured_value_of_none_does_not_override():
    result = lookup_parameters("clay_stiff", measured_values={"cu_kPa": None})
    assert result["fields"]["cu_kPa"]["source"] == "typical"


def test_no_measured_values_all_fields_typical():
    result = lookup_parameters("sand_dense")
    for field in result["fields"].values():
        assert field["source"] == "typical"
        assert "typical_value" not in field
