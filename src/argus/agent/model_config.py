"""Provider-neutral model registry and run planner (``config/models.yaml``).

This is the seam for cross-model robustness runs. It does **not** call any model.
It loads the registry, merges per-model settings over ``defaults``, and can build
a no-API *run manifest* (which models over how many units, projected call count
and estimated cost, checked against each model's ``cost_ceiling_usd``).

Wiring a provider
-----------------
The pipeline only needs a callable that maps a prompt to the judgement dict shape
in :mod:`argus.agent.llm_assessor` (``{risk, evidence_status, rationale,
cited_evidence}``). A provider is therefore any object satisfying
:class:`ProviderAdapter`. Today only the OpenAI path is implemented, via
``argus.agent.llm_assessor.make_client`` and the two ``chat.completions.create``
call sites; a new provider is added by implementing an adapter here and branching
it in ``argus.pipeline.assessment.assess``. Until then, enabling a non-openai
model in the registry is a declaration of intent, not a runnable backend, and
this module says so loudly (:func:`resolve` marks such models ``runnable: False``).

No number reported in the paper depends on this module: every reported result
uses the single default ``gpt-4o`` path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "models.yaml"

# Providers with a real backend implemented in this codebase today:
#   openai            - OpenAI SDK (llm_assessor.make_client)
#   openai-compatible - OpenAI SDK pointed at `base_url` (Gemini, Kimi, Ollama)
#   anthropic         - Anthropic SDK via agent/anthropic_compat.py
_IMPLEMENTED_PROVIDERS = {"openai", "openai-compatible", "anthropic"}
_REQUIRED_MODEL_FIELDS = ("id", "provider", "model", "enabled")


@runtime_checkable
class ProviderAdapter(Protocol):
    """Minimal contract a model backend must satisfy to plug into the assessor.

    An implementation returns the judgement dict the downstream pipeline consumes
    (see :mod:`argus.agent.llm_assessor`). This Protocol documents the seam; the
    only shipped implementation is the OpenAI path in ``llm_assessor``/``relevance``.
    """

    def complete(self, *, system: str, user: str, response_schema: dict[str, Any]) -> dict[str, Any]:
        ...


def load_model_registry(path: Optional[Path] = None) -> dict[str, Any]:
    """Parse ``config/models.yaml`` into ``{"defaults": {...}, "models": {id: cfg}}``.

    Each model config is the merge of ``defaults`` and the per-model entry, plus a
    derived ``runnable`` flag (True only if the provider has an implemented
    backend). Validates required fields and unique ids.
    """
    p = path or CONFIG_PATH
    with open(p, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    if not isinstance(raw, dict):
        raise ValueError("models.yaml must contain a mapping")

    defaults = raw.get("defaults") or {}
    if not isinstance(defaults, dict):
        raise ValueError("models.yaml defaults must be a mapping")

    rows = raw.get("models") or []
    if not isinstance(rows, list):
        raise ValueError("models.yaml models must be a list")

    models: dict[str, Any] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each models entry must be a mapping")
        missing = [f for f in _REQUIRED_MODEL_FIELDS if f not in row]
        if missing:
            raise ValueError(f"model entry missing required fields: {missing}")
        mid = row["id"]
        if mid in models:
            raise ValueError(f"duplicate model id: {mid}")
        merged = {**defaults, **row}
        merged["runnable"] = merged["provider"] in _IMPLEMENTED_PROVIDERS
        models[mid] = merged

    return {"defaults": defaults, "models": models}


def enabled_models(registry: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Model configs with ``enabled: true`` (empty by default, by design)."""
    reg = registry or load_model_registry()
    return [cfg for cfg in reg["models"].values() if cfg.get("enabled")]


def resolve(model_id: str, registry: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Return the merged config for one model id (raises if unknown)."""
    reg = registry or load_model_registry()
    if model_id not in reg["models"]:
        raise KeyError(f"unknown model id: {model_id} (have {sorted(reg['models'])})")
    return reg["models"][model_id]


def build_run_manifest(
    n_units: int,
    *,
    calls_per_unit: int = 2,   # LLM assessor issues ~2 calls/dimension (relevance gate + adequacy)
    model_ids: Optional[list[str]] = None,
    registry: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build a NO-API plan for running ``n_units`` audit units across models.

    Projects call count and a rough cost ESTIMATE per model (from
    ``avg_tokens_per_call`` x ``price_per_1k_usd``) and flags any model whose
    projection exceeds its ``cost_ceiling_usd``. Purely arithmetic; issues no
    calls. The cost figure is an order-of-magnitude estimate for planning only.
    """
    reg = registry or load_model_registry()
    ids = model_ids or [m["id"] for m in enabled_models(reg)]
    plan = []
    for mid in ids:
        cfg = resolve(mid, reg)
        calls = n_units * calls_per_unit
        est_tokens = calls * cfg.get("avg_tokens_per_call", 1500)
        est_cost = est_tokens / 1000.0 * cfg.get("price_per_1k_usd", 0.0)
        ceiling = cfg.get("cost_ceiling_usd")
        plan.append({
            "id": mid,
            "provider": cfg["provider"],
            "model": cfg["model"],
            "enabled": bool(cfg.get("enabled")),
            "runnable": bool(cfg.get("runnable")),
            "projected_calls": calls,
            "estimated_cost_usd": round(est_cost, 2),
            "cost_ceiling_usd": ceiling,
            "within_ceiling": (ceiling is None) or (est_cost <= ceiling),
        })
    return {"n_units": n_units, "calls_per_unit": calls_per_unit, "models": plan}


__all__ = [
    "ProviderAdapter",
    "load_model_registry",
    "enabled_models",
    "resolve",
    "build_run_manifest",
]
