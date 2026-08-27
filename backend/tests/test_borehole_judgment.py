"""Structure tests for the LLM-assisted judgment layer
(app/borehole_review/judgment.py).

Judgment-layer output is inherently non-deterministic, so these tests
check structure (valid JSON, expected fields, error handling, prompt
construction) against a mocked Anthropic client rather than asserting
exact wording - per the phase brief's own testing guidance. No real API
credentials are available in this environment (no ANTHROPIC_API_KEY, no
`ant` CLI), so a live quality read-through of real model output against
real example logs could not be done as part of this change - see the
follow-up note in the session summary. These tests only verify the code
around the API call behaves correctly, not the model's judgment quality.
"""

import json
import logging
from types import SimpleNamespace

import pytest

from app.borehole_review import judgment


def _fake_response(findings, usage=None):
    text_block = SimpleNamespace(type="text", text=json.dumps({"findings": findings}))
    usage = usage or SimpleNamespace(
        input_tokens=8500, output_tokens=120, cache_creation_input_tokens=8400, cache_read_input_tokens=0
    )
    return SimpleNamespace(content=[text_block], usage=usage)


class _FakeMessages:
    def __init__(self, response=None, exception=None):
        self._response = response
        self._exception = exception
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        if self._exception:
            raise self._exception
        return self._response


class _FakeClient:
    def __init__(self, response=None, exception=None):
        self.messages = _FakeMessages(response=response, exception=exception)


_SAMPLE_PAGE = {
    "page_type": "log",
    "header": {
        "log_type": "Borehole",
        "hole_id": "WSM_BH01",
        "sheet": 1,
        "sheet_total": 4,
        "continued_from_previous": False,
        "continued_to_next": True,
    },
    "strata": [{"text": "TOPSOIL -Silty SAND: fine grained, dark brown.", "depth_from_m": 0.1}],
    "field_test_entries": [{"type": "SPT", "depth_from_m": 1.5, "depth_to_m": 1.95, "blows": "9,19,13", "n_value": "32"}],
    "notes": [],
}


def test_review_page_judgment_returns_empty_for_non_log_page():
    result = judgment.review_page_judgment({"page_type": "photo_report"}, client=_FakeClient())
    assert result == {"findings": [], "error": None, "usage": None}


def test_review_page_judgment_parses_valid_structured_response():
    findings = [
        {
            "judgment_category": "spt_consistency_correlation",
            "standard_section": "§3.9, §3.10",
            "finding": "SPT N=32 at 1.5-1.95m seems high for the logged 'medium dense' term.",
            "confidence": "low",
            "uncertainty_note": "AECOM's own SPT correlation is a rough field guide only.",
            "stratum_reference": "1.5-1.95m",
        }
    ]
    client = _FakeClient(response=_fake_response(findings))
    result = judgment.review_page_judgment(_SAMPLE_PAGE, client=client)

    assert result["error"] is None
    assert len(result["findings"]) == 1
    f = result["findings"][0]
    assert f["category"] == "judgment_based"
    assert f["judgment_category"] == "spt_consistency_correlation"
    assert f["confidence"] == "low"
    assert "uncertainty_note" in f


def test_review_page_judgment_handles_empty_findings():
    client = _FakeClient(response=_fake_response([]))
    result = judgment.review_page_judgment(_SAMPLE_PAGE, client=client)
    assert result == {
        "findings": [],
        "error": None,
        "usage": {
            "input_tokens": 8500,
            "output_tokens": 120,
            "cache_creation_input_tokens": 8400,
            "cache_read_input_tokens": 0,
        },
    }


def test_review_page_judgment_degrades_on_api_failure():
    client = _FakeClient(exception=RuntimeError("no credentials configured"))
    result = judgment.review_page_judgment(_SAMPLE_PAGE, client=client)
    assert result["findings"] == []
    assert "no credentials configured" in result["error"]
    assert result["usage"] is None


def test_review_page_judgment_returns_exact_usage_from_real_response():
    # not a chars/4 estimate - the exact usage block from the (fake, but
    # shaped like a real) API response.
    usage = SimpleNamespace(
        input_tokens=8917, output_tokens=243, cache_creation_input_tokens=0, cache_read_input_tokens=8400
    )
    client = _FakeClient(response=_fake_response([], usage=usage))
    result = judgment.review_page_judgment(_SAMPLE_PAGE, client=client)
    assert result["usage"] == {
        "input_tokens": 8917,
        "output_tokens": 243,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 8400,
    }


def test_review_page_judgment_logs_usage(caplog):
    client = _FakeClient(response=_fake_response([]))
    with caplog.at_level(logging.INFO, logger="app.borehole_review.judgment"):
        judgment.review_page_judgment(_SAMPLE_PAGE, client=client)
    assert any("borehole_review.judgment" in r.message for r in caplog.records)
    assert any("input_tokens=8500" in r.message for r in caplog.records)


def test_model_is_opus_5():
    # A live read-through found Sonnet missing explicit standard-clause
    # violations (colour hyphenation, XW weathering-grade terminology)
    # that Opus caught on the same pages - a reliability gap, not just a
    # lower hit-count, so Opus was kept despite the higher cost.
    assert judgment.MODEL == "claude-opus-5"


def test_review_page_judgment_uses_json_schema_output_config():
    client = _FakeClient(response=_fake_response([]))
    judgment.review_page_judgment(_SAMPLE_PAGE, client=client)
    kwargs = client.messages.last_kwargs
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert kwargs["model"] == judgment.MODEL


def test_system_prompt_includes_standard_doc_part3_and_part43():
    client = _FakeClient(response=_fake_response([]))
    judgment.review_page_judgment(_SAMPLE_PAGE, client=client)
    system_text = client.messages.last_kwargs["system"][0]["text"]
    # Part 3 content actually present (grounded in the real doc, not a paraphrase)
    assert "Modified Casagrande" in system_text
    assert "A-line" in system_text
    # Part 4.3's negative constraint is present as an explicit instruction
    assert "not checkable at all" in system_text.lower()
    assert "geologically correct for the ground" in system_text


def test_system_prompt_is_cached():
    client = _FakeClient(response=_fake_response([]))
    judgment.review_page_judgment(_SAMPLE_PAGE, client=client)
    system_blocks = client.messages.last_kwargs["system"]
    assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}


def test_response_schema_requires_all_finding_fields():
    schema_props = judgment._RESPONSE_SCHEMA["properties"]["findings"]["items"]
    required = set(schema_props["required"])
    assert required == {
        "judgment_category",
        "standard_section",
        "finding",
        "confidence",
        "uncertainty_note",
        "stratum_reference",
    }
    assert schema_props["additionalProperties"] is False


@pytest.mark.parametrize("category", judgment.JUDGMENT_CATEGORIES)
def test_judgment_categories_match_standard_doc_part_4_2_count(category):
    # exactly six categories, matching §4.2 - not more, not fewer
    assert len(judgment.JUDGMENT_CATEGORIES) == 6
    assert category in judgment.JUDGMENT_CATEGORIES
