# Geotechnical Lab Data & Borehole Log Interpretation Website — Build Plan

## 1. What the app needs to do (from your files)

| Input | Examples in your files | Output needed |
|---|---|---|
| Structured lab PDF reports | Macquarie Geotech test reports (PSD, Atterberg/PI, Emerson, MC, CBR, SMDD, UU triaxial, point load, ISS/shrink-swell), Envirolab "Certificate of Analysis" (pH, EC, sulphate, chloride, resistivity) | Parsed numeric data per sample |
| Borehole log PDFs | (you'll send a sample) | Extracted stratigraphy/depth intervals + auto-generated comments (e.g. flag SPT refusal, fill depth, groundwater, sample gaps) |
| Excel interpretation workbook | `WORKING_Lab_data_Interpretation.xlsx`, `Report_Graphs.xlsx` | Same chart types, generated automatically from parsed data |

Chart types your workbook already builds, which the site needs to replicate:
- **PSD curve** — % passing vs sieve size, log-x axis, per borehole/sample, multiple lines overlaid
- **Atterberg/plasticity chart** — PI vs LL scatter, with A-line/U-line and CLAY/SILT zone bands (per AS 1726)
- **Moisture content vs depth**, often alongside LL/PL envelope
- **Emerson class summary** — class number (1–8) per sample, dispersion potential lookup
- **CBR vs depth**, **SMDD/OMC curve** (dry density vs moisture content, parabolic fit)
- **Swell-shrink index** results
- **DCP vs depth**
- **Aggressivity** — pH, sulphate, chloride, resistivity vs AS 2159 / DIN 4030 threshold bands

## 2. Recommended architecture

**Don't build this as a single Claude.ai artifact** — it needs persistent storage, real PDF parsing (not doable client-side reliably), and a proper backend. Structure:

```
geotech-app/
├── frontend/         React (or Next.js) — upload UI, dashboards, chart rendering
├── backend/          Python (FastAPI) — parsing, calculations, API
│   ├── parsers/       one module per report type (regex/table extraction)
│   ├── interpreters/  domain logic: AS2159 lookups, Emerson dispersion table,
│   │                  A-line calc, ECe conversion factors (Appendix 1 tables),
│   │                  DIN4030 aggressivity bands
│   └── charts/        chart-generation (Plotly/Recharts data prep)
├── db/                Postgres — samples, boreholes, projects, test results
└── storage/           uploaded PDFs (S3 or local)
```

**Why Python backend:** PDF table extraction (`pdfplumber`, `camelot`) and numeric interpretation logic are much easier in Python than in a browser. React/Next.js frontend consumes a clean JSON API.

**Charting:** Recharts or Plotly.js for interactive web charts (matches your Excel look) — log-scale PSD curves and the A-line plasticity chart are the two that need custom (non-default) chart configs.

## 3. PDF parsing strategy (the hard part — but tractable)

Your Macquarie Geotech reports are template-consistent: same field labels ("MG Sample No.", "Report No.", "Emerson Class Number:", etc.) in the same positions every time. That means:

1. **Use `pdfplumber`** to extract text + tables per page.
2. **Write one parser per report type**, keyed off the report title (e.g. "Determination of Emerson class number of a soil" → Emerson parser; "Determination of the liquid limit, plastic limit..." → Atterberg parser). Each parser looks for known field labels and grabs the adjacent value — much more robust than trying one generic parser for everything.
3. **Validate**: after parsing, show the user a side-by-side "here's what we read vs the PDF" screen before committing to the database — lab reports are exactly the kind of document where a silent misread (e.g. Emerson class 4 vs 5) has real consequences.
4. **Borehole logs** are usually less standardized (different consultants format them differently) — this will need its own parser per log template, and likely won't be 100% automatable. Realistic goal: extract depth/strata/SPT/sample-ID table rows reliably, and flag anything it can't parse for manual entry, rather than promising full auto-read on day one.

## 4. Calculation/interpretation logic to build in (from your booklet + workbook)

- ECe conversion: `EC(1:5) × soil-texture factor` (Table 6.1, sand=17 → heavy clay=6)
- Emerson class → dispersion potential lookup table
- Sodicity: ESP = (exchangeable Na / CEC) × 100, then non-sodic/sodic/highly sodic bands
- Atterberg A-line: `PI = 0.73(LL − 20)` for classification zone
- AS 2159 corrosivity thresholds (pH, chloride, resistivity, sulphate) — condition A vs B
- DIN 4030 aggressivity bands (pH, CO₂, NH₄⁺, Mg²⁺, SO₄²⁻)
- CBR/SMDD: dry density vs moisture parabolic fit, MDD/OMC read-off

Each result page should show the **raw value → the formula/lookup applied → the classification**, since you asked for calculation steps, not just a final chart.

## 5. Suggested build order (MVP → full)

1. **Data model + manual entry UI** — get one project's results into a database and charted correctly (validates your chart requirements before any parsing exists)
2. **PSD + Atterberg + MC parsers** — your three most common test types — parse a batch of your real Macquarie PDFs, check accuracy
3. **Chart engine** matching the 3 above
4. **Remaining parsers** (Emerson, CBR, SMDD, ISS/swell, aggressivity, point load, UU triaxial)
5. **Borehole log parser** — once you send an example, this gets scoped properly
6. **Auto-comment engine** for logs (rule-based: flag inconsistencies, refusal depths, missing samples, etc.)
7. **Project/report dashboard** — combine everything per borehole/project, exportable

## 6. Practical next step

Send me a sample borehole log PDF and I can prototype the log parser + comment logic here, and build one working chart (e.g. PSD) end-to-end from a real Macquarie PDF as a proof of concept. Once that's validated, that code + this plan hands straight to Claude Code to scaffold the full repo and iterate to completion.
