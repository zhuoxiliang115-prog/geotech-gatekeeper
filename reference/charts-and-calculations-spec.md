# Charts & Calculation Explanations — Implementation Spec

Extracted directly from `WORKING_Lab_data_Interpretation.xlsx` (the user's real interpretation
spreadsheet) and cross-checked against Macquarie Geotech PDF report formats. This spec covers
two features only: **(1) chart/graph generation** and **(2) calculation-step explanations**
shown alongside parsed results. Borehole log auto-commenting is a separate, later feature — not
covered here.

Goal: every chart and every calculation shown on the website should visually and numerically
match what this firm already produces in the spreadsheet, not a generic textbook version.

---

## 1. Particle Size Distribution (PSD)

**Chart type:** Line/scatter, X-axis log scale.

- X-axis: sieve aperture (mm), log scale, range ~0.001 to 200mm (or trim to the data's min/max
  sieve size present — don't hardcode 0.001 if the report only goes to 0.075mm, since these lab
  reports use standard method 0.075–200mm, no hydrometer).
- Y-axis: percentage passing (%), linear scale, 0–100.
- One line per sample. Circular markers at each sieve reading (matches PDF style exactly).
- Sieve sizes used in these reports (fixed set): 200, 75, 63, 37.5, 26.5, 19.0, 13.2, 9.5, 6.7,
  4.75, 2.36, 1.18, 0.6, 0.425, 0.3, 0.212, 0.15, 0.075 (mm).

**Explanation to show under the chart:**
- Plain-language: "This curve shows what percentage of the soil sample (by weight) passes
  through each sieve size. A steep curve means the soil is well-graded (mixed particle sizes);
  a flat curve at one point means most particles are a similar size."
- Show the raw sieve table (aperture vs % passing) alongside the chart, exactly as the PDF does.
- If %Gravel / %Coarse / %Fine / %Clay breakdown is available (see `PSD (2)` sheet columns), show
  it as a simple composition summary (e.g. "Gravel 4% · Sand 33% · Fines 63%").

---

## 2. Atterberg Limits / Plasticity Chart

**Chart type:** Scatter chart, LL (x) vs PI (y), with two fixed reference lines.

- X-axis: Liquid Limit (%), 0–100.
- Y-axis: Plasticity Index (%), 0–60.
- **A-line:** `PI = 0.73 × (LL − 20)`, plotted for LL from 0 to 100 (below the origin the line is
  typically not drawn until LL≈20, per AS 1726:2017 Figure 5 convention — draw from LL=20).
- **U-line:** `PI = 0.9 × (LL − 8)`, plotted from LL≈16 upward.
- Region labels "CLAY" (above A-line) and "SILT" (below A-line), plus "Inorganic Silts & Clays"
  dashed low-PI band, matching the PDF layout exactly (see any `*_AS_PI.pdf` sample).
- Plot the sample's point (LL, PI) with dashed guide lines down to each axis and a label
  "LL {value} / PI {value}" — this exact annotation style appears on every lab PDF.

**Calculation steps to show:**
```
PI = LL − PL
```
Show this as a literal worked example using the sample's actual numbers, e.g.:
`PI = 54 − 20 = 34%`

**Explanation:**
- "Liquid Limit (LL) and Plastic Limit (PL) mark the moisture contents at which a soil changes
  behaviour — from liquid to plastic, and from plastic to solid. Plasticity Index (PI) is the
  range of moisture over which the soil stays plastic (workable). A higher PI generally means
  more clay content and greater potential for shrink-swell behaviour."
- Also report Linear Shrinkage (%) alongside — it's a separate lab measurement, not derived from
  LL/PL, so don't imply it's calculated from them.

---

## 3. Standard Compaction (SMDD) Curve

**Chart type:** Line chart (smoothed/parabolic fit), Dry Density (y) vs Moisture Content (x).

- X-axis: Moisture Content (%).
- Y-axis: Dry Density (t/m³).
- Plot the individual test points, plus the fitted curve to the peak (Maximum Dry Density).
- Mark the peak point clearly and label it "MDD {value} t/m³ @ OMC {value}%".

**Explanation:**
- "This curve shows how compacted density changes with moisture content for this material. The
  peak — Maximum Dry Density (MDD) at Optimum Moisture Content (OMC) — is the target used to
  assess how well the material has been compacted on site."
- If a Field Moisture Content is available for comparison, show the ratio used in the CBR sheet:
  `FMC/OMC ratio (%) = (Field Moisture Content / OMC) × 100`

---

## 4. California Bearing Ratio (CBR) Curve

**Chart type:** Line chart, Load (kN) vs Penetration (mm).

- X-axis: Penetration (mm), 0–13.
- Y-axis: Load (kN).
- Plot the raw curve, then mark "Corrected Zero", "Corrected 2.5" and "Corrected 5.0" points —
  these are the standard CBR correction points shown in every lab PDF (dashed vertical lines at
  2.5mm and 5.0mm penetration back to the corrected curve).
- Report CBR value at whichever penetration governs (2.5mm or 5.0mm — the lab reports the higher
  corrected value's penetration, shown explicitly in the PDF, e.g. "CBR Value (%) at 2.5 mm
  Penetration: 12").

**Explanation:**
- "CBR measures the strength of a compacted material by comparing its resistance to a standard
  penetration test against a reference crushed-stone value. It's widely used to design pavement
  and subgrade thickness."
- Show achieved vs target density/moisture (Lab Density Ratio, Lab Moisture Ratio) as a simple
  two-column comparison, matching the PDF's "Achieved / Target" table.

---

## 5. Point Load Strength Index

**Chart type:** Not typically charted — presented as a table (matches PDF exactly: MG Sample
No., Sample ID, Test Type [Diametral/Axial], Failure Load, Uncorrected Is, Corrected Is50,
Failure Mode). If a chart is wanted, Is50 vs depth (scatter, one point per sample) is a natural
option for showing strength variation down a borehole.

**Calculation steps:**
```
Is = P / De²          (P = failure load in kN, De = equivalent core diameter in mm)
Is50 = Is × (De / 50)^0.45      (size correction to a reference 50mm diameter)
```
This correction formula is the standard AS 4133.4.1 form — safe to present as-is.

**Explanation:**
- "Point Load testing estimates rock strength from a small core or lump sample by measuring the
  load needed to fracture it between two conical platens. The result is size-corrected (Is50) so
  results from different specimen sizes can be compared on the same basis."
- Include the Failure Mode Key (1–4, as shown on every PLT PDF) as a small legend.

---

## 6. Emerson Class Number

**Chart type:** Bar chart — one bar per sample, Emerson Class Number (1–8) on the y-axis. The
spreadsheet's own `Emerson` sheet chart is a simple bar chart of class number by sample.

**Explanation:**
- "The Emerson Class Number (1–8) indicates how a soil breaks down when immersed in water — a
  quick indicator of dispersive/erosion-prone behaviour. Lower numbers (1–3) indicate dispersive,
  erosion-susceptible soils; higher numbers (7–8) indicate stable, non-dispersive soils."
- No calculation involved — it's a direct lab observation/classification, not derived from other
  numbers. Just present the class number, water type used, and any lab notes (e.g. "reaction
  with acid, calcite present").

---

## 7. Aggressivity / Durability Classification (chemical results)

Confirmed against **AS 2159-2009, Tables 6.4.2(C) and 6.5.2(C)** (published standard tables,
sighted directly — not the spreadsheet's approximation). Implement these exact tables verbatim.

**Soil Conditions A vs B (governs which column applies):**
- **Soil Condition A** — high permeability soils (e.g. sands and gravels) that are *in
  groundwater*.
- **Soil Condition B** — low permeability soils (e.g. silts and clays), OR any soil that is
  *above* the groundwater table (regardless of permeability).

This means the A/B flag isn't a free choice — it's determined per-sample from soil type + whether
that depth is above or below the groundwater table at the time of sampling. The parser/backend
will need groundwater depth (from the borehole log) to assign this automatically; until that's
wired up, let the user set A/B manually per sample.

**Table 6.4.2(C) — Concrete piles in soil:**

| Sulfate in soil (ppm) | Sulfate in groundwater (ppm) | pH | Chloride in groundwater (ppm) | Condition A | Condition B |
|---|---|---|---|---|---|
| <5,000 | <1,000 | >5.5 | <6,000 | Mild | Non-aggressive |
| 5,000–10,000 | 1,000–3,000 | 4.5–5.5 | 6,000–12,000 | Moderate | Mild |
| 10,000–20,000 | 3,000–10,000 | 4–4.5 | 12,000–30,000 | Severe | Moderate |
| >20,000 | >10,000 | <4 | >30,000 | Very severe | Severe |

Each row is matched independently per parameter (sulfate-in-soil, sulfate-in-groundwater, pH,
chloride-in-groundwater); **the governing (most severe) result across the parameters that have
data determines the final concrete exposure classification** for that sample. Only use the
sulfate-in-soil column against a soil sulfate result, and the sulfate-in-groundwater column
against a groundwater sample — don't cross them.

**Table 6.5.2(C) — Steel piles in soil:**

| pH | Chloride in soil (ppm) | Chloride in groundwater (ppm) | Resistivity (ohm·cm) | Condition A | Condition B |
|---|---|---|---|---|---|
| >5 | <5,000 | <1,000 | >5,000 | Non-aggressive | Non-aggressive |
| 4–5 | 5,000–20,000 | 1,000–10,000 | 2,000–5,000 | Mild | Non-aggressive |
| 3–4 | 20,000–50,000 | 10,000–20,000 | 1,000–2,000 | Moderate | Mild |
| <3 | >50,000 | >20,000 | <1,000 | Severe | Moderate |

Same governing-parameter logic: take the most severe class across pH, chloride, and resistivity
that have data for that sample.

**Chart type:** Classification summary table (sample, pH, SO4, Cl, resistivity, Soil Condition
A/B, governing class for concrete and for steel). A heatmap of exposure class by sample/depth is
a reasonable secondary visual, not a replacement for the table.

**Explanation:**
- "This classifies how aggressive the soil and groundwater environment is toward buried concrete
  and steel piles, based on acidity, sulfate and chloride content, and electrical resistivity —
  per AS 2159-2009. It's used to select appropriate concrete cover, sulfate-resisting cement, or
  corrosion protection allowances for pile foundations."
- Show which Soil Condition (A or B) applied and why (soil type + above/below groundwater),
  since that's what determines which column governs the result.

---

## 8. Soil Salinity Classification (ECe)

This is the separate classification the user actually wants prioritised — based on Electrical
Conductivity of the saturated extract (ECe), not the AS 2159 durability tables above. Both
reference tables are now confirmed (sourced by the user directly), so this section is fully
specified — no open questions remain.

**Calculation steps:**
```
EC(1:5), dS/m  =  measured Electrical Conductivity (µS/cm) ÷ 1000
ECe (dS/m)     =  EC(1:5) × Multiplication Factor (MF)
```

**MF input — manual, not auto-detected:** The Multiplication Factor depends on soil texture,
which isn't something the lab PDF or parser can reliably determine from text alone (texture
group is a hand-feel field assessment, not a lab-reported number). So:
- Add a **manual numeric input field** for MF per sample (plain number entry, not a dropdown).
- Alongside the input, display **Table 6.1** below as a reference guide so the user can look up
  the right value for their soil description before typing it in. Don't try to auto-map soil
  description text to a texture group — let the person doing the interpretation make that call.

**Table 6.1 — Factors for converting EC(1:5) to ECe** (source: multiple, per Richards 1954
convention commonly cited in Australian salinity guidance):

| Soil Texture Group | Description | Multiplication Factor |
|---|---|---|
| Sands | Very little or no coherence; cannot be rolled into a stable ball. Individual sand grains adhere to fingers. | 17 |
| Sandy loams | Some coherence, can be rolled into a stable ball but not a thread. Sand grains can be felt. | 14 |
| Loams | Can be rolled into a thick thread, breaks up before 3–4mm thick. Smooth, spongy feel, no obvious sandiness. | 10 |
| Clay loam | Can be rolled to a 3–4mm thread but with fractures along its length. Becoming plastic, capable of being moulded. | 9 |
| Light clays | Rolls to a 3–4mm thread without fracture. Plastic, smooth feel, some resistance to rolling out. | 8.5 |
| Light medium clay | Plastic and smooth to the touch; forms a ribbon of 7.5cm. | 8 |
| Medium clay | Handles like plasticine, forms rods without fracture, some resistance to ribboning shear, ribbons to 7.5cm+. | 7 |
| Heavy clays | Rolls to a 3–4mm thread, forms a ring in the palm without fracture. Smooth, very plastic, moderate-to-strong resistance to rolling out. | 6 |

**Table 6.2 — ECe values of soil salinity classes** (source: Richards, 1954):

| Class | ECe (dS/m) | Comments |
|---|---|---|
| Non-saline | <2 | Salinity effects mostly negligible |
| Slightly saline | 2–4 | Yields of very sensitive crops may be affected |
| Moderately saline | 4–8 | Yields of many crops affected |
| Very saline | 8–16 | Only tolerant crops yield satisfactorily |
| Highly saline | >16 | Only a few very tolerant crops yield satisfactorily |

Classify each sample's computed ECe against Table 6.2 automatically — this table is fully
bounded, no ambiguity remains.

**Chart type:** A horizontal bar or gauge per sample showing ECe against the five classification
bands (color-coded by class) works well now that the bands are confirmed. Also present the
underlying numbers in a table (Sample, EC(1:5), MF entered, ECe, Class) matching the
spreadsheet's layout.

**Explanation:**
- "This estimates the salinity of the soil (ECe) from a quick conductivity test (EC 1:5),
  adjusted for soil texture using a standard multiplication factor. Salinity affects plant
  growth, concrete durability, and corrosion risk, and is a standard part of site
  characterisation for reactive or saline sites."
- Note in the UI that MF is user-entered based on the Table 6.1 texture description, since it
  reflects a field/visual assessment of the soil, not something derived from lab numbers.

---

## Implementation notes for Claude Code

1. **Don't hardcode chart colors/fonts arbitrarily** — match the existing PDF report style
   (clean, black axis labels, blue data line/markers) since that's the visual language the
   user's clients already expect.
2. Every calculated value (PI, Is50, exposure class, ECe) should show its formula and inputs
   next to the result — not just the output — per the user's explicit request for
   "explanation and calculation steps."
3. Shrink-Swell Index (ISS) is explicitly **out of scope** — not needed per the user, don't
   implement it even though it appeared in the source spreadsheet.
4. All eight sections are now fully specified with confirmed reference tables (AS 2159-2009 for
   Section 7, Richards 1954 tables for Section 8) — no open questions remain. Build with
   confidence directly from this document.
5. This spec intentionally excludes borehole log auto-commenting — that's a distinct, later
   feature once parsing + charts + explanations are solid.
