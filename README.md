# Geotech Lab Data & Borehole Log Interpretation App

See `CLAUDE.md` for the project overview, `reference/geotech-webapp-buildplan.md`
for the full architecture and build plan, and `reference/charts-and-calculations-spec.md`
for the chart/calculation formulas and threshold tables the parsers,
`backend/app/calculations.py`, and the frontend charts implement.

- **Backend:** FastAPI, parses Emerson, Atterberg, PSD, SMDD, CBR, Point
  Load, and chemical COA (ALS/Envirolab) reports out of uploaded PDFs, plus
  a calculation engine for PI, point load size correction, AS 2159
  durability classes, and ECe soil salinity.
- **Frontend:** React + Vite + Recharts. Upload a PDF and see, per test
  type: raw extracted values, a chart matching the source PDF's style,
  calculation steps + plain-language explanation, and the raw JSON
  response. AS 2159 classification and ECe salinity take a manual
  per-sample input (Soil Condition A/B, salinity Multiplication Factor)
  since neither can be auto-detected from the lab data - entering them
  recomputes the classification live in the browser.

No database or auth yet.

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
  `atterberg_results`, `psd_results`, `smdd_results`, `cbr_results`,
  `point_load_results`, `chemical_coa_results`, and `unrecognized_pages` for
  any page whose title didn't match a known parser (flagged for manual
  entry, per CLAUDE.md's review-step convention). `atterberg_results` rows
  also carry a `calculations` block (formula, inputs, output). AS 2159
  classes and ECe salinity aren't in this response - they need the manual
  Soil Condition A/B and Multiplication Factor inputs, so the frontend
  computes them client-side (`frontend/src/calculations.js`, a hand-kept
  port of the relevant parts of `backend/app/calculations.py`) once the
  user enters them.

### Parsers

`backend/app/parsers/` ports the logic from `reference/parse_reports.py`,
one module per report type, dispatched by report title
(`backend/app/parsers/dispatch.py`), per CLAUDE.md's conventions. Chemical
COA reports (`chemical_coa.py`) are the one exception - a COA is a wide
pivot table spanning the whole PDF rather than one sample per page, so it's
detected once from the first page and handled as a whole-document unit
instead of going through the per-page loop. Point Load reports
(`point_load.py`) also differ from the single-sample pattern: one page
holds a table of *multiple* samples, so its parser returns a list of
readings per page instead of one row.

To add a new single-sample-per-page report type (aggressivity thresholds,
UU triaxial, etc.):

1. Add a `parse_<type>_page` function in a new `backend/app/parsers/<type>.py`,
   following the pattern in `emerson.py` or `atterberg.py` (text-field regex)
   or `psd.py` (table extraction).
2. Register its title prefix in `dispatch.py`.
3. Add unit tests in `backend/tests/test_new_parsers.py` (or a new file)
   checked against a real sample PDF in `reference/`.

`backend/app/calculations.py` holds the pure, PDF-parsing-free calculation
functions (plasticity index, point load Is50 size correction, AS 2159
concrete/steel durability classes, ECe soil salinity) - see
`reference/charts-and-calculations-spec.md` for the formulas and threshold
tables they implement.

### Testing

```bash
cd backend
source .venv/bin/activate
pytest -v
```

`backend/tests/test_parsers.py` and `test_upload_api.py` (Emerson/Atterberg/
PSD) use a synthetic PDF fixture (`backend/tests/fixtures/build_sample_pdf.py`,
via `reportlab`) since no real sample PDFs shipped with that phase.
`test_new_parsers.py`, `test_calculations.py`, and `test_upload_api_phase1.py`
(SMDD/CBR/Point Load/chemical COA) use the real sample PDFs now in
`reference/` instead, checked against the actual values printed in each
report.

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

Open `http://localhost:5173`. Pick a PDF and click "Upload & Parse" to see,
per test type: raw extracted values → chart → calculation steps +
explanation, plus the raw JSON response in a collapsible section. This is
the "here's what we extracted" review step from CLAUDE.md — there's no
database yet, so nothing is saved; it's just a way to see the parser's
output.

`frontend/src/components/` has one component per chart type
(`PsdChart.jsx`, `AtterbergChart.jsx`, etc.) plus the shared
`CalculationExplanation.jsx` (formula/inputs/output/explanation, reused
across every test type) and per-type `*Section.jsx` wrappers that combine
them. `frontend/src/theme.js` holds the chart color tokens (a validated
categorical palette plus a single blue as the default series color,
matching the existing PDF reports' style). SMDD and CBR intentionally show
a labeled summary instead of a fitted/drawn curve - the source PDFs render
those charts as vector graphics with no extractable data points (SMDD has
discrete markers but no reliable way to recover their coordinates; CBR is
a continuous line with no discrete points at all), so there's nothing real
to plot without fabricating a curve shape.

The frontend expects the backend at `http://localhost:8000` by default;
override with a `VITE_API_BASE_URL` env var (e.g. in `frontend/.env.local`)
if needed.

## What's not built yet

No database or persisted review/commit step - everything is recomputed
fresh on each upload, and per-sample inputs (Soil Condition A/B, salinity
MF) reset if you re-upload. No borehole log parsing or auto-comment
engine. No Soil Condition A/B auto-detection (needs borehole groundwater
depth data that doesn't exist yet - the spec is explicit this must stay
manual until then). `reference/geotech-webapp-buildplan.md` has the
original suggested build order; `reference/charts-and-calculations-spec.md`
scopes the chart/calculation work explicitly (ISS is out of scope by
request, and SMDD/CBR curve *data points* aren't extracted or charted -
see the Frontend section above).
