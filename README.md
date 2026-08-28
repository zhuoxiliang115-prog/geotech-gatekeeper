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

## New machine setup

Prerequisites: **Python 3.11+**, **Node.js 18+** (with npm), and **git**.

```bash
git clone https://github.com/zhuoxiliang115-prog/geotech-gatekeeper
cd geotech-gatekeeper

cd backend
python3 -m venv .venv
source .venv/bin/activate       # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
# for running the test suite too: pip install -r requirements-dev.txt

cd ../frontend
npm install
```

Then run both (see the Backend/Frontend sections below for the exact
commands) - no other setup needed. The frontend defaults to
`http://127.0.0.1:8000` for the backend, so no env var is required for a
normal local setup; see the Frontend section if you need to point it
somewhere else.

If you're going to use the Borehole Log Review feature's AI-assisted
judgment layer for real (not just see it, e.g., report a clean "not set"
error), you also need an Anthropic API key set as `APP_ANTHROPIC_API_KEY`
in the environment the backend runs in (not `ANTHROPIC_API_KEY` - see the
Borehole Log Review section below for why). Everything else (parsing, the
deterministic rule engine, lab cross-referencing) works without it.

```powershell
# Windows PowerShell, before starting uvicorn
$env:APP_ANTHROPIC_API_KEY="sk-ant-..."
```

```bash
# macOS/Linux, before starting uvicorn
export APP_ANTHROPIC_API_KEY="sk-ant-..."
```

This only lasts for that terminal session - set it again each time you
open a fresh terminal to run the backend (or add it to your shell profile
/ a `.env` file loaded by however you run it, if you want it permanent).

## Backend (FastAPI)

```bash
cd backend
source .venv/bin/activate       # Windows PowerShell: .venv\Scripts\Activate.ps1
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
- `POST /upload-log` — parses a borehole/pavement-dip/test-pit/cored-borehole
  log PDF only (no rule/judgment checks), mainly for inspecting the raw
  parse.
- `POST /review-log` — see "Borehole Log Review" below.

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

## Borehole Log Review

`POST /review-log` parses an uploaded borehole/pavement-dip/test-pit/
cored-borehole log PDF (`backend/app/parsers/borehole_log.py`), optionally
matches it against Atterberg/PSD lab report PDFs uploaded alongside it in
the same request (no persistence - matched fresh per request), and runs
every log page through two layers, checked against
`reference/borehole-log-standard.md`:

- **Rule engine** (`backend/app/borehole_review/rules.py`) - deterministic
  checks (required header fields, valid USCS/weathering symbols, defect
  description format, lab cross-referencing) with a genuine pass/fail per
  check. Free, no API key needed.
- **Judgment layer** (`backend/app/borehole_review/judgment.py`) - one
  real `claude-opus-5` API call per log page for the six categories that
  need real interpretive judgment (field-ID vs. USCS symbol, SPT-N vs.
  consistency correlation, geological-origin plausibility, cross-sheet
  continuity, colour-term plausibility, secondary-component wording). This
  is a real, billed API call per page, not free, and calls run one at a
  time (not in parallel) - a multi-page log can take a while. Requires
  `APP_ANTHROPIC_API_KEY` in the backend's environment (see "New machine
  setup" above); without it, this layer reports a clean error per page
  instead of crashing, and the rest of the review still works.

The frontend's "Borehole Log Review" tab (`frontend/src/components/
BoreholeLogReview.jsx`) drives this: upload a log PDF, optionally attach
lab report PDFs, click "Review this log" (deliberately not automatic, since
it's a paid call), then browse results by hole (`HoleTabs.jsx`) - each
hole shows a per-hole "Action items" checklist pulled from every sheet's
fails/flags, then the full per-sheet breakdown (rule-checked findings,
lab cross-reference findings, judgment-based findings, each visually
distinct).

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

The frontend expects the backend at `http://127.0.0.1:8000` by default -
deliberately `127.0.0.1`, not `localhost` (on some Windows setups
`localhost` resolves to the IPv6 loopback first, which nothing is
listening on since uvicorn's default bind is IPv4-only, causing
"Failed to fetch" even though the backend is up). Override with a
`VITE_API_BASE_URL` env var (e.g. in `frontend/.env.local`) if you need
to point it somewhere else, such as a real deployment.

## What's not built yet

No database or persisted review/commit step - everything is recomputed
fresh on each upload/review, and per-sample inputs (Soil Condition A/B,
salinity MF) reset if you re-upload. No auto-comment engine beyond the
Borehole Log Review feature above. No Soil Condition A/B auto-detection
(needs borehole groundwater depth data that doesn't exist yet - the spec
is explicit this must stay manual until then). No marked-up/annotated PDF
export of a reviewed log (discussed, not built - would need each stratum's
pixel position on the original page threaded through the whole pipeline,
not just its depth in metres). No hosting/deployment - everything above
runs locally only, on one machine at a time; going beyond that (LAN
sharing vs. real hosting) is a real, separate decision - see "New machine
setup" above for the local-only path. `reference/geotech-webapp-buildplan.md`
has the original suggested build order; `reference/charts-and-calculations-spec.md`
scopes the chart/calculation work explicitly (ISS is out of scope by
request, and SMDD/CBR curve *data points* aren't extracted or charted -
see the Frontend section above).
