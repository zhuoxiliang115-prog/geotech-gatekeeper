# Sydney Classification System (Pells et al. 1998)

Source: Pells, P.J.N. et al. (1998), as documented in Bertuzzi, R. (2019)
"Estimating Rock Mass Properties," originally Pells et al. (1978), updated
per Bertuzzi and Pells (2002). Developed for Hawkesbury Sandstone /
Ashfield Shale foundation design in the Sydney region. Classification
requires all three factors (UCS, defect spacing, allowable seams %) to be
satisfied simultaneously — the binding (lowest) class governs.

This document is citation/documentation only —
`backend/app/rock_parameters/classification.py` already correctly
implements these thresholds (Table 9.1 below) in code; this file exists so
the source is traceable in-repo, the same role
`reference/borehole-log-standard.md` plays for the AECOM logging standard.

## Sandstone

| Class | UCS (MPa) | Defect spacing | Allowable seams (%) |
|---|---|---|---|
| I | > 24 | > 600mm, widely spaced | < 1.5 |
| II | > 12 | > 600mm, widely spaced | < 3 |
| III | > 7 | > 200mm, moderately spaced | < 5 |
| IV | > 2 | > 60mm, closely spaced | < 10 |
| V | > 1 | NA | NA |

## Shale

| Class | UCS (MPa) | Defect spacing | Allowable seams (%) |
|---|---|---|---|
| I | > 16 | > 600mm, widely spaced | < 2 |
| II | > 7 | > 200mm, moderately spaced | < 4 |
| III | > 2 | > 60mm, closely spaced | < 8 |
| IV | > 1 | > 20mm, very closely spaced | < 25 |
| V | > 1 | NA | NA |

"Seams" = clay, fragmented, or highly weathered zones within the interval,
as a percentage of interval length.
