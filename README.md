# Geotech Lab Data & Borehole Log Interpretation App

See `CLAUDE.md` for the project overview and `reference/geotech-webapp-buildplan.md`
for the full architecture and build plan. This covers the MVP scaffolding:
a FastAPI backend that parses Emerson, Atterberg, and PSD reports out of
uploaded PDFs, and a React frontend that uploads a PDF and shows the raw
parsed JSON as a review step. No charts, database, or auth yet.

## Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # includes test-only deps (pytest, reportlab)
uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000` (docs at `/docs`). Endpoints:

- `GET /health` — liveness check
- `POST /upload` — accepts a PDF (`multipart/form-data`, field name `file`),
  returns parsed results grouped by report type: `emerson_results`,
  `atterberg_results`, `psd_results`, and `unrecognized_pages` for any page
  whose title didn't match a known parser (flagged for manual entry, per
  CLAUDE.md's review-step convention).

### Parsers

`backend/app/parsers/` ports the logic from `reference/parse_reports.py`,
one module per report type, dispatched by report title
(`backend/app/parsers/dispatch.py`), per CLAUDE.md's conventions. To add a
new report type (CBR, SMDD, aggressivity, etc.):

1. Add a `parse_<type>_page` function in a new `backend/app/parsers/<type>.py`,
   following the pattern in `emerson.py` or `atterberg.py` (text-field regex)
   or `psd.py` (table extraction).
2. Register its title prefix in `dispatch.py`.
3. Add unit tests in `backend/tests/test_parsers.py` and extend the sample
   PDF fixture (`backend/tests/fixtures/build_sample_pdf.py`) with a page
   for the new type.

### Testing

```bash
cd backend
source .venv/bin/activate
pytest -v
```

There are no real sample PDFs in this repo (only their parsed CSV/PNG
outputs, under `reference/`), so `backend/tests/fixtures/build_sample_pdf.py`
generates a synthetic multi-page PDF (via `reportlab`) with one page per
report type plus one unrecognized page, and `test_upload_api.py` runs it
through the real `/upload` endpoint end to end — not mocked.

To manually try `/upload` against a real report PDF once you have one:

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/report.pdf;type=application/pdf"
```

Or use the interactive docs at `http://localhost:8000/docs`, or the
frontend below.

## Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Pick a PDF and click "Upload & Parse" to see
the extracted results per report type, plus the raw JSON response. This is
the "here's what we extracted" review step from CLAUDE.md — there's no
database yet, so nothing is saved; it's just a way to see the parser's
output. No charts yet, per the current build step's scope.

The frontend expects the backend at `http://localhost:8000` by default;
override with a `VITE_API_BASE_URL` env var (e.g. in `frontend/.env.local`)
if needed.

## What's not built yet

Per `reference/geotech-webapp-buildplan.md`'s suggested build order: no
database, no persisted review/commit step, no chart engine, no remaining
parsers (CBR, SMDD, ISS/swell, aggressivity, point load, UU triaxial), and
no borehole log parsing or auto-comment engine.
