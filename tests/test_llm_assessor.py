"""Unit tests for the LLM assessor — no network, the OpenAI client is stubbed."""

import json

import pytest

from argus.agent.llm_assessor import assess_chain_llm
from argus.pipeline.audit import run_audit


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeClient:
    """Records the request and returns a canned structured judgement."""

    def __init__(self, payload):
        self._payload = payload
        self.last_request = None

        class _Completions:
            def __init__(self, outer):
                self._outer = outer

            def create(self, **kwargs):
                self._outer.last_request = kwargs
                return _FakeCompletion(json.dumps(self._outer._payload))

        class _Chat:
            def __init__(self, outer):
                self.completions = _Completions(outer)

        self.chat = _Chat(self)


def _dimension():
    return {
        "id": "parallel_trends",
        "name": "Parallel trends",
        "assumption": "Treated and control would have moved in parallel.",
        "implication": "Pre-period coefficients near zero.",
        "expected_evidence": ["event study", "pre-trend test"],
    }


def test_assess_chain_llm_parses_structured_judgement():
    client = _FakeClient({
        "risk": "high",
        "evidence_status": "flawed",
        "rationale": "Pre-period estimates drift upward.",
        "cited_evidence": ["section:parallel trends"],
    })
    evidence = {"items": [{"source": "section:parallel trends", "text": "estimates drift upward"}]}

    out = assess_chain_llm(_dimension(), evidence, client=client)

    assert out["judgement"]["risk"] == "high"
    assert out["judgement"]["evidence_status"] == "flawed"
    assert out["judgement"]["cited_evidence"] == ["section:parallel trends"]
    # request is well-formed: temperature 0, strict json schema, both turns present
    req = client.last_request
    assert req["temperature"] == 0
    assert req["response_format"]["json_schema"]["strict"] is True
    assert [m["role"] for m in req["messages"]] == ["system", "user"]
    assert "estimates drift upward" in req["messages"][1]["content"]


def test_run_audit_with_llm_assessor_uses_injected_client(monkeypatch, supported_paper):
    # Patch make_client so run_audit(assessor="llm") needs no key / network.
    canned = {
        "risk": "low",
        "evidence_status": "sufficient",
        "rationale": "Event study supports parallel trends.",
        "cited_evidence": ["section:parallel trends"],
    }
    fake = _FakeClient(canned)
    monkeypatch.setattr("argus.agent.llm_assessor.make_client", lambda client=None: fake)

    result = run_audit(supported_paper("llm_demo"), max_steps=1, assessor="llm")
    risks = {d["risk"] for d in result.risk_map["by_dimension"].values()}
    assert risks == {"low"}


def test_unknown_assessor_rejected(supported_paper):
    from argus.pipeline.assessment import assess

    with pytest.raises(ValueError, match="unknown assessor"):
        assess({"dimensions": {}}, {"evidence": {}}, max_steps=1, assessor="bogus")
