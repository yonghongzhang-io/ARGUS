"""Stage 3 — assessment (AGENTIC, bounded).

For each dimension, assess the assumption -> implication -> evidence chain and
emit a per-dimension risk judgement anchored to the extracted evidence.

Two assessors are selectable:
  - "keyword": the deterministic baseline (positive/negative signal scoring),
    judged over the stage-2 extraction evidence.
  - "llm":     a model that judges evidence ADEQUACY (OpenAI backend); this
    path does its OWN section-level retrieval + relevance gating and does not
    consume the stage-2 bundle, so keyword-vs-llm is an end-to-end pipeline
    comparison, not a same-evidence judgement swap.
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
    paper: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if assessor == "keyword":
        return _assess_keyword(skeleton, evidence, max_steps=max_steps)
    if assessor == "llm":
        if paper is None:
            raise ValueError("the 'llm' assessor needs the paper for section-level retrieval")
        return _assess_llm(skeleton, paper)
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


def _assess_llm(skeleton: dict[str, Any], paper: dict[str, Any]) -> dict[str, Any]:
    """Two-stage LLM path: section retrieval -> relevance gate -> adequacy.

    If the relevance gate finds no relevant evidence, the dimension is scored
    `risk: unknown` (retrieval failed) rather than `high` — separating "the
    system could not find evidence" from "the paper has no evidence".
    """
    from ..agent.llm_assessor import assess_chain_llm, make_client
    from ..agent.relevance import filter_relevant
    from ..agent.retrieval import retrieve_sections

    client = make_client()  # raises a clear error if OPENAI_API_KEY is unset
    TRACE_DIR.mkdir(parents=True, exist_ok=True)

    judgements: dict[str, Any] = {}
    trace_paths: list[str] = []
    for dim_id, dim in skeleton["dimensions"].items():
        candidates = retrieve_sections(paper, dim)
        gate = filter_relevant(dim, candidates, client=client)

        if gate["retrieval_quality"] == "failed":
            judgement = {
                "risk": "unknown",
                "evidence_status": "missing",
                "retrieval_quality": "failed",
                "rationale": (
                    "Retrieval did not surface evidence relevant to this dimension; "
                    "the system cannot assess it reliably (not a claim that the paper "
                    "lacks the evidence)."
                ),
                "cited_evidence": [],
            }
            trace_extra: dict[str, Any] = {"retrieval_quality": "failed", "candidates": candidates}
        else:
            result = assess_chain_llm(dim, {"items": gate["items"]}, client=client)
            judgement = result["judgement"]
            judgement["retrieval_quality"] = gate["retrieval_quality"]
            trace_extra = {
                "retrieval_quality": gate["retrieval_quality"],
                "relevant_items": gate["items"],
                "adequacy_trace": result["trace"],
            }

        judgements[dim_id] = judgement
        path = TRACE_DIR / f"assess_llm_{dim_id}-{uuid.uuid4().hex[:8]}.json"
        path.write_text(
            json.dumps({"t": time.time(), "dimension_id": dim_id, **trace_extra,
                        "judgement": judgement}, indent=2),
            encoding="utf-8",
        )
        trace_paths.append(str(path))
    return {"judgements": judgements, "trace_paths": trace_paths}
