"""Stage 3 — assessment (AGENTIC, bounded).

For each dimension, assess the assumption -> implication -> evidence chain and
emit a per-dimension risk judgement anchored to the extracted evidence.

Two assessors are selectable, run over the SAME retrieved evidence so the
comparison is clean:
  - "keyword": the deterministic baseline (positive/negative signal scoring).
  - "llm":     a model that judges evidence ADEQUACY (OpenAI backend).
Both log a trace to results/traces/.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from ..agent.loop import run_bounded_loop
from ..agent.tools import DEFAULT_TOOLS

TRACE_DIR = Path(__file__).resolve().parents[3] / "results" / "traces"


def assess(
    skeleton: dict[str, Any],
    evidence: dict[str, Any],
    *,
    max_steps: int,
    assessor: str = "keyword",
) -> dict[str, Any]:
    if assessor == "keyword":
        return _assess_keyword(skeleton, evidence, max_steps=max_steps)
    if assessor == "llm":
        return _assess_llm(skeleton, evidence)
    raise ValueError(f"unknown assessor: {assessor!r} (expected 'keyword' or 'llm')")


def _assess_keyword(
    skeleton: dict[str, Any],
    evidence: dict[str, Any],
    *,
    max_steps: int,
) -> dict[str, Any]:
    judgements: dict[str, Any] = {}
    trace_paths: list[str] = []
    for dim_id, dim in skeleton["dimensions"].items():
        result = run_bounded_loop(
            task=f"assess_chain:{dim_id}",
            context={"dimension": dim, "evidence": evidence["evidence"].get(dim_id)},
            tools=DEFAULT_TOOLS,
            max_steps=max_steps,
        )
        # Expected output shape: {risk: low|medium|high, rationale, cited_evidence}
        judgements[dim_id] = result["output"]
        trace_paths.append(result["trace_path"])
    return {"judgements": judgements, "trace_paths": trace_paths}


def _assess_llm(skeleton: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    from ..agent.llm_assessor import assess_chain_llm, make_client

    client = make_client()  # raises a clear error if OPENAI_API_KEY is unset
    TRACE_DIR.mkdir(parents=True, exist_ok=True)

    judgements: dict[str, Any] = {}
    trace_paths: list[str] = []
    for dim_id, dim in skeleton["dimensions"].items():
        result = assess_chain_llm(dim, evidence["evidence"].get(dim_id), client=client)
        judgements[dim_id] = result["judgement"]
        path = TRACE_DIR / f"assess_llm_{dim_id}-{uuid.uuid4().hex[:8]}.json"
        path.write_text(
            json.dumps({"t": time.time(), **result["trace"]}, indent=2),
            encoding="utf-8",
        )
        trace_paths.append(str(path))
    return {"judgements": judgements, "trace_paths": trace_paths}
