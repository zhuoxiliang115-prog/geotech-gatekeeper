import asyncio
import io

import pdfplumber
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import calculations
from .borehole_review import judgment, rules
from .parsers.borehole_log import process_log_pdf
from .parsers.dispatch import process_pdf

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
