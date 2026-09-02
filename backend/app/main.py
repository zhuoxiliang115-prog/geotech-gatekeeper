import asyncio
import io

import pdfplumber
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import calculations
from .borehole_review import judgment, rules
from .parsers.borehole_log import PAGE_TYPE_LOG, process_log_pdf
from .parsers.dispatch import process_pdf
from .rock_parameters import classification as rock_classification
from .rock_parameters import lookup as rock_lookup
from .soil_parameters import classification, lookup

app = FastAPI(title="Geotech Lab Data API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


def _attach_atterberg_calculations(rows: list) -> None:
    """PI = LL - PL, shown as a worked example next to the lab's own
    reported PI (a cross-check, not a replacement for it - the lab value
    stays the source of truth in classification_zone etc.)."""
    for row in rows:
        ll, pl = row.get("liquid_limit"), row.get("plastic_limit")
        if ll is None or pl is None:
            row["calculations"] = None
            continue
        row["calculations"] = {
            "plasticity_index": {
                "formula": "PI = LL - PL",
                "inputs": {"ll": ll, "pl": pl},
                "output": calculations.plasticity_index(ll, pl),
            }
        }


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        result = process_pdf(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse PDF: {exc}") from exc

    _attach_atterberg_calculations(result["atterberg_results"])

    result["filename"] = file.filename
    result["pages_parsed"] = result.pop("total_pages")
    return result


@app.post("/review-log")
async def review_log(
    file: UploadFile = File(...),
    lab_reports: list[UploadFile] = File(default=[]),
):
    """Parses an uploaded borehole/pavement-dip/test-pit/cored-borehole
    log PDF, then runs every log-type page through both the deterministic
    rule engine (rules.py, standard doc §4.1) and the LLM-assisted
    judgment layer (judgment.py, §4.2).

    Optional lab report PDFs (Atterberg, PSD) can be uploaded alongside
    the log in the same request and are matched to the log's strata by
    sample ID within this request only - stateless, no persistence (see
    reference/borehole-log-standard.md Part 1 and the phase brief's
    explicit decision against building this preemptively). Checks that
    need a matching lab result but don't get one are skipped for that
    sample only, not failed - the response says clearly which checks were
    skipped and why, so "no lab data provided" doesn't read as "passed".

    The judgment layer makes one real Claude API call per log-type page -
    a deliberate per-review cost, not something to call speculatively. A
    judgment-layer failure (e.g. no API credentials configured) degrades
    that page's judgment_findings to an empty list with judgment_error
    set, rather than failing the whole review.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        parsed = process_log_pdf(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse log PDF: {exc}") from exc

    words_by_page = {}
    with pdfplumber.open(io.BytesIO(contents)) as pdf:
        for i, page in enumerate(pdf.pages):
            words_by_page[i + 1] = page.extract_words(use_text_flow=False, keep_blank_chars=False)

    lab_results = {"atterberg": [], "psd": []}
    for lab_file in lab_reports:
        lab_contents = await lab_file.read()
        if not lab_contents:
            continue
        try:
            lab_parsed = process_pdf(io.BytesIO(lab_contents))
        except Exception as exc:
            raise HTTPException(
                status_code=422, detail=f"Failed to parse lab report {lab_file.filename}: {exc}"
            ) from exc
        lab_results["atterberg"].extend(lab_parsed.get("atterberg_results", []))
        lab_results["psd"].extend(lab_parsed.get("psd_results", []))

    pages_reviewed = []
    for page_row in parsed["pages"]:
        page_num = page_row["page"]
        words = words_by_page.get(page_num, [])
        is_log_page = page_row.get("page_type") == "log"

        rule_findings = rules.run_all_checks(page_row, words, lab_results) if is_log_page else []
        # review_page_judgment() is a synchronous call (its own Anthropic
        # client, a real blocking network request) - run it off-thread so a
        # slow/hanging call doesn't block the whole async event loop (and
        # every other in-flight request) for however long it takes.
        judgment_result = await asyncio.to_thread(judgment.review_page_judgment, page_row)

        pages_reviewed.append(
            {
                "page": page_num,
                "page_type": page_row.get("page_type"),
                "parsed": page_row,
                "rule_findings": rule_findings,
                "judgment_findings": judgment_result["findings"],
                "judgment_error": judgment_result["error"],
                "judgment_usage": judgment_result["usage"],
            }
        )

    holes = {}
    for page in pages_reviewed:
        hole_id = (page["parsed"].get("header") or {}).get("hole_id")
        if hole_id is None:
            continue
        holes.setdefault(hole_id, []).append(page)

    judgment_usage_total = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    for page in pages_reviewed:
        usage = page["judgment_usage"]
        if usage is None:
            continue
        for key in judgment_usage_total:
            judgment_usage_total[key] += usage[key]

    return {
        "filename": file.filename,
        "pages_reviewed": pages_reviewed,
        "judgment_model": judgment.MODEL,
        "judgment_usage_total": judgment_usage_total,
        "holes": holes,
        "lab_reports_provided": {
            "atterberg_samples": len(lab_results["atterberg"]),
            "psd_samples": len(lab_results["psd"]),
        },
    }


@app.post("/soil-parameters")
async def soil_parameters(file: UploadFile = File(...)):
    """Parses an uploaded borehole/pavement-dip/test-pit/cored-borehole log
    PDF, then for every log-type page classifies each stratum (Fill/Clay/
    Sand only this pass - see soil_parameters/classification.py) and, where
    classified, looks up its typical design-parameter range from
    soil_typical_parameters.json (soil_parameters/lookup.py).

    A stratum that can't be confidently classified (no printed consistency/
    relative-density term and no usable SPT-N fallback, an out-of-scope
    principal type like Silt/Gravel, Rock, etc.) gets parameters: null and
    its classification's flag explains why - never a guessed bucket. This
    is a dedicated endpoint (not folded into /review-log) since it's a
    deterministic, rules-only lookup with no LLM judgment call and no
    review-standard checks - a different, cheaper feature entirely.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        parsed = process_log_pdf(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse log PDF: {exc}") from exc

    pages_processed = []
    for page_row in parsed["pages"]:
        if page_row.get("page_type") != PAGE_TYPE_LOG:
            continue

        field_test_entries = page_row.get("field_test_entries", [])
        strata_results = []
        for stratum in page_row.get("strata", []):
            classified = classification.classify_stratum(stratum, field_test_entries)
            # measured_values is always omitted here - no lab parser in this
            # codebase yet produces a Stage-1 measured value in the shape
            # lookup.lookup_parameters() expects; see that function's
            # docstring for why this is intentionally dead code for now.
            parameters = lookup.lookup_parameters(classified["bucket_id"]) if classified["classified"] else None
            strata_results.append({"stratum": stratum, "classification": classified, "parameters": parameters})

        pages_processed.append(
            {
                "page": page_row["page"],
                "header": page_row.get("header"),
                "strata_results": strata_results,
            }
        )

    holes = {}
    for page in pages_processed:
        hole_id = (page.get("header") or {}).get("hole_id")
        if hole_id is None:
            continue
        holes.setdefault(hole_id, []).append(page)

    return {
        "filename": file.filename,
        "pages_processed": pages_processed,
        "holes": holes,
    }


@app.post("/rock-parameters")
async def rock_parameters(file: UploadFile = File(...)):
    """Parses an uploaded Cored Borehole log PDF, then for every Cored
    Borehole page classifies each rock stratum (Sandstone/Shale only this
    pass - see rock_parameters/classification.py) into a Class I-V bucket
    per the Sydney Classification System (Table 9.1: UCS + defect spacing,
    with a seam-content flag - see reference/sydney-classification-system.md)
    and, where classified, looks up its typical design parameters from
    rock_typical_parameters.json (rock_parameters/lookup.py) - both the
    design_table and hoek_brown_table, kept as two separate parameter sets
    since they aren't interchangeable.

    Only Cored Borehole pages are processed - other log types never carry
    Sandstone/Shale strata, so classify_rock_stratum() would just report
    "no recognisable rock type" for every one of their strata; skipping
    them here keeps the response to what this feature actually covers.

    A stratum that can't be confidently classified (no rock type text
    recognised, an out-of-scope rock type like Claystone, or no UCS/Is(50)
    reading nearby) gets parameters: null and its classification's flag
    explains why - never a guessed bucket. Where classification did use an
    Is(50)->UCS estimate rather than a direct UCS test, that's carried in
    the classification's own "strength" field (source, confidence) and
    restated in classification_basis and warnings - never silently
    presented as equivalent to a direct-UCS classification. This is a
    dedicated endpoint (not folded into /review-log or /soil-parameters)
    for the same reason those are separate: deterministic, rules-only,
    no LLM judgment call.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        parsed = process_log_pdf(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse log PDF: {exc}") from exc

    pages_processed = []
    for page_row in parsed["pages"]:
        if page_row.get("page_type") != PAGE_TYPE_LOG:
            continue
        if (page_row.get("header") or {}).get("log_type") != "Cored Borehole":
            continue

        point_load_ucs_readings = page_row.get("point_load_ucs_readings", [])
        defect_entries = page_row.get("defect_entries", [])
        strata = page_row.get("strata", [])

        strata_results = []
        for i, stratum in enumerate(strata):
            next_stratum_depth_m = strata[i + 1]["depth_from_m"] if i + 1 < len(strata) else None
            classified = rock_classification.classify_rock_stratum(
                stratum, next_stratum_depth_m, point_load_ucs_readings, defect_entries
            )
            parameters = (
                rock_lookup.lookup_rock_parameters(classified["bucket_id"]) if classified["classified"] else None
            )
            strata_results.append({"stratum": stratum, "classification": classified, "parameters": parameters})

        pages_processed.append(
            {
                "page": page_row["page"],
                "header": page_row.get("header"),
                "strata_results": strata_results,
            }
        )

    holes = {}
    for page in pages_processed:
        hole_id = (page.get("header") or {}).get("hole_id")
        if hole_id is None:
            continue
        holes.setdefault(hole_id, []).append(page)

    return {
        "filename": file.filename,
        "pages_processed": pages_processed,
        "holes": holes,
    }


@app.post("/upload-log")
async def upload_log_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        result = process_log_pdf(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse PDF: {exc}") from exc

    result["filename"] = file.filename
    result["pages_parsed"] = result.pop("total_pages")
    return result
