"""Tests for the provider-neutral model registry (no API calls)."""

import pytest

from argus.agent.model_config import (
    build_run_manifest,
    enabled_models,
    load_model_registry,
    resolve,
)


def test_registry_loads_and_merges_defaults():
    reg = load_model_registry()
    assert reg["models"], "no models declared"
    gpt = resolve("gpt4o", reg)
    # per-model fields present, defaults merged in
    assert gpt["provider"] == "openai"
    assert gpt["temperature"] == reg["defaults"]["temperature"]
    assert "cost_ceiling_usd" in gpt


def test_all_models_disabled_by_default():
    """Safety invariant: nothing is enabled, so nothing can run by accident."""
    assert enabled_models() == []


def test_all_declared_providers_are_runnable():
    """openai, openai-compatible (Gemini/Kimi/Ollama), and anthropic all have
    implemented backends now; the runnable flag must reflect that."""
    reg = load_model_registry()
    for mid, cfg in reg["models"].items():
        assert cfg["runnable"] is True, f"{mid} ({cfg['provider']}) should be runnable"


def test_anthropic_compat_translates_openai_surface():
    """The Anthropic facade must accept the exact call shape our two call sites
    use and return an OpenAI-shaped response with the tool input as JSON."""
    import json as _json

    from argus.agent.anthropic_compat import AnthropicCompatClient

    captured = {}

    class _StubMessages:
        def create(self, **kwargs):
            captured.update(kwargs)

            class _Block:
                type = "tool_use"
                input = {"risk": "low", "evidence_status": "sufficient",
                         "rationale": "r", "cited_evidence": []}

            class _Resp:
                content = [_Block()]

            return _Resp()

    class _StubAnthropic:
        messages = _StubMessages()

    client = AnthropicCompatClient(anthropic_client=_StubAnthropic())
    resp = client.chat.completions.create(
        model="claude-sonnet-5",
        temperature=0,
        messages=[{"role": "system", "content": "sys"},
                  {"role": "user", "content": "user"}],
        response_format={"type": "json_schema",
                         "json_schema": {"name": "risk_judgement", "strict": True,
                                         "schema": {"type": "object"}}},
    )
    out = _json.loads(resp.choices[0].message.content)
    assert out["risk"] == "low"
    # system prompt extracted, tool forced with our schema name
    assert captured["system"] == "sys"
    assert captured["tool_choice"] == {"type": "tool", "name": "risk_judgement"}
    assert captured["messages"] == [{"role": "user", "content": "user"}]


def test_manifest_projects_calls_and_flags_ceiling():
    manifest = build_run_manifest(33, calls_per_unit=2, model_ids=["gpt4o"])
    row = manifest["models"][0]
    assert row["projected_calls"] == 66
    assert row["estimated_cost_usd"] >= 0.0
    assert isinstance(row["within_ceiling"], bool)


def test_resolve_unknown_model_raises():
    with pytest.raises(KeyError, match="unknown model id"):
        resolve("does_not_exist")
