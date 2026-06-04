"""Stage 3 — assessment (AGENTIC, bounded).

For each dimension, assess the assumption -> implication -> evidence chain and
emit a per-dimension risk judgement anchored to the extracted evidence. Runs the
same bounded loop, logs a trace.
"""

from __future__ import annotations

from typing import Any

from ..agent.loop import run_bounded_loop
from ..agent.tools import DEFAULT_TOOLS


def assess(
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
