"""Stage 2 — extraction (AGENTIC, bounded).

For each dimension, run a bounded ReAct loop to gather supporting evidence from
the paper using the fixed tool set (evidence_search, figure_parse, policy_lookup).
Every step is logged to results/traces/.
"""

from __future__ import annotations

from typing import Any

from ..agent.loop import run_bounded_loop
from ..agent.tools import DEFAULT_TOOLS


def extract(
    paper: dict[str, Any],
    skeleton: dict[str, Any],
    *,
    max_steps: int,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    trace_paths: list[str] = []
    for dim_id in skeleton["dimensions"]:
        result = run_bounded_loop(
            task=f"extract_evidence:{dim_id}",
            context={"paper": paper, "dimension": skeleton["dimensions"][dim_id]},
            tools=DEFAULT_TOOLS,
            max_steps=max_steps,
        )
        evidence[dim_id] = result["output"]
        trace_paths.append(result["trace_path"])
    return {"evidence": evidence, "trace_paths": trace_paths}
