import io

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import calculations
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
