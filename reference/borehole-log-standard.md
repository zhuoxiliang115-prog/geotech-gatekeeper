# Borehole Log Standard

This document is the yardstick Phase 2's review/markup feature will check parsed
borehole log data against. It does not itself check anything — it defines what
"correct" means, for a rule-checking engine (and, where the rules run out, for
an LLM reviewer) to be built against later.

It has two parts that behave differently, and the rest of this document keeps
them apart:

- **Terminology & classification** (Part 3) is fixed. It's transcribed from
  AECOM's own AS1726-2017 description sheets. It doesn't change unless AECOM
  issues a new revision of that document.
- **Structural completeness** (Part 2) is derived by observation from the
  example logs actually on file. It's a description of what today's examples
  do, not a specification handed down by a standard - AECOM's description
  sheets say nothing about which header fields a Pavement Dip log must carry.
  It is expected to be wrong at the margins and to improve as more approved
  examples arrive.

---

## 1. How this was generated

**Source files:**

| Source | Informed |
|---|---|
| `reference/logs/Chowder bay logs combined.pdf`, pages 1-6 ("Soil & Rock Description Sheets", AECOM, AS1726-2017, revision 30/6/2017) | Part 3 (Terminology & classification reference), in full |
| All 15 PDFs in `reference/logs/` (Borehole, Cored Borehole, Pavement Dip, and Test Pit logs from the PRUP/TfNSW Picton Road project, the WSM/Sydney Water Willoughby project, Heathcote Road, Alex Canal, and Chowder Bay DFI) | Part 2 (Structural completeness checklist), by cross-referencing header fields and table columns actually present |
| `backend/app/parsers/borehole_log.py` and its build notes (this repo's prior Claude Code session) | Part 4's "not rule-checkable without a parser" callouts, and the known parser-limitation notes threaded through Part 2 |

**Note on the description-sheets file location:** the request that produced
this document named the source as
`reference/borehole-logs/AECOM-soil-rock-description-sheets.pdf`. No such
path exists in the repository. The content it describes - AECOM's 6-page
"Soil & Rock Description Sheets" - is instead the first 6 pages of
`reference/logs/Chowder bay logs combined.pdf` (confirmed by title match on
every page: "Soil & Rock Description Sheets", AECOM letterhead, "Soil and
Rock Description 2017 (incorporating AS1726-2017), Revision Date 30/6/2017").
That's the source actually used. If a standalone copy is added later at the
originally-named path (or anywhere else), point the regeneration process at
it instead - the content should be identical since it's the same firm
document, but confirm the revision date hasn't changed.

**Process used:**

1. The 6 description-sheet pages were rendered to images (250 DPI, via
   PyMuPDF) and read as images, not extracted as text. This matters: like the
   log files themselves, these pages are dense tables, and pdfplumber's text
   extraction garbles column alignment badly enough to misattribute values
   across columns. Every table in Part 3 was transcribed by reading the
   rendered page image directly.
2. For the structural checklist, `backend/app/parsers/borehole_log.py`'s own
   header regex (`Engineering Log (Cored Borehole|Borehole|Pavement Dip|Test
   Pit) No.`) was reused to classify every page across 12 of the 15 log PDFs
   (excluding the three largest - Alex Canal, Heathcote, Chowder Bay
   combined - from the full field-presence survey for runtime reasons; their
   first few pages were sampled directly instead and confirmed to follow the
   same templates found elsewhere, introducing no new log type). A small
   standalone script (not part of the shipped parser) then checked, per log
   type, what fraction of pages contained each candidate header-field label
   and each candidate field-test token (SPT/PP/BS/DCP/etc.) - 203 log pages
   surveyed in total (Pavement Dip 34, Test Pit 21, Borehole 58, Cored
   Borehole 90). Column layouts (which table columns exist per type) were
   confirmed by reading each type's rotated/reversed column-header row
   directly from word coordinates (the same technique the parser uses),
   sampled on one representative page per type.
3. Every field or column claimed "required" in Part 2 was seen at 100% (or
   noted otherwise) across its type's surveyed pages - not assumed from a
   single example.

**How to refresh this document when new example logs arrive:**

The user has deliberately not built a live example-upload feature into the
app for this - new approved logs arrive by being added to `reference/logs/`
via GitHub, same as the current 15 did. To regenerate this document in a
future session:

1. Ask Claude Code to re-run the classification + field-presence survey
   described in step 2 above across the full current contents of
   `reference/logs/` (old files plus whatever's new).
2. Compare the new per-type field/column presence numbers against the
   tables in Part 2. Anything that drops below 100% that was previously
   listed "required" should be downgraded (with a note of which example
   broke the pattern); anything new appearing consistently should be added.
3. Part 3 only needs to change if AECOM issues a new revision of the
   description sheets (check the revision date on the source file's footer -
   currently 30/6/2017) - it is not affected by new *log* examples.
4. Re-check whether new examples introduce a fifth log type beyond
   Borehole/Cored Borehole/Pavement Dip/Test Pit (all 15 files on hand as of
   this writing map onto exactly those four - see the file-to-type table in
   Part 2).
5. Do not fold this into `borehole_log.py`. This document and the parser
   are deliberately separate: the parser extracts, this document judges.
   Phase 2 combines them.

---

## 2. Structural completeness checklist

Confirmed log types, from every file currently in `reference/logs/`:

| File | Log type(s) found | Holes |
|---|---|---|
| `PRUP_AC Logs.pdf` | Pavement Dip | PRUP_AC01-08 (L/S pairs) |
| `PRUP_CC Logs.pdf` | Pavement Dip | PRUP_CC01-04 |
| `PRUP_PC Logs.pdf` | Pavement Dip | PRUP_PC01-16 |
| `PRUP_TP Logs.pdf` | Test Pit | PRUP_TP01-02 |
| `PRUP_PTP Logs.pdf` | Test Pit | PRUP_PTP01-20 |
| `PRUP_HA Logs.pdf` | Borehole (hand auger method) | PRUP_HA01-34 |
| `PRUP_BH Logs.pdf` | Borehole, Cored Borehole | PRUP_BH01-03 |
| `WSM_ BH Logs FINAL.pdf` | Borehole, Cored Borehole | WSM_BH01-11 (+ A/B/C sub-holes) |
| `WSM_BH12_20260819.pdf` … `WSM_BH15_20260720.pdf` | Borehole, Cored Borehole | WSM_BH12-15 |
| `Alex Canal.pdf` | Borehole | (sampled: same AECOM template, no new type) |
| `Heathcote.pdf` | Borehole, Cored Borehole | BH01 (sampled) |
| `Chowder bay logs combined.pdf` | Borehole, Cored Borehole, plus the description-sheet pages (1-6) | 19 Cored Borehole + 16 Borehole sheets |

Two more page types appear throughout but carry no header fields or table
data, so they're out of scope for the field/column checklist below - they're
noted here so a future reviewer doesn't mistake them for parse failures:

- **Photo report pages** - titled `PHOTO REPORT ID NO. <hole>` (Borehole/
  Cored Borehole), `PAVEMENT DIP PHOTO REPORT PAVEMENT DIP NO. <hole>`, or
  `TEST PIT PHOTO REPORT TEST PIT NO. <hole>` depending on log type, produced
  by OpenGround. One to a few per hole. No structured fields - photos plus a
  handful of caption strings (e.g. `SPT -2.00 to 2.45 m`).
  **Parser note:** `borehole_log.py`'s `classify_log_page` currently
  recognises only the Borehole-style title (`PHOTO REPORT ID NO.`) - the
  Pavement Dip and Test Pit title variants fall through to
  `PAGE_TYPE_UNRECOGNIZED` instead of `PAGE_TYPE_PHOTO_REPORT`. This is a
  real, minor gap discovered while building this document; per this phase's
  scope it is documented here rather than fixed in the parser.
- **Description sheet pages** - the AECOM explanatory content itself (Part
  3's source). Appears once as a 6-page insert in `Chowder bay logs
  combined.pdf`; not observed standalone or repeated per-hole in any other
  file on hand.

### 2.1 Borehole

Surveyed: 58 pages across `PRUP_HA`, `PRUP_BH`, `WSM_ BH Logs FINAL`,
`WSM_BH12`-`15`.

**Required header fields (100% of surveyed pages):**

| Field | Notes |
|---|---|
| Hole ID | from the title line, `Engineering Log Borehole No. <id>` |
| Sheet X of Y | |
| Client | |
| Project No. | |
| Project | |
| Logged by | |
| Checked by | |
| Location | |
| Start Date | |
| End Date | |
| Driller | |
| Hole Diameter | |
| Easting | |
| Northing | |
| RL | |
| Drill Rig | |
| Inclination | |
| Vertical Datum | |
| Total Depth | |
| Bearing | |
| Horizontal Datum | |
| Surface | |
| "ADDITIONAL OBSERVATIONS (Geological Origin)" column caption | present even when no observations are logged on a given sheet |

**Inconsistently present:**

- **Location Meth.** - present on 42/58 (72%) of surveyed Borehole pages.
  Not a sheet-number effect (verified: present on every sheet of a hole, or
  absent from every sheet of a hole, never mixed within one hole) and not
  cleanly a per-client rule either (present throughout PRUP/TfNSW and
  Heathcote/TfNSW; present in Alex Canal, whose client is Sydney Water;
  absent throughout the WSM_BH*/Sydney Water Willoughby set). Treat as
  optional - flag its absence for awareness, not as a defect.

**Table columns** (soil-description page layout):

METHOD · SUPPORT · FIELD TESTS/SAMPLES & WATER · GROUND WATER (RL, AHD, m) ·
DEPTH (m) · GRAPHIC LOG · CLASSIFICATION SYMBOL · MATERIAL DESCRIPTION ·
MOISTURE CONDITION / CONSISTENCY-RELATIVE DENSITY · ADDITIONAL OBSERVATIONS
(Geological Origin)

**Field test / sample presence:** 14/58 (24%) of surveyed Borehole pages
carry at least one SPT/U/BS/DS token. This is expected, not a gap: many
sheets are continuation sheets below the depth where SPTs are still being
taken, or (for the 35 `PRUP_HA` "hand auger" pages specifically) hand-auger
holes that never carry SPT at all - hand augering can't drive a standard
penetration test. A missing SPT column entry is only worth flagging on a
sheet whose depth range plausibly still permits sampling.

**Known parser limitation:** the depth axis (tick labels `0.0, 1.0, 2.0...`)
calibrates correctly for this template's column positions.

### 2.2 Cored Borehole

Surveyed: 90 pages across `PRUP_BH`, `WSM_ BH Logs FINAL`, `WSM_BH12`-`15`.

**Required header fields:** identical set to Borehole (§2.1), all at 100%.
Location Meth. present on 28/90 (31%) - same non-clean split as Borehole.

**Table columns** (rock-core page layout - materially different from the
soil layout, not just a variant):

METHOD · **CORE RUN** (depth-from/depth-to and run number, replaces
SUPPORT) · FIELD TESTS/SAMPLES & WATER · GROUND WATER (RL, AHD, m) · DEPTH
(m) · GRAPHIC LOG · MATERIAL DESCRIPTION · **WEATHERING / INFERRED STRENGTH
(20×Is₍₅₀₎, symbols A:● D:o UCS:□) / TCR (%) / [RQD] / (SCR)** · **DEFECT
SPACING (mm)**, banded SOIL/VL/L/M/H/VH/EH at 20/60/200/600/2000mm ·
ADDITIONAL OBSERVATIONS (Defect Descriptions)

No CLASSIFICATION SYMBOL or MOISTURE CONDITION/CONSISTENCY-RELATIVE DENSITY
columns - both are soil-specific concepts, absent once material is
solid rock. Point load (Is₍₅₀₎ D=/A=) and UCS readings appear in the same
FIELD TESTS/SAMPLES column soil boreholes use for SPT - 0/90 surveyed pages
carry an SPT/U/BS/DS token, confirming SPT genuinely never appears once a
hole is cored.

**Known parser limitation:** `borehole_log.py`'s depth-axis calibration
(`COLUMN_RANGES["depth"] = (145, 165)`) returned `depth_axis_calibrated:
false` for all 90/90 surveyed Cored Borehole pages. Root cause, confirmed by
reading the reversed column-header word positions directly: the "DEPTH"
column header sits further left on Cored Borehole pages (x≈130) than on
Borehole pages (x≈147-154) to make room for the wider rock-specific columns
on the right, shifting the actual tick-value words outside the parser's
hardcoded column range. Strata text is still extracted; only the
depth-from-position estimate is unavailable on this page type.

### 2.3 Pavement Dip

Surveyed: 34 pages across `PRUP_AC`, `PRUP_CC`, `PRUP_PC`.

**Required header fields (100%):** Hole ID (`Engineering Log Pavement Dip
No. <id>`), Sheet X of Y, Client, Project No., Project, Logged by, Checked
by, Location, **Location Meth.**, Start Date, End Date, Driller, Hole
Diameter, Easting, Northing, RL, Drill Rig, Inclination, Vertical Datum,
Total Depth, Bearing, Horizontal Datum, Surface, "ADDITIONAL OBSERVATIONS
(Geological Origin)" caption.

Unlike Borehole, Location Meth. was present on **100%** of surveyed
Pavement Dip pages (all three files) - worth re-checking as more examples
arrive, since Borehole's split suggests this field isn't universally
guaranteed.

**Table columns:** METHOD · SUPPORT · (BLOWS DCP PER 100mm) · GROUND WATER ·
FIELD TESTS/SAMPLES (sample prefix seen: `C:` with a depth range - a cut/core
sample) · RL (AHD, m) · DEPTH (m) · GRAPHIC LOG · CLASSIFICATION SYMBOL ·
MATERIAL DESCRIPTION · MOISTURE CONDITION/CONSISTENCY-RELATIVE DENSITY ·
ADDITIONAL OBSERVATIONS (Geological Origin). Structurally the same column
set as Borehole, with DCP (Dynamic Cone Penetration) in place of SPT - a
Pavement Dip never carries an SPT token (0/34 surveyed), and PP (Pocket
Penetrometer) and BS (Bulk Sample) tokens appear on 100% and 100% of
surveyed pages respectively - these, not SPT, are this type's standard field
tests.

**Depth-axis calibration:** unlike Test Pit and Cored Borehole, Pavement
Dip's depth column sits inside the parser's existing column range and
calibrated successfully on 34/34 surveyed pages (confirmed via
`borehole_log.py` directly, not just the header-text survey).

### 2.4 Test Pit

Surveyed: 21 pages across `PRUP_TP`, `PRUP_PTP`.

**Required header fields (100%):** Hole ID (`Engineering Log Test Pit No.
<id>`), Sheet X of Y, Client, Project No., Project, Logged by, Checked by,
Location, Location Meth., Start Date, End Date, **Operator** (not Driller),
**Dimensions** (not Hole Diameter), **Plant** (not Drill Rig),
**Orientation** (not Inclination), Easting, Northing, RL, Vertical Datum
(printed `Ver Datum:`, no period - differs from Borehole/Pavement Dip's
`Ver. Datum:`), Total Depth, Horizontal Datum, Surface, "ADDITIONAL
OBSERVATIONS (Geological Origin)" caption. No Bearing field (a hand-dug pit
has no drilled bearing/inclination to record).

**Table columns:** METHOD · SUPPORT · GROUND WATER · (BLOWS DCP PER 100mm) ·
FIELD TESTS/SAMPLES (sample prefix seen: `B:` with a depth range - Bulk
sample) · RL (AHD, m) · DEPTH (m) · GRAPHIC LOG · CLASSIFICATION SYMBOL ·
MATERIAL DESCRIPTION · MOISTURE CONDITION/CONSISTENCY-RELATIVE DENSITY ·
ADDITIONAL OBSERVATIONS (Geological Origin). Same column set as Pavement
Dip; PP and BS tokens both appear on 100% of surveyed pages, DS
(disturbed sample) on 11/21 (52%), PID on 9/21 (43%) - situational, not
required. 0/21 carry an SPT token.

**Known parser limitation:** the DEPTH column sits noticeably further right
on Test Pit pages (tick-value words at x≈193) than on Borehole/Pavement Dip
pages (x≈145-154), outside `borehole_log.py`'s hardcoded column range -
`depth_axis_calibrated: false` on all 21/21 surveyed pages. Header and
field-test extraction are unaffected; only position-based depth estimates
for strata text are unavailable.

---

## 3. Terminology and classification reference

Source: AECOM "Soil and Rock Logging Explanatory Notes and Abbreviations",
Soil and Rock Description 2017 (incorporating AS1726-2017), Revision Date
30/6/2017. All tables below are transcribed as printed; nothing here is
inferred from the log examples.

**A note on vintage:** the source states AECOM logs prepared *before* July
2017 followed AS1726-1993, which classifies fine- vs coarse-grained soils
differently (on percentage passing 75 micron, not fines behaviour) and
gives different results for materials AS1726-2017 would call e.g. "sandy
CLAY" but 1993 called "silty SAND". Every example log currently in
`reference/logs/` is dated 2025-2026, so this doesn't currently bite - but
if an older or third-party log is ever added as an example, its
classification must not be checked against the 2017 rules below without
first confirming which revision it was logged under.

### 3.1 Description order convention

**Soil name** is built in this order: plasticity or particle characteristics
of the major component (capitalised); colour; structure; secondary and
minor components. The AS1726 Group Symbol, consistency/density, and
moisture condition are recorded in their own separate columns, not folded
into the name text. Geological origin (FILL, ALLUVIUM, etc.) and other
observations go in a separate column again.

**Rock name** order: grain size and type; colour; fabric and texture;
structure; minor components; bedding dip. Geological formation, rock
strength, weathering/alteration, mass defect spacing, and defect
descriptions are each recorded in their own columns.

**Defect description** order (rock only): Type; dip/direction; planarity;
roughness; infill/coating; colour. Example: `P,30/145°,PL,ro,1mm,CH,gy` =
a parting, 30° dip, 145° dip direction, planar, rough, 1mm infill of grey
high-plasticity clay. A healed defect is prefixed "healed" before the type.

Defect thickness distinctions: ≤10mm = *parting* or *joint*; 10-100mm
perpendicular to the defect = *seam* or *zone*; >100mm, or a defect
intersecting the full core width = logged as a new material strata, not a
defect.

### 3.2 Plasticity ↔ Liquid Limit

| Term | LL range |
|---|---|
| Low plasticity | ≤ 35% |
| Medium plasticity | > 35% and ≤ 50% |
| High plasticity | > 50% |

### 3.3 Colour abbreviations

| Term | Abbrev. | Term | Abbrev. |
|---|---|---|---|
| Brown | br | Yellow | yl |
| Grey | gy | Orange | or |
| Black | bk | Red | rd |
| White | wh | Pale | pl |
| Blue | bl | Dark | dk |
| Green | gr | Mottled | mtld |

Colour is assessed moist, using basic colours plus pale/dark/mottled
modifiers. Borderline colours combine two terms (e.g. "red-brown").

### 3.4 Moisture condition

| Term | Symbol | Cohesive | Granular |
|---|---|---|---|
| Dry | D | Hard/friable/powdery, very dry of plastic limit | Cohesion-less, free running |
| Moist | M, w<PL, w~PL, w>PL | Cool, darkened, moulds, w between PL and LL as indicated | Cool, darkened, tends to cohere |
| Wet | W, w~LL, w>LL | Cool, dark, usually weakened, free water, w at/above LL as indicated | Cool, darkened, cohere, free water |

### 3.5 Geological origin

| Category | Term | Description |
|---|---|---|
| Weathered in place | Extremely weathered material | Parent-rock structure/fabric visible (logged as a **soil**, with soil terminology) |
| Weathered in place | Residual Soil | Parent-rock structure/fabric not visible |
| Transported | Aeolian soil | Deposited by wind |
| Transported | Alluvial soil | Deposited by streams/rivers |
| Transported | Colluvial soil | Deposited on slopes |
| Transported | Lacustrine soil | Deposited by lakes |
| Transported | Marine soil | Deposited in oceans/bays/beaches/estuaries |
| — | TOPSOIL | Surface/near-surface mantle, often but not always high organic content (prefix) |
| — | FILL | Soil/rock/refuse placed by humans, controlled or uncontrolled (prefix) |

Where origin is uncertain, "possibly" or "probably" qualifies the term.

### 3.6 Organic and artificial material

- **> 25% organic**: PEAT (e.g. "sandy PEAT").
- **2-25% organic**: prefixed "Organic" (e.g. "Organic CLAY").
- Organic matter described with terms: fibrous peat, charcoal, wood
  fragments, roots (>2mm dia.) or root fibres (<2mm dia.).
- **Any evidence of human placement** (compacted embankment, artificial
  material) is prefixed FILL. Waste fill terms: domestic refuse, oil,
  bitumen, brickbats, concrete rubble, fibrous plaster, wood pieces/
  shavings, sawdust, iron filings, drums, steel bars/scrap, bottles, broken
  glass, leather.
- Organic/artificial material can't be adequately described with soil
  classification terms - use qualitative frequency terms instead ("rare",
  "occasional", "frequent"), e.g. "SAND with rare gravel size brick
  fragments". These are relative; no percentage is defined for them - this
  is a documented reason a rule engine cannot score them numerically (see
  Part 4).
- **Cobbles/boulders** (>200mm boulders, 63-200mm cobbles) are oversize:
  removed before describing the soil, then the description is prefixed
  "MIXTURE OF SOIL AND COBBLES/BOULDERS" (word order = dominant proportion
  first), with the oversize proportion noted separately.

### 3.7 Structure terms

intact (no joints) · fissured (closed joints) · voided · vesicular ·
slickensided (sheared) · interbedded · laminated · cemented

### 3.8 Grain size

| | Clay | Silt | Sand F | Sand M | Sand C | Gravel F | Gravel M | Gravel C | Cobbles |
|---|---|---|---|---|---|---|---|---|---|
| Size | <2 µm | 2-75 µm | 0.075-0.21mm | 0.21-0.6mm | 0.6-2.36mm | 2.36-6.7mm | 6.7-19mm | 19-63mm | 63-200mm |
| Field guide | Shiny, not visible <10x | Dull, visible <10x | Visible by eye | Visible <1m | Visible <3m | Visible <5m | Road gravel | Rail ballast | Beaching |

Boulders (>200mm) and cobbles (63-200mm) are oversize (see §3.6).

**Grain shape:** angular / sub-angular / sub-rounded / rounded (equi-
dimensional particles). Essentially 2-D particles: "flaky"/"platy".
Essentially 1-D: "elongated".

### 3.9 Relative density (non-cohesive soils)

| Term | Symbol | Density index | Uncorrected SPT N | Field guide |
|---|---|---|---|---|
| Very Loose | VL | ≤15% | 0-4 | Ravels |
| Loose | L | >15% ≤35% | 4-10 | Shovels easily |
| Medium Dense | MD | >35% ≤65% | 10-30 | Shovelling very difficult |
| Dense | D | >65% ≤85% | 30-50 | Pick required |
| Very Dense | VD | >85% | >50 | Pick difficult |

AECOM's own caveat: this SPT correlation is "a rough field guide for clean,
dry, fine to medium sands at a depth of 5 to 15m" (Gibbs & Holtz 1957) -
correlations vary with grain size, angularity, overburden, moisture, fines,
cementation and SPT efficiency. Treat mismatches as a flag to review, not
an automatic fail (see Part 4).

### 3.10 Consistency (cohesive soils)

| Term | Symbol | Undrained shear strength (kPa) | Approx. SPT N | Field guide |
|---|---|---|---|---|
| Very Soft | VS | ≤12 | 0-2 | Exudes between fingers when squeezed |
| Soft | S | >12 ≤25 | 2-4 | Moulded by light finger pressure |
| Firm | F | >25 ≤50 | 4-8 | Moulded by strong finger pressure |
| Stiff | St | >50 ≤100 | 8-15 | Cannot be moulded by fingers; indented by thumb |
| Very Stiff | VSt | >100 ≤200 | 15-30 | Indented by thumbnail |
| Hard | H | >200 | >30 | Indented with difficulty by thumbnail |

Same caveat as §3.9: "SPT is not a direct measure of consistency" - a rough
guide only.

### 3.11 Full soil classification (AS1726-2017)

**Coarse grained** (>65% of coarse fraction >2.36mm = GRAVEL; >50% <2.36mm =
SAND; major component assessed after removing >63mm oversize):

| Group Symbol | Field ID | Typical name |
|---|---|---|
| GW | Wide grain-size range, substantial intermediate sizes, no dry strength, <5% fines | Well graded GRAVEL or sandy GRAVEL |
| GP | Predominantly one size/range, some sizes missing, <5% fines | Poorly graded GRAVEL or sandy GRAVEL |
| GM | "Dirty", excess non-plastic fines, zero-medium dry strength, ≥12% fines | silty GRAVEL or silty sandy GRAVEL |
| GC | "Dirty", excess plastic fines, medium-high dry strength, ≥12% fines | clayey GRAVEL or clayey sandy GRAVEL |
| SW | Wide grain-size range, substantial intermediate sizes, no dry strength, <5% fines | Well graded SAND or gravelly SAND |
| SP | Predominantly one size/range, some sizes missing, <5% fines | Poorly graded SAND or gravelly SAND |
| SM | "Dirty", excess non-plastic fines, ≥12% fines | silty SAND |
| SC | "Dirty", excess plastic fines, ≥12% fines | clayey SAND |

Lab criteria: GW/SW need Cᵤ≥4 (GW) or ≥6 (SW) and Cc=1-3
(Cᵤ=D₆₀/D₁₀, Cc=D₃₀²/(D₁₀×D₆₀)); GM/GC/SM/SC need ≥12% fines, split below/
above the A-line. Secondary/minor descriptors: >30% coarse grains -
"sandy"/"gravelly" prefix; >15% ≤30% - "with sand/gravel"; ≤15% - "trace
sand/gravel". Fine-grains split at >12% (fines descriptor), >5% ≤12%, ≤5%.

**Fine grained** (≥35% of material <63mm passes 0.075mm; classified on fines
behaviour, not fines percentage - see §3 vintage note):

| Group Symbol | LL | Dry strength / dilatancy / toughness | Typical name |
|---|---|---|---|
| MH | >50% | Low-medium / none-slow / low-medium | Inorganic SILT, gravelly/sandy SILT |
| ML | ≤50% | None-low / slow-rapid / low | Inorganic SILT, very fine sand, rock flour, silty/clayey fine sand or silt |
| OL | ≤50% | Low-medium / slow / low | Organic SILT (2%<organics<25%) |
| ML-CL | ≤35% | Low-medium / none-slow / low-medium | clayey SILT (borderline) |
| CH | >50% | High-very high / none / high | Inorganic CLAY, sandy/gravelly CLAY |
| CI | >35% ≤50% | Medium-high / none-slow / medium | Inorganic CLAY, sandy/gravelly CLAY |
| CL | ≤35% | Medium-high / none-slow / medium | Inorganic CLAY, sandy/gravelly CLAY |
| OH | >35% | Medium-high / none-very slow / low-medium | Organic CLAY (2%<organics<25%) |
| Pt | (>25% organic by dry weight) | Identified by colour, odour, sponge feel, fibrous texture | PEAT, sandy PEAT |

The A-line (Modified Casagrande Chart) divides CL/CI/CH from ML/OL and
MH/OH: **PI = 0.73×(LL − 20)**. "CL-ML" borderline zone: LL≤35, PI 4-7
(matches `AtterbergChart.jsx`'s existing implementation). Secondary/minor
descriptors for fine-grained soils mirror the coarse-grained convention
("sandy"/"gravelly" >30%, "with sand/gravel" 15-30%, "trace sand/gravel"
≤15%); secondary fine-grained soil not otherwise described is "clayey
SILT".

**Boundary classification:** soils with characteristics of two groups use a
combined symbol, e.g. `GP-GC` (gravel, 5-12% clay fines) or `CI-CH` (medium-
to-high borderline plasticity) - this is the same dual-symbol format the
example logs actually use (`CI-CH`, `CL-ML`, `SC-`, etc.).

### 3.12 Rock type, grain size, and structure

| Grain size / spacing | Soil-grain-size term | Sedimentary (deposited) | Sedimentary (≥90% carbonate) | Metamorphic (foliated) | Metamorphic (non-foliated) |
|---|---|---|---|---|---|
| >2m / 0.6-2m / 0.2-0.6m | large/medium/small BOULDERS | CONGLOMERATE or BRECCIA | CALCIRUDITE / LIMESTONE / DOLOMITE | GNEISS | MARBLE / QUARTZITE / SERPENTINITE / HORNFELS |
| 60-200mm | COBBLES | " | " | " | " |
| 20-60 / 6-20 / 2-6mm | coarse/medium/fine GRAVEL | SANDSTONE/GREYWACKE/ARKOSE/QUARTZOSE SANDSTONE | CALCARENITE | SCHIST | " |
| 0.6-2.0 / 0.2-0.6 / 0.06-0.2mm | coarse/medium/fine SAND | " | " | " | " |
| 2-60 µm | SILT | MUDSTONE/SHALE/LAMINITE, SILTSTONE | CALCISILTITE | PHYLLITE/SLATE | " |
| <2 µm | CLAY | CLAYSTONE | CALCILUTITE | " | " |

Volcanic ejecta (any grain size): AGGLOMERATE or VOLCANIC BRECCIA (coarse),
TUFF (medium/fine). Impure carbonate (50-90%) is prefixed "IMPURE"; ≥90%
uses the plain rock name.

**Defect spacing:** Very Wide (VW) / Wide (W) / Medium (M) / Close (C) /
Very Close (VC) / Extremely Close (EC) - maps to bedding thickness terms
Very Thickly Bedded through Very Thinly Laminated.

**Igneous rocks (grain size × felsic/mafic):** COARSE: GRANITE/DIORITE/
GABBRO; MEDIUM: MICROGRANITE/MICRODIORITE/DOLERITE; FINE: RHYOLITE/
ANDESITE/BASALT. Notes: PEGMATITE (large crystals, dyke/vein), VOLCANIC
GLASS/OBSIDIAN (glassy), APLITE (light quartz/feldspar veins), PORPHYRY
(large crystals in finer matrix).

**Duricrust** (soils cemented to rock): FERRICRETE (iron oxide), SILCRETE
(silica), GYPCRETE (salt), CALCRETE (CaCO₃, replacement-dominated). Mass
grade: DI (massive/hardspan, >90% continuous), DII (vuggy/patchy, 50-90%),
DIII (nodular/fragmental, <50%, logged as soil).

### 3.13 Rock strength

| Term | Symbol | UCS (MPa) | Is₍₅₀₎ (MPa) | Field guide |
|---|---|---|---|---|
| Soil | soil | ≤0.6 | – | logged as soil, using consistency |
| Very Low | VL | >0.6 ≤2 | >0.03 ≤0.1 | Crumbles under firm pick blow; peeled with knife |
| Low | L | >2 ≤6 | >0.1 ≤0.3 | Scored with knife; 1-3mm indent with pick |
| Medium | M | >6 ≤20 | >0.3 ≤1 | Readily scored with knife; core breaks by hand with difficulty |
| High | H | >20 ≤60 | >1 ≤3 | Core doesn't break by hand; breaks with one firm pick blow |
| Very High | VH | >60 ≤200 | >3 ≤10 | Hand specimen breaks with pick after >1 blow |
| Extremely High | EH | >200 | >10 | Requires many pick blows |

Notes: strength should use UCS on near-in-situ-moisture material; Is₍₅₀₎ only
where UCS isn't practical; UCS is typically 10-20× Is₍₅₀₎ but the multiplier
varies widely by rock type - **not** a fixed conversion factor to rule-check
against (see Part 4).

### 3.14 Degree of weathering / alteration

| Term | Symbol | Description |
|---|---|---|
| Residual Soil | RS | Parent rock structure/fabric not visible |
| Extremely Weathered/Altered | XW / XA | Has soil properties; mass structure/fabric still visible; logged as a soil |
| Highly Weathered/Altered | HW / HA | Whole rock discoloured, original colour unrecognisable, strength changed |
| Distinctly Weathered/Altered | DW / DA | Used when HW/HA vs MW/MA can't be distinguished by strength |
| Moderately Weathered/Altered | MW / MA | Discoloured, original colour unrecognisable, little/no strength change |
| Slightly Weathered/Altered | SW / SA | Partially discoloured (staining along joints if weathering), little/no strength change |
| Fresh | FR | No decomposition or colour change |

Weathering = surface exposure effects; alteration = hot liquid/gas at
depth - the distinction matters because their spatial distribution differs.

### 3.15 Rock defects

| Symbol | Term | Definition |
|---|---|---|
| P | Parting | Surface/crack parallel to bedding/cleavage, little/no tensile strength |
| J | Joint | Surface/crack, no shear displacement, not parallel to bedding |
| S | Sheared Surface | Smooth/polished/slickensided, shows shear displacement |
| SZ | Sheared Zone | Roughly parallel boundaries cut by close joints/shears, lenticular blocks |
| MB | Mechanical Break | Not natural - drilling, testing, storage |
| SH | Sheared Seam | Roughly parallel boundaries cut by close joints/cleavage |
| CR | Crushed Seam | Roughly parallel boundaries, mainly angular host-rock fragments |
| NF | Infilled Seam | Distinct parallel boundaries, infill from soil migration into joints |
| EW | Extremely Weathered Seam | Soil substance weathered from host rock |
| SS | Soil Seam | Used where origin (SH/CR/NF/EW) can't be determined |

Sheared surfaces/zones/seams and crushed seams are "generally faults in
geological terms". Healed defects are prefixed "healed".

**Planarity:** PL planar / CU curved / UN undulating / ST stepped / IR
irregular. **Roughness:** vr very rough / ro rough / sm smooth / po polished
/ sl slickensided.

**Infill/coating:** cn clean / sn stained / vn veneered / co coated / op
open-voided / Ca calcium carbonate / Fe iron oxide / Ch chlorite / Qz
quartz.

**Vesicularity:** D dense (negligible porosity) / NV non-vesicular (<10%) /
SV slightly vesicular (10-20%) / HV highly vesicular (>20%).

**Carbonate content:** <~50% (weak/sporadic effervescence in 10% HCl) =
prefixed "Calcareous"; >50% = prefixed "Carbonate"; ≥90% carbonate
sedimentary rocks use the rock-type name directly (§3.12); 50-90% prefixed
"IMPURE".

### 3.16 Field sampling and testing abbreviations

| Symbol | Meaning | | Symbol | Meaning |
|---|---|---|---|---|
| V | Uncorrected Borehole Vane Shear (kPa), Peak/Residual | | UP | Undisturbed Piston Sample |
| HV | Uncorrected Hand Vane Shear (kPa), Peak/Residual | | DS | Disturbed Sample |
| PP | Pocket Penetrometer (kPa) | | BS | Bulk Sample |
| SPT | Standard Penetration Test | | E | Environmental Sample |
| N | Uncorrected SPT blow count / 300mm | | RQD | Rock Quality Designation (%) |
| N* | SPT with sample collected | | SCR | Solid Core Recovery (%) |
| RW | SPT rod weight only (N<1) | | TCR | Total Core Recovery (%) |
| HW | SPT rod + hammer weight (N<1) | | DCP | Dynamic Cone Penetration (blows/100mm) |
| HB | SPT Hammer Bouncing | | PSP | Perth Sand Penetrometer (blows/150mm) |
| FPM | Field Permeability | | PID | Photoionization Detector |
| Lu | Lugeon/Packer Test (L/m/min) | | U(X) | Undisturbed Sample, X mm diameter |
| Is₍₅₀₎(A/D/I) | Axial/Diametral/Irregular Point Load Strength Index (MPa) | | | |

**Water:** ▼ static water level · ▽ water level during drilling · ▷ inflow ·
◁ outflow · ◄ complete water loss.

**Drilling method:** ADV auger V-bit (100mm) · AS auger screwing · WB wash
boring · B blank bit* · T tungsten carbide bit* · RR rock roller/tricone ·
DHH down-hole hammer · PD percussion · CT cable tool · HA hand auger · DT
diatube (114mm) · NMLC triple-tube core (50mm) · NQ3/HQ3/PQ3 wireline
triple-tube (45/61/83mm) · NQ/HQ/PQ wireline double-tube (48/64/85mm) · RC
reverse circulation · CA casing advancer · VC vibro coring · SC sonic coring
· GP Geoprobe continuous sampling. (*bit symbol suffixes the method, e.g.
ADV = auger drilling with V-bit.)

**Drilling support:** U unsupported · C casing · M mud · W water.

---

## 4. Rule-checkable vs. judgment-based vs. not checkable

### 4.1 Rule-checkable (deterministic - Phase 2's rule engine can score these directly)

- **Required header fields present**, per log type (Part 2's per-type
  tables). A missing field on a page classified as that log type is a
  binary check.
- **Required table-column captions present** for the log type (Part 2).
- **Valid abbreviation used**, checked against the fixed lookup tables in
  Part 3: colour (§3.3), moisture symbol (§3.4), relative density symbol
  (§3.9), consistency symbol (§3.10), USCS group symbol (§3.11), weathering/
  alteration symbol (§3.14), defect type/planarity/roughness/infill symbols
  (§3.15), field-test/sample/drilling-method symbols (§3.16). An abbreviation
  not in the table is either a typo or an undocumented convention - either
  way, flaggable.
- **Plasticity term matches stated/lab LL%** (§3.2): "medium plasticity"
  paired with a lab LL of 30% is a direct contradiction. Requires the
  Atterberg lab-report parser's output alongside the log, when a lab test
  exists for the same sample - a concrete cross-parser check for Phase 2.
- **USCS group symbol consistent with LL/PI position on the A-line**
  (§3.11): given LL and PI (from a paired lab result), the symbol implied by
  PI = 0.73×(LL−20) is computable and comparable to the symbol printed on
  the log. `frontend/src/calculations.js` already implements this line.
- **Grading-curve group symbol criteria** (Cᵤ, Cc thresholds, §3.11) for
  GW/GP/SW/SP, when paired with the existing PSD parser's output for the
  same sample.
- **Defect description field order and format** (§3.1): a syntactic check
  that a defect description follows Type;dip/direction;planarity;roughness;
  infill/coating;colour, not a check on whether the description is
  geologically apt.
- **Boundary-symbol format** (§3.11): dual symbols follow the `XX-YY`
  pattern seen in both the standard and the examples.
- **Rock strength band consistency**: given a UCS or Is₍₅₀₎ value, the
  strength term (§3.13) it implies is computable and comparable to the
  logged term - with the explicit caveat from §3.13 that the UCS:Is₍₅₀₎
  ratio itself varies too widely to rule-check directly.

### 4.2 Judgment-based (LLM-assisted, report with stated uncertainty)

- **Whether the field-ID description (dry strength/dilatancy/toughness
  language) matches the assigned USCS symbol** - §3.11's field-ID columns
  are qualitative prose ("readily scored with a knife"), not machine-
  checkable thresholds; an LLM reading the description against the symbol
  is doing real classification judgment, not lookup.
- **Whether secondary/minor-component wording follows the prefix convention
  correctly** (§3.6, §3.11) in free-text descriptions - the *rule* (>30%
  "sandy", 15-30% "with sand", ≤15% "trace sand") is precise, but nothing in
  the parsed output currently states the actual percentage the logger
  observed in the field, only the word they chose - so this is closer to
  "does the prose read as internally consistent" than a number comparison.
- **Whether SPT-N vs. consistency/density term correlation looks
  reasonable** (§3.9, §3.10) - AECOM's own sheet calls this "a rough field
  guide" affected by grain size, angularity, overburden, moisture, fines,
  and cementation. A mismatch is a prompt to look closer, not a defect.
- **Whether a geological-origin term (FILL, ALLUVIUM, RESIDUAL...) is
  plausible** given the described material, depth, and site context.
- **Cross-sheet strata continuity** ("Log continued on/from" pages) -
  whether the described material at the bottom of one sheet plausibly
  matches the top of the next.
- **Colour-term plausibility** for combination/borderline colours.

### 4.3 Not checkable at all with what's currently on hand

- **Whether a classification is actually geologically correct for the
  ground it describes.** Every example the standard is built from is an
  already-approved log. There are no paired wrong/right examples - no case
  where a real log misclassified a soil and a corrected version exists to
  learn the failure mode from. A rule engine or LLM reviewer built from this
  document can confirm a log *uses valid terminology in valid formats
  consistent with itself*; it cannot confirm the description matches what
  was actually in the ground, because nothing in this repository represents
  ground truth independent of the loggers' own judgment.
- **Logging thoroughness or completeness of judgment calls** - e.g.,
  "should another sample have been taken here", "should this defect have
  been logged individually rather than generalised". These are professional
  judgment calls with no negative examples to calibrate against.
- **Distinguishing an unusual-but-correct entry from a genuine mistake.**
  Without labelled error cases, an outlier in the data (a rare abbreviation,
  an unusual combination) looks identical to a typo.
- **Firm-internal or project-specific conventions not written down here and
  not observable from the examples** - e.g. internal QA sign-off norms,
  informal shorthand a particular logger uses that isn't in AECOM's own
  abbreviation table.
- **Any log logged under AS1726-1993** (see the vintage note in Part 3) -
  none of the current examples are, but this document's classification
  rules would misjudge one if it appeared, since 1993 draws the fine/coarse
  boundary differently.
