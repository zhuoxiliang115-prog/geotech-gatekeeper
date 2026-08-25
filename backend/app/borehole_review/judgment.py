"""LLM-assisted judgment layer for borehole log review (Phase 2a).

Covers exactly the six categories in reference/borehole-log-standard.md's
Part 4.2 "Judgment-based" breakdown - no more, no less. The rule engine
(rules.py) covers everything deterministic (Part 4.1); Part 4.3
(not-checkable-at-all) is explicitly off-limits here too, enforced as a
system prompt constraint rather than left as an assumption.

The prompt is grounded in the standard doc's actual Part 3 text (read
from reference/borehole-log-standard.md at call time, not a paraphrase),
so the model checks against the terminology tables that took real
verification effort to build, not its own general geotechnical knowledge.

Each call to review_page_judgment() is one real Claude API request, at
real per-review cost - the user's explicit choice (see the phase brief),
not something to invoke speculatively or in a loop without the caller
knowing. Output is structured JSON only (via output_config.format), not
free-form prose, so it can be rendered distinctly from rules.py's
higher-confidence findings.

Model: claude-sonnet-5, not the skill-default Opus 5 - switched after a
cost/quality comparison (see the session's manual read-through notes) at
the user's explicit request. Revert MODEL below to "claude-opus-5" if a
future read-through finds Sonnet's judgment quality doesn't hold up.

Every request logs its exact token usage (input/output/cache
read/write, from the real API response's `usage` field - not an
estimate) via the standard `logging` module, and returns the same figures
in the result dict under "usage", so real per-review cost is visible
without guessing from a chars/4 heuristic.
"""

import json
import logging
import re
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

CATEGORY = "judgment_based"
MODEL = "claude-sonnet-5"

STANDARD_DOC_PATH = Path(__file__).resolve().parents[3] / "reference" / "borehole-log-standard.md"

JUDGMENT_CATEGORIES = [
    "field_id_vs_uscs_symbol",
    "secondary_minor_component_wording",
    "spt_consistency_correlation",
    "geological_origin_plausibility",
    "cross_sheet_continuity",
    "colour_term_plausibility",
]

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "judgment_category": {"type": "string", "enum": JUDGMENT_CATEGORIES},
                    "standard_section": {"type": "string"},
                    "finding": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                    "uncertainty_note": {"type": "string"},
                    "stratum_reference": {"type": ["string", "null"]},
                },
                "required": [
                    "judgment_category",
                    "standard_section",
                    "finding",
                    "confidence",
                    "uncertainty_note",
                    "stratum_reference",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}

SYSTEM_PROMPT_TEMPLATE = """You are reviewing a parsed geotechnical borehole/pavement-dip/test-pit/cored-borehole log against AECOM's soil and rock logging standard (AS1726-2017, revision 28/10/2025). You are given the standard's terminology and classification reference verbatim below, followed by the parsed log data to review.

Your job is to assess ONLY these six judgment-based categories (the standard doc's Part 4.2) - each requires real interpretive judgment, not a lookup table match:

1. Whether the field-ID description (dry strength/dilatancy/toughness language) matches the assigned USCS symbol.
2. Whether secondary/minor-component wording follows the prefix convention correctly (>30% "sandy"/"gravelly", 15-30% "with sand/gravel", <=15% "trace sand/gravel" - see SS3.6, SS3.11 below).
3. Whether SPT-N vs. consistency/density term correlation looks reasonable (SS3.9, SS3.10) - AECOM's own sheet calls this correlation "a rough field guide" affected by grain size, angularity, overburden pressure, moisture content, fines content, and cementation. Do not overstate confidence here; a mismatch is a prompt to look closer, not a defect.
4. Whether a geological-origin term (FILL, ALLUVIUM, RESIDUAL, etc.) is plausible given the described material, depth, and site context.
5. Cross-sheet strata continuity: whether the described material at the bottom of one sheet plausibly matches the top of the next (relevant when the log's header says "continued from previous" / "continued to next").
6. Colour-term plausibility for combination/borderline colours.

You must NOT attempt to assess anything in the standard's Part 4.3 (not checkable at all with what's on hand) - reproduced verbatim below. This includes, but is not limited to:
- Whether a classification is actually geologically correct for the ground it describes (there is no ground truth in this data - only already-approved logs, no paired wrong/right examples).
- Logging thoroughness or completeness (e.g. "should another sample have been taken here").
- Distinguishing an unusual-but-correct entry from a genuine mistake, with no labelled error examples to calibrate against.
- Firm-internal or project-specific conventions not written down in the standard.
- Classifying a log that may have been logged under AS1726-1993 using the current rules without first confirming the vintage.

If you are tempted to comment on any of these, decline - do not produce a finding for it, and do not guess at ground truth.

Only report a finding when something is genuinely worth a second look. Do not manufacture a finding for a description that looks fine - an empty findings list is a valid and expected result for a clean log. Every finding must state its own uncertainty honestly in uncertainty_note - these are judgment calls, not verified facts, and should read that way.

--- STANDARD DOC PART 3 (terminology & classification reference) ---
{part3}

--- STANDARD DOC PART 4.3 (explicitly out of scope - do not attempt) ---
{part4_3}
"""


def _load_standard_doc_section(pattern: str, fallback_label: str) -> str:
    text = STANDARD_DOC_PATH.read_text()
    m = re.search(pattern, text, re.DOTALL)
    if not m:
        return f"[{fallback_label} could not be loaded from {STANDARD_DOC_PATH}]"
    return m.group(0)


def _load_standard_doc_part3() -> str:
    return _load_standard_doc_section(r"## 3\. Terminology.*?(?=\n## 4\.)", "Part 3")


def _load_standard_doc_part4_3() -> str:
    return _load_standard_doc_section(r"### 4\.3.*?(?=\n---|\Z)", "Part 4.3")


def _build_log_summary(parsed_page: dict) -> str:
    header = parsed_page.get("header") or {}
    lines = [
        f"Log type: {header.get('log_type')}",
        f"Hole ID: {header.get('hole_id')}",
        f"Sheet {header.get('sheet')} of {header.get('sheet_total')} "
        f"(continued from previous: {header.get('continued_from_previous')}, "
        f"continued to next: {header.get('continued_to_next')})",
        "",
        "Strata descriptions (in order down the hole; depth is an estimate "
        "interpolated from the depth axis, not a printed value):",
    ]
    for s in parsed_page.get("strata") or []:
        lines.append(f"  - depth~{s.get('depth_from_m')}m: {s['text']}")

    lines.append("")
    lines.append("Field test entries:")
    for e in parsed_page.get("field_test_entries") or []:
        lines.append(f"  - {e}")

    lines.append("")
    lines.append("Notes / additional observations:")
    for n in parsed_page.get("notes") or []:
        lines.append(f"  - {n}")

    return "\n".join(lines)


def _usage_dict(usage) -> dict:
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
    }


def review_page_judgment(parsed_page: dict, client: "anthropic.Anthropic" = None) -> dict:
    """Runs the LLM-assisted judgment layer against one parsed log page.

    Returns {"findings": [...], "error": None, "usage": {...}} on success,
    each finding stamped category="judgment_based" plus which of the six
    §4.2 categories and which standard section it addresses. "usage" is
    the exact token accounting from the real API response (input/output/
    cache read/cache write), logged at INFO level too - not an estimate.
    On any API failure, returns {"findings": [], "error": "<message>",
    "usage": None} rather than raising - a judgment-layer failure should
    degrade the review, not crash it, and the caller can report the
    failure like any other skipped check rather than a 500.
    """
    if parsed_page.get("page_type") != "log":
        return {"findings": [], "error": None, "usage": None}

    try:
        client = client or anthropic.Anthropic()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            part3=_load_standard_doc_part3(),
            part4_3=_load_standard_doc_part4_3(),
        )
        log_summary = _build_log_summary(parsed_page)

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": f"Parsed log data to review:\n\n{log_summary}"}],
            output_config={"format": {"type": "json_schema", "schema": _RESPONSE_SCHEMA}},
        )
        usage = _usage_dict(response.usage)
        hole_id = (parsed_page.get("header") or {}).get("hole_id")
        logger.info(
            "borehole_review.judgment model=%s hole_id=%s input_tokens=%d output_tokens=%d "
            "cache_creation_input_tokens=%d cache_read_input_tokens=%d",
            MODEL,
            hole_id,
            usage["input_tokens"],
            usage["output_tokens"],
            usage["cache_creation_input_tokens"],
            usage["cache_read_input_tokens"],
        )

        text = next(b.text for b in response.content if b.type == "text")
        raw = json.loads(text)
    except Exception as exc:  # noqa: BLE001 - any API/parsing failure degrades, doesn't crash
        return {"findings": [], "error": str(exc), "usage": None}

    findings = []
    for f in raw.get("findings", []):
        findings.append({**f, "category": CATEGORY})
    return {"findings": findings, "error": None, "usage": usage}
