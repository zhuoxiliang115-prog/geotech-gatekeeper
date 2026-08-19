"""Parser for chemical Certificate of Analysis (COA) reports: ALS and
Envirolab formats.

Unlike every other report type here, a COA isn't one-sample-per-page - it's
a wide pivot table (one column per sample, one row per analyte) that can
span several pages of one PDF, and the two labs format it differently
(different header layout, different section structure, different
resistivity unit: ALS reports ohm*cm, Envirolab reports ohm*m). That's why
this gets its own whole-PDF extraction logic rather than fitting the
per-page report-title dispatch every other parser uses - dispatch.py
detects the format from the first page and hands the whole pdfplumber.PDF
to the matching function here instead of looping page by page.

Only the fields the calculation engine needs are extracted: pH, Electrical
Conductivity (for ECe salinity), Sulfate, Chloride, Resistivity (for AS
2159 durability classification). Below-detection-limit results (e.g.
"<10") are recorded as a limit-of-reporting bound, not silently treated as
an exact reading.
"""

import re

ALS_SIGNATURE = ("CERTIFICATE OF ANALYSIS", "Work Order")
ENVIROLAB_SIGNATURE = ("Envirolab",)


def detect_format(first_page_text: str):
    if all(marker in first_page_text for marker in ENVIROLAB_SIGNATURE):
        return "envirolab"
    if all(marker in first_page_text for marker in ALS_SIGNATURE):
        return "als"
    return None


def _parse_numeric(raw):
    """Returns (value, below_lor). value is None for missing/non-numeric
    results; below_lor carries the limit-of-reporting bound when the lab
    reported a '<X' below-detection-limit result instead of a value."""
    if raw is None:
        return None, None
    raw = raw.strip()
    if raw in ("", "----", "-", "[NT]", "NT", "NA"):
        return None, None
    if raw.startswith("<"):
        try:
            return None, float(raw[1:])
        except ValueError:
            return None, None
    try:
        return float(raw), None
    except ValueError:
        return None, None


def _add_analyte(sample: dict, key: str, raw: str):
    value, below_lor = _parse_numeric(raw)
    sample[key] = value
    sample[f"{key}_below_lor"] = below_lor


# ---------- ALS ----------

_ALS_ANALYTE_PATTERNS = [
    ("ph", re.compile(r"^pH Value\b")),
    ("ec_us_cm", re.compile(r"^Electrical Conductivity\b")),
    ("moisture_content_pct", re.compile(r"^Moisture Content\b")),
    ("resistivity_ohm_cm", re.compile(r"^Resistivity at 25")),
    ("sulfate_mg_kg", re.compile(r"^Sulfate as SO4\b")),
    ("chloride_mg_kg", re.compile(r"^Chloride\b")),
]


def _als_work_order(first_page_text: str):
    m = re.search(r"Work Order\s*:\s*(\S+)", first_page_text)
    return m.group(1) if m else None


def parse_als_coa(pdf) -> list:
    first_page_text = pdf.pages[0].extract_text() or ""
    work_order = _als_work_order(first_page_text)

    samples = []
    for page_num, page in enumerate(pdf.pages, start=1):
        for table in page.extract_tables():
            date_idx = next(
                (i for i, row in enumerate(table) if row and row[0] == "Sampling date / time"),
                None,
            )
            if date_idx is None or date_idx == 0:
                continue

            sample_id_row = table[date_idx - 1]
            date_row = table[date_idx]
            lab_id_row = table[date_idx + 1] if date_idx + 1 < len(table) else []

            sample_ids = sample_id_row[3:]
            n = len(sample_ids)
            dates = (date_row[3:] + [None] * n)[:n]
            lab_ids = (lab_id_row[3:] + [None] * n)[:n] if lab_id_row else [None] * n

            page_samples = [
                {
                    "lab_format": "ALS",
                    "report_reference": work_order,
                    "lab_reference": lab_id,
                    "sample_id": sample_id,
                    "mg_sample_no": None,
                    "sampling_date": date.split(" ")[0] if date else None,
                    "page": page_num,
                }
                for sample_id, date, lab_id in zip(sample_ids, dates, lab_ids)
            ]

            for row in table[date_idx + 3 :]:
                if not row or row[0] is None:
                    continue
                for key, pattern in _ALS_ANALYTE_PATTERNS:
                    if pattern.match(row[0]):
                        values = (row[3:] + [None] * n)[:n]
                        for sample, raw in zip(page_samples, values):
                            _add_analyte(sample, key, raw)
                        break

            samples.extend(page_samples)

    return samples


# ---------- Envirolab ----------

_ENVIROLAB_ANALYTE_PATTERNS = [
    ("ph", re.compile(r"^pH 1:5 soil:water")),
    ("ec_us_cm", re.compile(r"^Electrical Conductivity\b")),
    ("chloride_mg_kg", re.compile(r"^Chloride, Cl\b")),
    ("sulfate_mg_kg", re.compile(r"^Sulphate, SO4\b")),
    ("resistivity_ohm_m", re.compile(r"^Resistivity in soil")),
]

_OHM_M_TO_OHM_CM = 100


def _envirolab_coa_reference(first_page_text: str):
    m = re.search(r"CERTIFICATE OF ANALYSIS\s+(\S+)", first_page_text)
    return m.group(1) if m else None


def parse_envirolab_coa(pdf) -> list:
    first_page_text = pdf.pages[0].extract_text() or ""
    coa_reference = _envirolab_coa_reference(first_page_text)

    samples = []
    for page_num, page in enumerate(pdf.pages, start=1):
        for table in page.extract_tables():
            if table and table[0] and table[0][0] and "QUALITY CONTROL" in table[0][0]:
                continue

            current_block = None
            for row in table:
                if not row or row[0] is None:
                    continue
                label = row[0]

                if label == "Your Reference":
                    if current_block is not None:
                        samples.extend(current_block)
                    n = len(row) - 2
                    current_block = [
                        {
                            "lab_format": "Envirolab",
                            "report_reference": coa_reference,
                            "lab_reference": None,
                            "sample_id": None,
                            "mg_sample_no": mg_sample_no,
                            "sampling_date": None,
                            "page": page_num,
                        }
                        for mg_sample_no in row[2 : 2 + n]
                    ]
                    continue

                if current_block is None:
                    continue

                n = len(current_block)
                if label == "Our Reference":
                    for sample, lab_ref in zip(current_block, (row[2:] + [None] * n)[:n]):
                        sample["lab_reference"] = lab_ref
                elif label == "Sample ID":
                    for sample, sample_id in zip(current_block, (row[2:] + [None] * n)[:n]):
                        sample["sample_id"] = sample_id
                elif label == "Date Sampled":
                    for sample, date in zip(current_block, (row[2:] + [None] * n)[:n]):
                        sample["sampling_date"] = date
                else:
                    for key, pattern in _ENVIROLAB_ANALYTE_PATTERNS:
                        if pattern.match(label):
                            values = (row[2:] + [None] * n)[:n]
                            for sample, raw in zip(current_block, values):
                                _add_analyte(sample, key, raw)
                            break

            if current_block is not None:
                samples.extend(current_block)

    for sample in samples:
        if sample.get("resistivity_ohm_m") is not None:
            sample["resistivity_ohm_cm"] = sample["resistivity_ohm_m"] * _OHM_M_TO_OHM_CM
        else:
            sample["resistivity_ohm_cm"] = None

    return samples


def parse_chemical_coa(pdf, fmt: str) -> list:
    if fmt == "als":
        return parse_als_coa(pdf)
    if fmt == "envirolab":
        return parse_envirolab_coa(pdf)
    raise ValueError(f"Unknown chemical COA format: {fmt!r}")
