"""Unit tests for the rock typical-parameter table lookup
(app/rock_parameters/lookup.py): resolving a bucket_id to both reference
tables' rows, keeping design_table and hoek_brown_table independent
(never merged), and surfacing every field generically - including
whichever ones happen to carry a *_source_note (currently one per
table, both on shale_class_5, deliberately checked without hardcoding
which field that turns out to be)."""

from app.rock_parameters.lookup import get_design_bucket, get_hoek_brown_bucket, lookup_rock_parameters


def test_get_bucket_known_id():
    assert get_design_bucket("sandstone_class_1")["geological_unit"] == "Sandstone"
    assert get_hoek_brown_bucket("sandstone_class_1")["label"] == "SST-1"


def test_get_bucket_unknown_id_returns_none():
    assert get_design_bucket("not_a_real_bucket") is None
    assert get_hoek_brown_bucket("not_a_real_bucket") is None


def test_lookup_unknown_bucket_returns_none():
    assert lookup_rock_parameters("not_a_real_bucket") is None


def test_lookup_returns_both_tables_independently():
    result = lookup_rock_parameters("sandstone_class_3")
    assert result["bucket_id"] == "sandstone_class_3"
    assert result["geological_unit"] == "Sandstone"

    design = result["design_table"]
    hb = result["hoek_brown_table"]
    assert design["label"] == "Class III"
    assert hb["label"] == "SST-3"
    # Genuinely different parameter sets for the same class - not merged,
    # not one derived from the other.
    assert "E_prime_MPa" in design["fields"]
    assert "E_prime_MPa" not in hb["fields"]
    assert "Emass_MPa" in hb["fields"]
    assert "Emass_MPa" not in design["fields"]
    assert design["fields"]["E_prime_MPa"]["value"] != hb["fields"]["Emass_MPa"]["value"]


def test_all_ten_buckets_resolve_in_both_tables():
    bucket_ids = [f"{rock}_class_{n}" for rock in ("sandstone", "shale") for n in range(1, 6)]
    assert len(bucket_ids) == 10
    for bucket_id in bucket_ids:
        result = lookup_rock_parameters(bucket_id)
        assert result is not None, bucket_id
        assert result["design_table"] is not None, bucket_id
        assert result["hoek_brown_table"] is not None, bucket_id


def test_source_notes_surfaced_generically_on_both_tables():
    """Scans both tables for any *_source_note field, the same way
    soil_parameters/lookup.py's equivalent test does - not hardcoded to
    "shale_class_5"/"E_prime_MPa" specifically, so this keeps working if
    the source discrepancy gets resolved and the notes move or
    disappear."""
    from app.rock_parameters.lookup import _DESIGN_BUCKETS_BY_ID, _HOEK_BROWN_BUCKETS_BY_ID

    found_any = False
    for buckets_by_id, table_key in (
        (_DESIGN_BUCKETS_BY_ID, "design_table"),
        (_HOEK_BROWN_BUCKETS_BY_ID, "hoek_brown_table"),
    ):
        for bucket_id, raw_bucket in buckets_by_id.items():
            note_fields = [k[: -len("_source_note")] for k in raw_bucket if k.endswith("_source_note")]
            for field_name in note_fields:
                found_any = True
                result = lookup_rock_parameters(bucket_id)
                assert "source_note" in result[table_key]["fields"][field_name], (table_key, bucket_id, field_name)
                assert (
                    result[table_key]["fields"][field_name]["source_note"]
                    == raw_bucket[field_name + "_source_note"]
                )
    assert found_any, "expected at least one *_source_note field across both tables"


def test_fields_without_a_source_note_dont_get_one():
    result = lookup_rock_parameters("sandstone_class_1")
    assert "source_note" not in result["design_table"]["fields"]["E_prime_MPa"]
    assert "source_note" not in result["hoek_brown_table"]["fields"]["Emass_MPa"]


def test_classification_bucket_id_matches_lookup_bucket_id():
    """The join key classify_rock_stratum() produces must actually exist
    in both tables - checked directly rather than assumed, since a
    naming mismatch here would silently return parameters: null for
    every classified stratum."""
    from app.rock_parameters.classification import classify_rock_stratum

    for rock_type, ucs in [("SANDSTONE", 30), ("SHALE", 20)]:
        stratum = {"text": f"{rock_type}: grey.", "depth_from_m": 5.0}
        readings = [{"type": "ucs", "value_mpa": ucs, "depth_m": 5.1}]
        classification = classify_rock_stratum(stratum, 6.0, readings, [])
        assert classification["classified"] is True
        assert lookup_rock_parameters(classification["bucket_id"]) is not None
