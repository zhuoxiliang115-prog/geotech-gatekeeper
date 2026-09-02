"""Stage 3b: resolves a classify_rock_stratum() bucket_id to its typical
design-parameter rows from rock_typical_parameters.json.

Two independent reference tables, kept separate rather than merged into
one row - design_table and hoek_brown_table are two different parameter
sets for the same class labels (shared bucket_id), not interchangeable.
The source workbook itself disagrees between them for shale_class_5's
modulus (design_table's E_prime_MPa=50 vs hoek_brown_table's
Emass_MPa=100) - not a bug in this lookup, a discrepancy in the source
data, already flagged via *_source_note on both sides so it can't get
lost by averaging or picking one silently.

No Stage-1 lab-measured-value override here (unlike
soil_parameters/lookup.py) - nothing in this feature's scope has asked
for one; soil's was built ahead of a specific, named future need. Add it
if/when there's an actual reason to.
"""

import json
from pathlib import Path

_DATA_PATH = Path(__file__).parent / "data" / "rock_typical_parameters.json"

with _DATA_PATH.open("r", encoding="utf-8") as _f:
    _TABLE = json.load(_f)["rock_typical_parameters"]

_DESIGN_TABLE = _TABLE["design_table"]
_HOEK_BROWN_TABLE = _TABLE["hoek_brown_table"]

_DESIGN_BUCKETS_BY_ID = {b["bucket_id"]: b for b in _DESIGN_TABLE["buckets"]}
_HOEK_BROWN_BUCKETS_BY_ID = {b["bucket_id"]: b for b in _HOEK_BROWN_TABLE["buckets"]}

_METADATA_KEYS = {"bucket_id", "geological_unit", "label"}
_SOURCE_NOTE_SUFFIX = "_source_note"


def _fields_from_bucket(bucket: dict, units: dict) -> dict:
    """Every non-metadata field the bucket carries, generically - not a
    hardcoded subset - so a *_source_note (currently one on each table:
    design_table's shale_class_5.E_prime_MPa, hoek_brown_table's
    shale_class_5.Emass_MPa) is surfaced for whichever field actually has
    one, the same generic approach soil_parameters/lookup.py already
    uses."""
    fields = {}
    for key, value in bucket.items():
        if key in _METADATA_KEYS or key.endswith(_SOURCE_NOTE_SUFFIX):
            continue
        field = {"value": value, "unit": units.get(key)}
        note = bucket.get(key + _SOURCE_NOTE_SUFFIX)
        if note is not None:
            field["source_note"] = note
        fields[key] = field
    return fields


def _table_result(bucket, units: dict, table_source):
    if bucket is None:
        return None
    return {
        "label": bucket.get("label"),
        "table_source": table_source,
        "fields": _fields_from_bucket(bucket, units),
    }


def get_design_bucket(bucket_id: str) -> dict | None:
    return _DESIGN_BUCKETS_BY_ID.get(bucket_id)


def get_hoek_brown_bucket(bucket_id: str) -> dict | None:
    return _HOEK_BROWN_BUCKETS_BY_ID.get(bucket_id)


def lookup_rock_parameters(bucket_id: str) -> dict | None:
    """Returns both reference tables' rows for bucket_id:
        {bucket_id, geological_unit,
         design_table: {label, table_source, fields: {...}} | None,
         hoek_brown_table: {label, table_source, fields: {...}} | None}
    or None if bucket_id is in neither table. In practice a bucket_id
    from classify_rock_stratum() is always in both (verified: the two
    tables' bucket_id sets are identical), but each table result is
    still resolved independently and can be None on its own if that
    ever stops being true, rather than assuming symmetry.
    """
    design_bucket = _DESIGN_BUCKETS_BY_ID.get(bucket_id)
    hb_bucket = _HOEK_BROWN_BUCKETS_BY_ID.get(bucket_id)
    if design_bucket is None and hb_bucket is None:
        return None

    geological_unit = (design_bucket or hb_bucket).get("geological_unit")

    return {
        "bucket_id": bucket_id,
        "geological_unit": geological_unit,
        "design_table": _table_result(design_bucket, _DESIGN_TABLE["units"], _DESIGN_TABLE.get("source")),
        "hoek_brown_table": _table_result(
            hb_bucket, _HOEK_BROWN_TABLE["units"], _HOEK_BROWN_TABLE.get("source")
        ),
    }
