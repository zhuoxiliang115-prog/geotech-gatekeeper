# Borehole Log Standard

This document is the yardstick Phase 2's review/markup feature will check parsed
borehole log data against. It does not itself check anything — it defines what
"correct" means, for a rule-checking engine (and, where the rules run out, for
an LLM reviewer) to be built against later.

It has two parts that behave differently, and the rest of this document keeps
them apart:

- **Terminology & classification** (Part 3) is fixed. It's transcribed from
  AECOM's own AS1726-2017 description sheets (current revision: 28/10/2025).
  It doesn't change unless AECOM issues a new revision of that document.
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
| `reference/borehole-logs/AECOM-soil-rock-description-sheets.pdf` ("AECOM Soil and Rock Logging Explanatory Notes and Abbreviations", Revision Date 28/10/2025 - the current revision) | Part 3 (Terminology & classification reference), in full |
| All 15 PDFs in `reference/logs/` (Borehole, Cored Borehole, Pavement Dip, and Test Pit logs from the PRUP/TfNSW Picton Road project, the WSM/Sydney Water Willoughby project, Heathcote Road, Alex Canal, and Chowder Bay DFI) | Part 2 (Structural completeness checklist), by cross-referencing header fields and table columns actually present |
| `backend/app/parsers/borehole_log.py` and its build notes (this repo's prior Claude Code session) | Part 4's "not rule-checkable without a parser" callouts, and the known parser-limitation notes threaded through Part 2 |

**Revision history of this source:** this document was first built against
the first 6 pages of `reference/logs/Chowder bay logs combined.pdf` - AECOM's
"Soil & Rock Description Sheets", Revision Date 30/6/2017 - because that was
the only copy on hand at the time, and the path originally requested
(`reference/borehole-logs/AECOM-soil-rock-description-sheets.pdf`) didn't
exist in the repository yet. A dated 28/10/2025 copy was subsequently
supplied at that exact path, and Part 3 below has been rewritten against it.
**The two revisions are not just a date change** - see the changelog at the
top of Part 3 for what's actually different. The 2017 copy embedded in
`Chowder bay logs combined.pdf` is left in place as-is (it's part of that
PDF's own content, not something this project owns to edit) but is now
superseded - don't transcribe from it again.

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
4. **Correction made during this revision:** the Pavement Dip and Test Pit
   field-test token counts in step 2 were originally computed with plain
   `if token in text` substring checks, which silently false-matched "BS"
   inside "OBSERVATIONS" and "DS" inside "SANDSTONE" - both came back
   showing 100%/high percentages that weren't real. Re-run with
   word-boundary/colon-anchored patterns (see §2.3, §2.4); the
   Borehole/Cored Borehole SPT survey used a colon-anchored pattern from the
   start and wasn't affected. Lesson for next time: never survey this
   template's `extract_text()` output with a bare substring check - anchor
   every token to a boundary or a following colon, or better, use
   `borehole_log.py`'s own coordinate-based column extraction instead.
5. **Second correction, user-flagged after the above:** the DCP ("Dynamic
   Cone Penetration") figures were *also* wrong even after the substring-bug
   fix, but for a different reason - the corrected search still checked for
   the literal word "DCP", which never prints next to a reading (DCP
   readings are bare integers under the column caption, same pattern as
   SPT-N). That produced a false "zero DCP readings anywhere", read at the
   time as "can't confirm from text" rather than recognised as "wrong
   question asked". Fixed by reading the field-tests column's actual
   numeric content by word position instead of searching for a label: 9/34
   Pavement Dip pages and 13/21 Test Pit pages (§2.3, §2.4) do carry DCP
   data, including a `blows/mm` partial-penetration format (e.g. `22/80`)
   parallel to SPT's refusal notation. Lesson for next time: when a column's
   caption names a test but its data rows are bare numbers (as with SPT-N
   and DCP alike), search for the *shape* of the data (a run of plain
   integers, or `N/mm`) in that column's coordinates - not for the test
   name as a text token, which will never appear per-row.
6. **User-confirmed correction to Part 3's Defect Type table:** the
   MB/DL/DB/HB row was wrong - three symbols had been merged into one
   shared definition and HB was missing entirely. Confirmed directly by the
   user against OpenGround (the software that generates these logs, treated
   as authoritative over the static AECOM PDF where they conflict): MB, DL,
   DB, and HB are four separate codes (Mechanical Break / Drill Lift /
   Drilling Break / Handling Break). Fixed in §3.15. The user also
   spot-checked Surface Roughness, Surface Shape/Planarity, and Infill/
   Coating against OpenGround directly and confirmed all three already
   matched Part 3 exactly - no changes needed there.

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
   description sheets (check the revision date on
   `reference/borehole-logs/AECOM-soil-rock-description-sheets.pdf`'s
   footer - currently 28/10/2025) - it is not affected by new *log*
   examples. When it does change, diff the new copy page-by-page against
   this document's Part 3 rather than assuming only the date moved - the
   28/10/2025 revision changed several abbreviations and table structures
   from the 30/6/2017 one with no other signal that anything besides the
   date had changed.
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
| `Chowder bay logs combined.pdf` | Borehole, Cored Borehole, plus the description-sheet pages (1-6, superseded 30/6/2017 copy - see `reference/borehole-logs/` for the current one) | 19 Cored Borehole + 16 Borehole sheets |

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
FIELD TESTS/SAMPLES (sample prefixes seen: `C:` with a depth range on 33/34
- **Core Sample**, per §3.16's `C / CONCC` entry - and `B:` on 13/34 -
**Bulk Sample**) · RL (AHD, m) · DEPTH (m) · GRAPHIC LOG · CLASSIFICATION
SYMBOL · MATERIAL DESCRIPTION · MOISTURE CONDITION/CONSISTENCY-RELATIVE
DENSITY · ADDITIONAL OBSERVATIONS (Geological Origin). Structurally the
same column set as Borehole, with a DCP column (Dynamic Cone Penetration)
in place of SPT's; PID readings appear on 5/34 pages.

**Correction - DCP data is present, an earlier pass just looked for the
wrong thing.** DCP readings don't print the word "DCP" next to each value -
same pattern as SPT-N, which prints bare blow counts, not "N: 9" - so the
original bare-substring search for the literal text "DCP" was checking for
something that was never going to appear per-row and reported a false
"zero". Re-checked by reading the field-tests column's actual numeric
content by word position (the same coordinate-based approach
`borehole_log.py` uses, not `extract_text()` substring search): **9/34
(26%) of surveyed Pavement Dip pages carry DCP readings** - runs of plain
integers (blow count per 100mm increment), up to 13 readings on one page.
Absence on the other 74% looks like genuine "DCP wasn't performed at this
hole" (e.g. `PRUP_AC01L`, a shallow asphalt coring to 0.4m with no DCP
data at all) rather than an extraction failure, but that's inferred, not
independently confirmed per hole.

**Partial-penetration format:** where a single blow drives the cone more
than 100mm, the reading isn't a clean whole number - it's printed as
`blows/mm`, e.g. `22/80` (found on `PRUP_PC` pages) meaning that many blows
achieved only 80mm of the 100mm increment. This is the DCP equivalent of
SPT's refusal notation (`10/50 mm HB N=R`). **`borehole_log.py` has no DCP
extraction at all currently** - it only parses `SPT:`/`D:`/`ES:`/`U:`
labelled entries (`_ENTRY_LABEL_RE`) - so this format isn't handled or
mishandled by the parser today; it simply isn't looked for. Any future DCP
extraction needs to handle both the plain-integer and `N/mm` forms from the
start, the same way the existing SPT parsing already does.

PP (Pocket Penetrometer) readings remain unconfirmed either way: the
original "PP" substring search also returned a false zero (same flawed
method), but unlike DCP, a quick re-check with word-position extraction
didn't turn up an obvious numeric pattern for PP the way it did for DCP -
it may sit in a different sub-column not yet identified, or use a
non-numeric marker. Treat PP presence as genuinely unverified, not "zero",
until someone deliberately locates its column.

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
FIELD TESTS/SAMPLES (sample prefix `B:` with a depth range - Bulk Sample -
on 19/21 surveyed pages) · RL (AHD, m) · DEPTH (m) · GRAPHIC LOG ·
CLASSIFICATION SYMBOL · MATERIAL DESCRIPTION · MOISTURE
CONDITION/CONSISTENCY-RELATIVE DENSITY · ADDITIONAL OBSERVATIONS (Geological
Origin). Same column set as Pavement Dip; PID readings appear on 9/21
(43%). No `SPT:`/`D:`/`C:` prefix matched on any surveyed page.

**Correction - DCP is common here, not absent** (see §2.3 for the same fix
and why the original "DCP" substring search was always going to find
nothing - it prints as bare numbers, not the word "DCP"). Re-checked by
word position: **13/21 (62%) of surveyed Test Pit pages carry DCP
readings** - the highest presence of any log type surveyed, up to 18
readings on one page - including partial-penetration entries like `25/70`
and `5/10` (see §2.3 for what this format means). This is a meaningfully
higher rate than Pavement Dip's 26%, consistent with DCP being a more
central field test for Test Pits specifically.

Note (see §2.3): an earlier pass also reported "BS" at 100% and "DS" at
11/21 - both false positives from unbounded substring search (`"BS"` inside
`"OBSERVATIONS"`, `"DS"` inside `"SANDSTONE"`). Re-verified: `B:` is the
only sample-type prefix confirmed present by colon-anchored search. PP
(Pocket Penetrometer) remains genuinely unverified - no "PP" text or "kPa"
value was found by either method - it may use a column/format not yet
identified.

**Known parser limitation:** the DEPTH column sits noticeably further right
on Test Pit pages (tick-value words at x≈193) than on Borehole/Pavement Dip
pages (x≈145-154), outside `borehole_log.py`'s hardcoded column range -
`depth_axis_calibrated: false` on all 21/21 surveyed pages. Header and
field-test extraction are unaffected; only position-based depth estimates
for strata text are unavailable.

---

## 3. Terminology and classification reference

Source: AECOM "Soil and Rock Logging Explanatory Notes and Abbreviations",
Revision Date **28/10/2025** (`reference/borehole-logs/AECOM-soil-rock-
description-sheets.pdf`). All tables below are transcribed as printed;
nothing here is inferred from the log examples.

**Changelog from the 30/6/2017 revision** (what this document was built
against until this revision was supplied - see Part 1's revision-history
note): this is not a cosmetic date bump. Concretely:

- §3.4 Moisture Condition's table is restructured - cohesive soils now get
  distinct per-sub-symbol descriptions (previously shared, generic text).
- §3.11's Modified Casagrande Chart now explicitly draws and labels a 'U'
  line with an accompanying interpretive note (new).
- §3.13 Rock Material Strength (renamed from "Rock Strength") drops its
  three explanatory notes (in-situ moisture caveat, anisotropy caveat, the
  "UCS ≈ 10-20× Is₍₅₀₎" ratio) in favour of a pointer to AS1726-2017 §6.2.4.1;
  the numeric bands themselves are unchanged.
- §3.15's Defect Planarity symbol for "planar" changed from **PL to PR**;
  Defect Roughness's "rough" changed from **ro to RF** (all roughness/
  planarity symbols also went uppercase). The Defect Type table gained
  **DL**, **DB**, and **HB** alongside MB - four separate codes (Mechanical
  Break / Drill Lift / Drilling Break / Handling Break), not a single
  shared row - and reassigned the seam symbols: **SS now means Sheared
  Seam** (previously a generic "Soil Seam, origin undetermined" fallback),
  with **CS** (Crushed Seam) and **IS** (Infilled Seam) replacing the old
  CR/NF. A new "vein" suffix convention and a generalised-defect-count-and-
  spacing suffix convention were both added. (**Correction**: this table
  originally merged MB/DL/DB into one row reading "Mechanical Break / Drill
  Lift / Handling Break" and omitted HB entirely - the static PDF's layout
  was misread. Confirmed directly against OpenGround, the software that
  actually generates these logs and the authoritative source where it and
  the PDF disagree: MB/DL/DB/HB are four distinct codes, each with its own
  meaning - see §3.15.)
- §3.15's Infill/Coating table replaced generic "co" (coated) with **CT**
  ("Coating, ≤1mm thick") and refined "vn"→**VN** to "Veneer, too thin to
  measure"; added a footnote that infill/coating of soil should use soil
  group symbols (e.g. "CH"), not a separate descriptive word.
- §3.16's Field Sampling table renamed **DS→D**, **BS→B**, **E→ES**, and
  **HV→FV/HV**; added **C / CONCC** (Core Sample / Concrete Core Sample -
  this resolves the `C:` prefix seen in Pavement Dip logs in Part 2, which
  had no matching entry in the 2017 table). N*/RW/HW no longer appear.
  Notably, the real example logs in `reference/logs/` already print `D`,
  `ES`, and `B` - **not** the 2017 sheet's `DS`/`E`/`BS` - so the new
  revision's names match observed practice better than the one this
  document was first built against.
- §3.16's Drilling Method table renamed **ADV→AD** and **B/T→V/T**
  ("Blank Bit" retired in favour of "V Bit"); dropped **RC**; added **E**
  (Excavator) and **VE** (Hydro-vacuum Excavation) - filling a real gap,
  since Test Pit logs' "Plant: 5t Excavator" field had no corresponding
  drilling-method symbol in the 2017 table.
- The 2017 sheet's paragraph explaining that pre-July-2017 AECOM logs
  followed AS1726-1993 (a different fine/coarse classification boundary) is
  **not present** in the 28/10/2025 revision - see the vintage note below.
- "Symbol" columns are relabelled "Abbreviation" throughout - cosmetic, but
  applied to every symbol table.
- Confirmed **unchanged**: Plasticity↔LL (§3.2), Colour abbreviations
  (§3.3), Geological Origin (§3.5, heading gained "- Soils"), Grain size/
  shape (§3.8), Relative Density and Consistency numeric bands (§3.9,
  §3.10), the full soil classification chart's group symbols/criteria
  (§3.11), rock type/grain size/defect-spacing/igneous/duricrust tables
  (§3.12), Degree of Weathering/Alteration (§3.14), Vesicularity,
  Cementation/Duricrust grade, Carbonate rules, Water symbols, and Drilling
  Support (all in §3.15/§3.16's area).

**A note on vintage:** the 2017 sheet stated that AECOM logs prepared
*before* July 2017 followed AS1726-1993, which classifies fine- vs
coarse-grained soils differently (on percentage passing 75 micron, not
fines behaviour) and gives different results for materials AS1726-2017
would call e.g. "sandy CLAY" but 1993 called "silty SAND". **The current
(28/10/2025) revision no longer states this** - the paragraph was removed,
not just superseded. The underlying historical fact presumably still holds
for any genuinely pre-2017 log, but the current standard gives no explicit
guidance on it any more. Every example log currently in `reference/logs/`
is dated 2025-2026, so this doesn't currently bite - but if an older or
third-party log is ever added as an example, don't assume either revision's
classification rules apply without first confirming which AS1726 vintage it
was actually logged under.

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
roughness; infill/coating; other descriptors (e.g. colour). Example:
`P, 30/145°, PR, RF, CT CH, 1 mm, gy` = a parting, 30° dip, 145° dip
direction, planar, rough surfaces, a ≤1mm coating of high-plasticity clay,
grey. (The 2017 revision's equivalent example was
`P,30/145°,PL,ro,1mm,CH,gy` - same content, but using the retired
planarity/roughness/infill symbols PL/ro/co; see §3.15 for the current
symbol set.) A healed defect is suffixed "healed"; an intrusive feature or
mineral growth thicker than a cemented joint (>1mm) is suffixed "vein".

Defect thickness distinctions: <10mm = *parting* or *joint*; ≥10mm and
<100mm perpendicular to the defect = *seam* or *zone*; ≥100mm, or a defect
intersecting the full core width for more than 100mm = logged as a new
material strata, not a defect. Generalised defect sets (grouped rather than
logged individually) note their count and spacing at the end of the
description, e.g. "…, x2, 30 mm spacing".

**Field tests and in-situ tests:** recorded in the relevant log column
using the abbreviations in §3.16. As of the 28/10/2025 revision, field
descriptions of consistency/density and rock strength are **updated based
on laboratory test results** before being presented on the log - a change
from the 30/6/2017 revision, which stated the opposite (field results were
transferred "and not modified to coincide with laboratory results",
explicitly meant as an independent estimate). This matters for Phase 2: a
logged consistency/density term that doesn't match the raw field-test
correlation (§3.9, §3.10) is no longer necessarily an independent
cross-check succeeding or failing on its own terms - it may already reflect
a lab-informed revision the field reading alone wouldn't predict. Treat a
mismatch as a prompt for review, not a defect (see Part 4).

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

Restructured in the 28/10/2025 revision: cohesive soils now get a distinct
description per w-subcategory; granular soils get one generic description
per moisture state (previously the reverse - both shared similar generic
text, and the "cool, darkened, tends to cohere" language now attributed to
Granular was previously Cohesive's).

| Term | Cohesive sub-state | Cohesive description | Granular symbol | Granular description |
|---|---|---|---|---|
| Dry | (n/a) | — | D | Non-cohesive and free running |
| Moist | w<PL | Hard and friable or powdery (dry) | M | Soil feels cool, darkened in colour, tends to cohere |
| Moist | w≈PL | Soils can be moulded at a moisture content approximately equal to the plastic limit | M | (as above) |
| Moist | w>PL | Soils usually weakened and free water forms on hands when handling | M | (as above) |
| Wet | w≈LL | Wet, near liquid limit | W | Soil feels cool, darkened in colour, tends to cohere, free water |
| Wet | w>LL | Wet, wet of liquid limit | W | (as above) |

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
(matches `AtterbergChart.jsx`'s existing implementation). The chart also
draws and labels a **'U' line** (as of the 28/10/2025 revision, with an
explicit note that wasn't present in 2017): *"The 'U' line is an
approximate upper bound for most natural soils. If data plots above the U
line, it may represent unusual/problem soil behaviour, or unreliable data
and should be considered carefully."* This matches
`AtterbergChart.jsx`'s existing shaded zone above the U-line - it's now
citable as an explicit rule from the standard itself, not just inferred
chart geometry. Secondary/minor descriptors for fine-grained soils mirror
the coarse-grained convention ("sandy"/"gravelly" >30%, "with sand/gravel"
15-30%, "trace sand/gravel" ≤15%); secondary fine-grained soil not
otherwise described is "clayey SILT".

**Boundary classification:** soils with characteristics of two groups use a
combined symbol, e.g. `GP-GC` (gravel, >5% and ≤12% clay fines) or `CI-CH`
(medium-to-high borderline plasticity) - this is the same dual-symbol
format the example logs actually use (`CI-CH`, `CL-ML`, `SC-`, etc.).

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

### 3.13 Rock Material Strength

(Renamed from "Rock Strength" in the 28/10/2025 revision; "Symbol" row
relabelled "Abbreviation". Numeric bands and field-guide text below are
unchanged from 2017.)

| Term | Abbreviation | UCS (MPa) | Is₍₅₀₎ (MPa) | Field guide |
|---|---|---|---|---|
| Soil | – | ≤0.6 | – | logged as soil, using consistency |
| Very Low | VL | >0.6 ≤2 | >0.03 ≤0.1 | Crumbles under firm pick blow; peeled with knife |
| Low | L | >2 ≤6 | >0.1 ≤0.3 | Scored with knife; 1-3mm indent with pick |
| Medium | M | >6 ≤20 | >0.3 ≤1 | Readily scored with knife; core breaks by hand with difficulty |
| High | H | >20 ≤60 | >1 ≤3 | Core doesn't break by hand; breaks with one firm pick blow |
| Very High | VH | >60 ≤200 | >3 ≤10 | Hand specimen breaks with pick after >1 blow |
| Extremely High | EH | >200 | >10 | Requires many pick blows |

The 2017 revision's three explanatory notes here (use UCS on near-in-situ-
moisture material; anisotropy caveat; "UCS is typically 10-20× Is₍₅₀₎ but
the multiplier varies widely by rock type - not a fixed conversion factor")
are **not present** in the 28/10/2025 revision - it instead just says
"Refer to Section 6.2.4.1 Rock Material Strength of AS1726-2017 for
additional details." The underlying caution (don't rule-check a fixed
UCS:Is₍₅₀₎ ratio) is still sound engineering practice and Part 4 keeps
citing it, but it's no longer stated on the sheet itself as of this
revision - if AS1726-2017 §6.2.4.1 itself is ever added as a reference
source, defer to its exact wording over this document's restatement.

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

**Changed in the 28/10/2025 revision - do not use the old symbols below.**
Most importantly, **SS changed meaning**: in 2017 it was a generic "Soil
Seam, origin can't be determined" fallback; as of 28/10/2025 it means
Sheared Seam specifically, and the generic fallback concept is gone
entirely.

**Correction (confirmed against OpenGround, the software that actually
generates these logs - authoritative over the static AECOM PDF where the
two disagree):** MB, DL, DB, and HB are **four separate codes**, not one
merged row. The AECOM PDF's layout was originally misread as a single row
"MB / DL / DB = Mechanical Break / Drill Lift / Handling Break", which both
conflated three symbols into one definition and omitted HB (Handling
Break) entirely. Corrected below.

| Abbreviation | Term | Definition |
|---|---|---|
| P | Parting | Surface/crack parallel to bedding/cleavage, little/no tensile strength |
| J | Joint | Surface/crack, no shear displacement, not parallel to bedding |
| S | Sheared Surface | Smooth/polished/slickensided, shows shear displacement |
| SZ | Sheared Zone | Roughly parallel boundaries cut by close joints/shears, lenticular blocks |
| MB | Mechanical Break | A break in rock mass not caused by natural effects |
| DL | Drill Lift | A break in rock mass not caused by natural effects |
| DB | Drilling Break | A break in rock mass not caused by natural effects |
| HB | Handling Break | A break in rock mass not caused by natural effects |
| SS | Sheared Seam | Roughly parallel boundaries cut by close joints/cleavage |
| CS | Crushed Seam | Roughly parallel boundaries, disorientated/angular host-rock fragments |
| IS | Infilled Seam | Distinct parallel boundaries, infill from soil migration into joints |
| EW | Extremely Weathered Seam | Soil substance weathered from host rock; often has gradational boundaries |

(2017→2025 renames: SH→SS, CR→CS, NF→IS. The old catch-all "SS = Soil Seam,
origin undetermined" has no equivalent in the current revision.)

**Namespace collision to watch for in Phase 2:** `HB` also appears in
§3.16's Field Sampling table meaning "SPT Hammer Bouncing" (and prints in
the wild that way, e.g. an SPT reading of `10/50 mm HB N=R`). Same two
letters, two unrelated meanings, disambiguated only by which column/context
the token appears in - a rule-checker matching bare `HB` tokens must key
off the surrounding column (rock-defect-description text vs. an SPT field-
test entry), not the symbol alone.

Sheared surfaces/zones/seams and crushed seams are "generally faults in
geological terms". Healed defects are suffixed "healed"; a mineral growth
thicker than a cemented joint (>1mm), or an intrusive feature, is suffixed
"vein" (both new/clarified conventions as of this revision).

**Planarity:** PR planar / CU curved / UN undulating / ST stepped / IR
irregular. (2017's symbol for planar was **PL**, not PR - retired.)

**Roughness:** VR very rough / RF rough / SM smooth / PO polished / SL
slickensided. (2017 used lowercase vr/ro/sm/po/sl, with "rough" as **ro**,
not RF - retired.)

**Infill/coating:** CN clean / SN stained / **VN** veneer (too thin to
measure, may be patchy) / **CT** coating (≤1mm thick) / OP open/voided / Ca
calcium carbonate / Fe iron oxide / Ch chlorite / Qz quartz. Infill/veneers/
coatings *of soil* should use the soil classification group symbol instead
of a descriptive word, e.g. "SW" or "CH" (new guidance as of this revision).
(2017's table used lowercase symbols and a generic "co = coated" in place of
CT; "vn = veneered" was generic where VN is now the specific "too thin to
measure" case.)

**Vesicularity:** D dense (negligible porosity) / NV non-vesicular (<10%) /
SV slightly vesicular (10-20%) / HV highly vesicular (>20%).

**Carbonate content:** <~50% (weak/sporadic effervescence in 10% HCl) =
prefixed "Calcareous"; >50% = prefixed "Carbonate"; ≥90% carbonate
sedimentary rocks use the rock-type name directly (§3.12); 50-90% prefixed
"IMPURE".

### 3.16 Field sampling and testing abbreviations

**Rock core indices:** Total Core Recovery (TCR) and Rock Quality
Designation (RQD) are calculated over the length of a core run as defined
in AS1726-2017. Solid Core Recovery (SCR) is calculated similarly to RQD
but includes full-width pieces less than 100mm long. (This explanatory
paragraph is new as of the 28/10/2025 revision - the 2017 sheet listed
TCR/SCR/RQD as bare abbreviations with no explanation.)

**Changed in the 28/10/2025 revision:** DS→**D** (Disturbed Sample), BS→**B**
(Bulk Sample), E→**ES** (Environmental Sample), HV→**FV/HV** (now "Field
Hand Vane Shear"). New: **C / CONCC** (Core Sample / Concrete Core Sample -
this is the `C:` prefix seen on Pavement Dip logs in Part 2, unexplained
until this revision). Dropped: N* (SPT with sample collected), RW/HW (SPT
rod/hammer weight only, N<1). **The example logs in `reference/logs/`
already print D/ES/B, not the 2017 sheet's DS/E/BS** - i.e. real practice
matches this revision, not the one this document was first built from.

| Abbreviation | Meaning | | Abbreviation | Meaning |
|---|---|---|---|---|
| V | Uncorrected Borehole Vane Shear (kPa), Peak/Residual | | UP | Undisturbed Piston Sample |
| FV/HV | Uncorrected Field Hand Vane Shear (kPa), Peak/Residual | | C / CONCC | Core Sample / Concrete Core Sample |
| PP | Pocket Penetrometer (kPa) | | D | Disturbed Sample |
| SPT | Standard Penetration Test | | B | Bulk Sample |
| N | Uncorrected SPT blow count / 300mm | | ES | Environmental Sample |
| HB | SPT Hammer Bouncing | | RQD | Rock Quality Designation (%) |
| FPM | Field Permeability | | SCR | Solid Core Recovery (%) |
| Lu | Lugeon/Packer Test (L/m/min) | | TCR | Total Core Recovery (%) |
| Is₍₅₀₎(A/D/I) | Axial/Diametral/Irregular Point Load Strength Index (MPa) | | DCP | Dynamic Cone Penetration (blows/100mm) |
| U(X) | Undisturbed Sample, X mm diameter | | PSP | Perth Sand Penetrometer (blows/150mm) |
| | | | PID | Photoionization Detector |

**Water:** ▼ static water level · ▽ water level during drilling · ▷ inflow ·
◁ outflow · ◄ complete water loss. (Unchanged.)

**Drilling method** (changed in the 28/10/2025 revision: ADV→**AD**, the
separate B "Blank Bit" and T "Tungsten Carbide Bit" symbols merged into
**V/T** "V Bit/Tungsten Carbide Bit", **RC** "Reverse Circulation" dropped,
**E** "Excavator" and **VE** "Hydro-vacuum Excavation" added - filling a
real gap, since Test Pit logs' "Plant: 5t Excavator" header field had no
matching drilling-method symbol in the 2017 table):

AD auger drilling* · AS auger screwing · WB wash boring · V/T V bit/
tungsten carbide bit* · RR rock roller/tricone · DHH down-hole hammer · PD
percussion · CT cable tool · HA hand auger · DT diatube (114mm) · NMLC
triple-tube core (50mm) · NQ3/HQ3/PQ3 wireline triple-tube (45/61/83mm) ·
NQ/HQ/PQ wireline double-tube (48/64/85mm) · CA casing advancer · VC vibro
coring · SC sonic coring · E excavator · VE hydro-vacuum excavation · GP
Geoprobe continuous sampling. (*bit symbol suffixes the method, e.g. AD/V =
auger drilling with V-bit - previously written "ADV".)

**Drilling support:** U unsupported · C casing · M mud · W water.
(Unchanged.)

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
  way, flaggable. One symbol is context-dependent, not a simple lookup: `HB`
  means Handling Break in a defect-type context (§3.15) and SPT Hammer
  Bouncing in a field-test context (§3.16) - the check must key off which
  column/field the token was found in, not the bare symbol.
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
  infill/coating;other descriptors, not a check on whether the description
  is geologically apt. Check against the current (28/10/2025) symbol set -
  PR/RF/CT/SS/CS/IS, not the retired PL/ro/co/SH/CR/NF (§3.15).
- **Boundary-symbol format** (§3.11): dual symbols follow the `XX-YY`
  pattern seen in both the standard and the examples.
- **Rock strength band consistency**: given a UCS or Is₍₅₀₎ value, the
  strength term (§3.13) it implies is computable and comparable to the
  logged term - with the caveat that the UCS:Is₍₅₀₎ ratio itself varies too
  widely by rock type to rule-check directly (stated explicitly in the
  2017 sheet; the 28/10/2025 sheet drops the explanation but the caution
  still holds - see §3.13).

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
  and cementation. A mismatch is a prompt to look closer, not a defect - and
  as of the 28/10/2025 revision, field descriptions are stated to be
  *updated* based on lab results (§3.1), where the 2017 revision said the
  opposite (explicitly independent). A persisting mismatch may now be more
  worth flagging than it used to be, since policy says the two should be
  reconciled - but this is a stated policy, not confirmed practice on any
  given log, so it stays a judgment call rather than a hard rule.
  **Reliability caution:** §3.9 (cohesionless/sand, relative density) and
  §3.10 (cohesive/silt-clay, consistency) are two separate correlation
  tables, and their bands share exact SPT-N values at adjacent boundaries -
  e.g. N=4 is simultaneously the Very Loose/Loose line in §3.9 and the
  Soft/Firm line in §3.10. Citing "N is near the X/Y boundary" is precise,
  table-lookup work, not a paraphrase - an LLM reviewer can get the specific
  boundary or even the applicable table wrong while its overall qualitative
  flag ("this SPT-N looks low for the stated term") stays reasonable. Any
  cited boundary/band in a judgment-layer finding should be checked against
  the actual §3.9/§3.10 table before being taken as correct, not accepted
  on the finding's own say-so.
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
  boundary differently. The current (28/10/2025) description sheet no
  longer even mentions this distinction, so there's no standing guidance to
  fall back on if one turns up - it would need to be flagged for a human to
  confirm which AS1726 vintage applies before any rule-checking runs.
