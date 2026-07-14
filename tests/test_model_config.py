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


def test_only_openai_is_runnable():
    reg = load_model_registry()
    assert reg["models"]["gpt4o"]["runnable"] is True
    # non-openai providers are declarations of intent until an adapter is added
    assert reg["models"]["claude_sonnet"]["runnable"] is False


def test_manifest_projects_calls_and_flags_ceiling():
    manifest = build_run_manifest(33, calls_per_unit=2, model_ids=["gpt4o"])
    row = manifest["models"][0]
    assert row["projected_calls"] == 66
    assert row["estimated_cost_usd"] >= 0.0
    assert isinstance(row["within_ceiling"], bool)


def test_resolve_unknown_model_raises():
    with pytest.raises(KeyError, match="unknown model id"):
        resolve("does_not_exist")
