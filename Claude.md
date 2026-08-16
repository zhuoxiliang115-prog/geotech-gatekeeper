# Geotech Lab Data & Borehole Log Interpretation App

## What this is
A web app for uploading geotechnical lab test PDFs (Macquarie Geotech report
format) and borehole logs, auto-extracting results, generating the same charts
as the team's existing Excel workbook (PSD curves, Atterberg/plasticity chart,
moisture vs depth, Emerson class summary, CBR/SMDD curves, swell-shrink,
aggressivity vs AS 2159/DIN 4030 thresholds), and eventually auto-commenting on
borehole logs (flagging SPT refusal, fill depth, groundwater, sample gaps).

Lab reports are template-consistent (same field labels in the same positions
every time), which is what makes automated parsing tractable. Borehole logs
are less standardized and won't be 100% automatable — the realistic goal there
is reliable extraction of depth/strata/SPT/sample-ID rows, with anything
unparseable flagged for manual entry.

## Reference materials (read these first)
These currently live at the repo root (the project's setup guide,
`claude-code-setup-guide.md`, describes organizing them into a `reference/`
subfolder — do that as part of the first real scaffolding task, not before).

- `geotech-webapp-buildplan.md` — the architecture and build-order doc this
  project follows: recommended repo layout, why the backend is Python, the
  PDF parsing strategy, the calculation/interpretation logic to implement
  (ECe conversion, Emerson dispersion lookup, sodicity/ESP, Atterberg A-line,
  AS 2159 and DIN 4030 threshold bands, CBR/SMDD fit), and the suggested
  MVP-to-full build order.
- `parse_reports.py` — a working prototype parser, validated against real
  Macquarie Geotech PDFs. Covers Emerson class and Atterberg/PI reports
  (text-field regex extraction) and PSD reports (table extraction). This is
  the pattern to extend for every other report type, not rewrite.
- `emerson_results.csv`, `atterberg_results.csv`, `psd_results.csv` — sample
  outputs from running `parse_reports.py` against real reports, showing the
  expected shape of parsed data per report type.
- `atterberg_chart.png`, `psd_chart.png` — example charts matching what the
  Excel workbook produces, for the frontend chart engine to replicate.
- `claude-code-setup-guide.md` — onboarding notes for using Claude Code on
  this project (not app reference material itself).

## Intended stack
- **Backend:** Python (FastAPI). PDF parsing via `pdfplumber`. Organized as
  `parsers/` (one module per report type), `interpreters/` (domain logic:
  AS 2159 lookups, Emerson dispersion table, A-line calc, ECe conversion,
  DIN 4030 aggressivity bands), and `charts/` (chart-data prep for the
  frontend).
- **Frontend:** React (or Next.js) — upload UI, dashboards, chart rendering
  (Recharts or Plotly.js; PSD log-scale curves and the A-line plasticity
  chart need custom, non-default chart configs).
- **Database:** Postgres — samples, boreholes, projects, test results.
- **Storage:** uploaded PDFs (S3 or local), separate from the DB.

## Conventions
- **One parser per report type, dispatched by report title.** Each PDF page
  is one report; the report type is detected from its title line (e.g.
  "Determination of Emerson class number of a soil" vs "Determination of the
  particle size distribution of a soil"), then routed to a type-specific
  extractor that looks for known field labels and pulls the adjacent value.
  Follow the structure in `parse_reports.py`
  (`extract_common_fields` for shared fields, a `parse_<type>_page` function
  per report type, dispatched in `process_pdf` by matching on
  `get_report_title(text)`) — do not write one generic parser that tries to
  handle every report type at once.
- Always show the user a "here's what we extracted" review step before
  committing parsed results to the database — a silent misread (e.g. Emerson
  class 4 vs 5) has real consequences, so never auto-commit an unreviewed
  parse.
- Result pages should show the raw value, the formula/lookup applied, and the
  resulting classification — not just a final chart or number.

## Not yet built
No application code exists yet. This file and the reference materials above
are project setup only — see the build plan's suggested build order before
scaffolding.
