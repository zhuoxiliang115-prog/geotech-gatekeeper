"""Stage 3: resolves a classification.py bucket_id to its typical
design-parameter row from soil_typical_parameters.json.

Supports substituting a Stage-1 lab-measured value in place of the
table's typical value, per field, when one is available for this
stratum - see lookup_parameters()'s measured_values argument. That
argument is always None/empty today: no parser in this codebase yet
produces per-stratum lab-measured values in the shape this expects
(e.g. cu_kPa from a triaxial/UU test, phi_prime_deg from a direct-shear
test) - Atterberg/PSD/Emerson, the only lab reports parsed so far, don't
carry those fields. The override path is therefore dead code for now,
by design (per explicit instruction) - built ahead of a parser that can
call it, so wiring one up later doesn't mean revisiting this function.
"""

import json
from pathlib import Path

_DATA_PATH = Path(__file__).parent / "data" / "soil_typical_parameters.json"

with _DATA_PATH.open("r", encoding="utf-8") as _f:
    _TABLE = json.load(_f)["soil_typical_parameters"]

_UNITS = _TABLE["units"]
_BUCKETS_BY_ID = {bucket["bucket_id"]: bucket for bucket in _TABLE["buckets"]}

_METADATA_KEYS = {"bucket_id", "geological_unit", "label", "classification_key"}
_SOURCE_NOTE_SUFFIX = "_source_note"


def get_bucket(bucket_id: str) -> dict | None:
    return _BUCKETS_BY_ID.get(bucket_id)


def lookup_parameters(bucket_id: str, measured_values: dict | None = None) -> dict | None:
    """Returns the typical-parameter row for bucket_id as
    {bucket_id, geological_unit, label, classification_key, table_source,
    fields: {field_name: {value, unit, source, source_note?, typical_value?}}}
    or None if bucket_id isn't in the reference table.

    Every field the reference row carries is included - not a hardcoded
    subset - so a *_source_note (today just two: clay_very_soft.gamma_kNm3
    and sand_dense.poissons_ratio, both provisional placeholders for a
    source-workbook value that looked like a typo) is surfaced for
    whichever field actually has one, without this function needing to
    know in advance which fields those are.

    measured_values, when given, maps field name -> lab-measured value;
    a present, non-None entry replaces that field's "value" (source
    becomes "measured", and the table's typical value is kept alongside
    as "typical_value" for comparison). This is a straight substitution,
    not a recompute - overriding phi_prime_deg or c_prime_kPa does NOT
    recompute the table's derived K0/Kp/reduced_phi_deg/reduced_c_kPa,
    which stay at their typical-row values. Revisit that if/when a real
    override path exists; it doesn't yet (see module docstring).
    """
    bucket = _BUCKETS_BY_ID.get(bucket_id)
    if bucket is None:
        return None

    measured_values = measured_values or {}
    fields = {}
    for key, value in bucket.items():
        if key in _METADATA_KEYS or key.endswith(_SOURCE_NOTE_SUFFIX):
            continue

        field = {"value": value, "unit": _UNITS.get(key), "source": "typical"}

        measured = measured_values.get(key)
        if measured is not None:
            field["value"] = measured
            field["source"] = "measured"
            field["typical_value"] = value

        note = bucket.get(key + _SOURCE_NOTE_SUFFIX)
        if note is not None:
            field["source_note"] = note

        fields[key] = field

    return {
        "bucket_id": bucket_id,
        "geological_unit": bucket.get("geological_unit"),
        "label": bucket.get("label"),
        "classification_key": bucket.get("classification_key"),
        "table_source": _TABLE.get("source"),
        "fields": fields,
    }
