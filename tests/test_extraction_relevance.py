"""Tests for Patch 1-3: section retrieval, relevance gate, unknown status.

The LLM calls are stubbed (a fake client routed by the structured-output schema
name), so these run with no network.
"""

import json

from argus.agent.relevance import filter_relevant
from argus.agent.retrieval import retrieve_sections
from argus.pipeline.audit import run_audit


# ---- a fake OpenAI client that routes by response schema name ----
class _Msg:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, relevance_payload, adequacy_payload):
        self._rel = relevance_payload
        self._adq = adequacy_payload

    def create(self, **kwargs):
        name = kwargs["response_format"]["json_schema"]["name"]
        payload = self._rel if name == "relevance" else self._adq
        return _Resp(json.dumps(payload))


class _FakeClient:
    def __init__(self, relevance_payload, adequacy_payload):
        self.chat = type("C", (), {"completions": _Completions(relevance_payload, adequacy_payload)})()


PARALLEL = {
    "id": "parallel_trends",
    "name": "Parallel trends",
    "assumption": "Treated and control would have moved in parallel.",
    "implication": "Pre-period coefficients near zero.",
    "expected_evidence": ["event study"],
}


def test_retrieve_sections_prefers_on_target_section():
    paper = {
        "id": "p", "title": "t",
        "sections": {
            "data": "States are ranked by effective abortion rates in 1997 for violent crime.",
            "empirical strategy": "We plot event-study coefficients; pre-treatment leads are near zero, supporting parallel trends.",
        },
    }
    items = retrieve_sections(paper, PARALLEL)
    assert items, "should retrieve at least one section"
    # the on-target section (event study / pre-trend) must rank first
    assert "event-study" in items[0]["text"] or "pre-treatment leads" in items[0]["text"]


def test_filter_relevant_keeps_high_drops_none():
    candidates = [
        {"source": "section:data", "text": "abortion rate table"},
        {"source": "section:strategy", "text": "event-study pre-trend plot"},
    ]
    rel_payload = {"items": [
        {"index": 0, "relevance": "none", "reason": "abortion table, off-topic"},
        {"index": 1, "relevance": "high", "reason": "event-study pre-trend"},
    ]}
    client = _FakeClient(rel_payload, {})
    out = filter_relevant(PARALLEL, candidates, client=client)
    assert out["retrieval_quality"] == "good"
    assert len(out["items"]) == 1
    assert out["items"][0]["source"] == "section:strategy"


def test_llm_unknown_when_retrieval_fails(monkeypatch, supported_paper):
    # relevance returns no verdicts -> every candidate is 'none' -> failed -> unknown
    fake = _FakeClient({"items": []}, {})
    monkeypatch.setattr("argus.agent.llm_assessor.make_client", lambda client=None: fake)

    result = run_audit(supported_paper("rfail"), max_steps=1, assessor="llm")
    risks = {d["risk"] for d in result.risk_map["by_dimension"].values()}
    quals = {d["retrieval_quality"] for d in result.risk_map["by_dimension"].values()}
    assert risks == {"unknown"}
    assert quals == {"failed"}


def test_llm_good_retrieval_yields_assessed_risk(monkeypatch, supported_paper):
    rel_payload = {"items": [{"index": 0, "relevance": "high", "reason": "on-topic"}]}
    adq_payload = {
        "risk": "low", "evidence_status": "sufficient",
        "rationale": "Event study supports parallel trends.",
        "cited_evidence": ["section:parallel trends"],
    }
    fake = _FakeClient(rel_payload, adq_payload)
    monkeypatch.setattr("argus.agent.llm_assessor.make_client", lambda client=None: fake)

    result = run_audit(supported_paper("rgood"), max_steps=1, assessor="llm")
    pt = result.risk_map["by_dimension"]["parallel_trends"]
    assert pt["risk"] == "low"
    assert pt["retrieval_quality"] in {"good", "weak"}
