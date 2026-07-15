"""LLM-based evidence-adequacy assessor (OpenAI backend).

This replaces the keyword assessment policy with a model that judges whether the
retrieved evidence *adequately* supports a DID identification assumption — not
whether the right keywords are present. Distinguishing evidence presence from
evidence adequacy is the reasoning step the keyword baseline cannot do, and the
gap the phase-1 results quantify.

Provider note: this module uses the OpenAI SDK (the project's available key is an
OpenAI key). The ARGUS pipeline is provider-agnostic — the assessor only has to
return a judgement dict of the documented shape, so an Anthropic/other backend
can be dropped in later without touching the pipeline.

Configuration (environment):
  OPENAI_API_KEY    required
  ARGUS_LLM_MODEL   model id (default: gpt-4o)
  OPENAI_BASE_URL   optional, for proxies / compatible gateways

Reproducibility: temperature=0 and a fixed model id; the full request and raw
response are returned for the caller to log to results/traces/.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

DEFAULT_MODEL = "gpt-4o"

# Project-root .env so the key need not be re-exported every shell. Gitignored.
_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


def _load_env_file(path: Path = _ENV_PATH) -> None:
    """Load KEY=VALUE lines from a .env file into os.environ (no overwrite).

    Dependency-free; ignores blanks, comments, and malformed lines. Existing
    environment variables win, so an explicit `export` still overrides the file.
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val

_SYSTEM_PROMPT = (
    "You audit the causal-IDENTIFICATION credibility of difference-in-differences "
    "(DID) studies in environmental policy evaluation. You do NOT judge whether the "
    "estimated effect is true — the counterfactual is never observed. For ONE "
    "identification dimension, judge whether the evidence the paper reports is "
    "ADEQUATE to support the assumption.\n\n"
    "Crucial distinction: evidence PRESENCE is not evidence ADEQUACY. The mere "
    "mention of a topic (an event study, a balance table, 'placebo') does not make "
    "the assumption supported — assess whether the reported evidence actually "
    "establishes the testable implication, and whether it reveals a flaw.\n\n"
    "Return a risk level and an evidence-status label:\n"
    "  risk: low | medium | high\n"
    "  evidence_status: sufficient | partial | missing | flawed\n"
    "Map roughly: sufficient->low, partial->medium, missing->high, flawed->high. "
    "Be conservative: if the evidence is absent, thin, or describes a flawed design, "
    "do not call it supported. Cite the specific evidence (by source) your judgement "
    "rests on. Keep the rationale to one or two sentences."
)

_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "risk": {"type": "string", "enum": ["low", "medium", "high"]},
        "evidence_status": {
            "type": "string",
            "enum": ["sufficient", "partial", "missing", "flawed"],
        },
        "rationale": {"type": "string"},
        "cited_evidence": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["risk", "evidence_status", "rationale", "cited_evidence"],
}


def make_client(client: Optional[Any] = None) -> Any:
    """Return a chat client for the configured provider.

    Providers (env ``ARGUS_PROVIDER``, default ``openai``):
      - ``openai`` (default): the OpenAI SDK. ``OPENAI_BASE_URL`` retargets it at
        any OpenAI-compatible endpoint (Gemini, Kimi/Moonshot, a local Ollama),
        with ``OPENAI_API_KEY`` carrying that provider's key for the run.
      - ``anthropic``: the Anthropic SDK behind an OpenAI-shaped facade
        (see :mod:`argus.agent.anthropic_compat`); needs ``ANTHROPIC_API_KEY``.
    """
    if client is not None:
        return client
    _load_env_file()  # pick up keys from a project-root .env (no overwrite)

    provider = os.environ.get("ARGUS_PROVIDER", "openai").lower()
    if provider == "anthropic":
        from .anthropic_compat import AnthropicCompatClient

        return AnthropicCompatClient()
    if provider != "openai":
        raise RuntimeError(f"unknown ARGUS_PROVIDER: {provider!r} (openai|anthropic)")

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Either export it, or put it in a .env file "
            "at the project root (see .env.example):\n"
            "  echo 'OPENAI_API_KEY=sk-...' > .env"
        )
    from openai import OpenAI

    kwargs: dict[str, Any] = {}
    if os.environ.get("OPENAI_BASE_URL"):
        kwargs["base_url"] = os.environ["OPENAI_BASE_URL"]
    return OpenAI(**kwargs)


def _build_user_prompt(dimension: dict[str, Any], evidence: Optional[dict[str, Any]]) -> str:
    items = (evidence or {}).get("items") or []
    if items:
        ev_lines = [
            f"- [{it.get('source', 'unknown')}] {str(it.get('text', '')).strip()}"
            for it in items
        ]
        ev_block = "\n".join(ev_lines)
    else:
        ev_block = "(no evidence was retrieved for this dimension)"
    return (
        f"Identification dimension: {dimension.get('name', dimension.get('id'))}\n"
        f"Assumption: {dimension.get('assumption', '')}\n"
        f"Testable implication: {dimension.get('implication', '')}\n"
        f"Evidence a credible paper would report: "
        f"{', '.join(dimension.get('expected_evidence', []) or [])}\n\n"
        f"Evidence retrieved from THIS paper:\n{ev_block}\n\n"
        f"Judge the adequacy of this evidence for the assumption."
    )


def assess_chain_llm(
    dimension: dict[str, Any],
    evidence: Optional[dict[str, Any]],
    *,
    client: Optional[Any] = None,
    model: Optional[str] = None,
) -> dict[str, Any]:
    """Assess one dimension with the LLM. Returns {"judgement", "trace"}.

    The judgement dict matches the keyword assessor's shape (risk / rationale /
    cited_evidence) plus an evidence_status field, so localization and report
    consume it unchanged.
    """
    client = make_client(client)
    model = model or os.environ.get("ARGUS_LLM_MODEL", DEFAULT_MODEL)
    user_prompt = _build_user_prompt(dimension, evidence)

    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "risk_judgement", "strict": True, "schema": _SCHEMA},
        },
    )
    raw = response.choices[0].message.content or "{}"
    parsed = json.loads(raw)

    judgement = {
        "risk": parsed.get("risk", "high"),
        "evidence_status": parsed.get("evidence_status", "missing"),
        "rationale": parsed.get("rationale", ""),
        "cited_evidence": parsed.get("cited_evidence", []),
    }
    trace = {
        "assessor": "llm",
        "model": model,
        "dimension_id": dimension.get("id"),
        "prompt": user_prompt,
        "raw_response": raw,
        "judgement": judgement,
    }
    return {"judgement": judgement, "trace": trace}
