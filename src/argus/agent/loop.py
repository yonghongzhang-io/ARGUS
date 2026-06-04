"""Bounded ReAct-style loop.

Deliberately *not* an open-ended autonomous agent. Each call gets:
  - a small fixed tool set (passed in),
  - a hard step budget (`max_steps`) — the loop cannot wander indefinitely,
  - a logged trace of every step / tool call / cited evidence.

These three constraints are what keep ARGUS reproducible and evidence-traceable.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable

TRACE_DIR = Path(__file__).resolve().parents[3] / "results" / "traces"

Tool = Callable[..., Any]

_NEGATIVE_SIGNALS = {
    "parallel_trends": [
        "different pre-treatment trends",
        "divergent pre-treatment",
        "non-zero pre-period",
        "significant pre-period",
        "significant leads",
        "failed pre-trend",
        "fail the pre-trend",
        "not parallel",
        "without a pre-trend test",
        "no pre-trend test",
    ],
    "no_anticipation": [
        "anticipation effect",
        "behaviour shifts before",
        "behavior shifts before",
        "announcement precedes",
        "significant lead",
        "shift before implementation",
    ],
    "treatment_timing": [
        "plain twfe",
        "two-way fixed effects only",
        "forbidden comparison",
        "already-treated units as controls",
        "negative-weight",
        "no staggered-adoption robustness",
    ],
    "treatment_definition_sutva": [
        "spillover contamination",
        "unaddressed carbon leakage",
        "leakage omitted",
        "untested leakage",
        "adjacent provinces as controls",
        "no interference discussion",
        "treated as clean controls",
    ],
    "control_group": [
        "large pre-treatment imbalance",
        "poorly matched",
        "noncomparable controls",
        "no balance table",
        "without balance",
    ],
    "specification": [
        "bad control",
        "post-treatment control",
        "on the causal path",
        "outcome-affected control",
        "sensitive to controls",
    ],
    "inference": [
        "unclustered standard errors",
        "wrongly clustered",
        "few clusters without",
        "serial correlation ignored",
        "spatial correlation ignored",
    ],
    "sample_period": [
        "cherry-picked window",
        "cherrypicked window",
        "favourable window",
        "favorable window",
        "no window sensitivity",
        "result concentrated in a narrow span",
    ],
    "concurrent_policies": [
        "unaddressed co-timed policy",
        "unaddressed concurrent policy",
        "left unaddressed",
        "confounding policy",
        "another policy explains",
    ],
    "robustness_placebo": [
        "no placebo",
        "missing placebo",
        "without falsification",
        "no falsification",
        "no permutation",
    ],
    "data_measurement": [
        "measurement break",
        "definition change",
        "reporting change",
        "measurement regime shift",
        "coincides with treatment",
    ],
}

_POSITIVE_SIGNALS = {
    "parallel_trends": ["parallel trend", "pre-trend", "event-study", "event study", "placebo"],
    "no_anticipation": ["no anticipation", "announcement", "implementation", "leads"],
    "treatment_timing": ["callaway", "sun-abraham", "goodman-bacon", "staggered", "heterogeneous"],
    "treatment_definition_sutva": ["spillover", "sutva", "buffer", "leakage", "interference"],
    "control_group": ["balance table", "matched", "matching", "synthetic control", "donor pool"],
    "specification": ["robustness", "specification", "fixed effects", "controls"],
    "inference": ["clustered", "wild-cluster", "bootstrap", "serial correlation"],
    "sample_period": ["window sensitivity", "sample period", "unbalanced panel", "start period", "end period"],
    "concurrent_policies": ["concurrent", "co-timed", "policy controls", "placebo periods"],
    "robustness_placebo": ["placebo", "falsification", "permutation", "randomization"],
    "data_measurement": ["data source", "definition stability", "missingness", "measurement"],
}

_SEARCH_TERMS = {
    "parallel_trends": "parallel trends pre-trend pretrend event-study event study placebo leads",
    "no_anticipation": "no anticipation anticipation announcement implementation leads timeline",
    "treatment_timing": (
        "staggered adoption treatment timing callaway santanna sun-abraham "
        "goodman-bacon twfe heterogeneous effects"
    ),
    "treatment_definition_sutva": (
        "sutva spillover interference carbon leakage buffer zone treatment definition"
    ),
    "control_group": "control group balance table matching matched synthetic control donor pool",
    "specification": "specification robustness fixed effects controls functional form bad control",
    "inference": "standard errors clustering clustered wild-cluster bootstrap inference",
    "sample_period": "sample period sample frame time window window sensitivity unbalanced panel",
    "concurrent_policies": "concurrent policies co-timed intervention policy controls placebo periods",
    "robustness_placebo": "robustness placebo falsification permutation randomization inference",
    "data_measurement": "data measurement data source definition stability reporting changes missingness",
}


def run_bounded_loop(
    *,
    task: str,
    context: dict[str, Any],
    tools: dict[str, Tool],
    max_steps: int,
) -> dict[str, Any]:
    """Run one bounded loop for a single sub-task.

    Returns {"output": ..., "trace_path": str}. The model-driven reason/act body
    is a stub; the budget enforcement, tool gating, and trace logging that make
    the loop *bounded* are the real contract and are implemented here.
    """
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")

    trace: list[dict[str, Any]] = []
    run_id = f"{task.replace(':', '_')}-{uuid.uuid4().hex[:8]}"

    output: Any = None
    state: dict[str, Any] = {"observations": []}
    for step in range(max_steps):
        decision = _next_step_baseline(task, context, step, state)
        trace.append({"step": step, "t": time.time(), **_trace_decision(decision)})

        if decision["action"] == "stop":
            output = decision.get("output")
            break
        tool_name = decision["action"]
        if tool_name not in tools:
            # hard tool gate: the loop may only call its fixed tool set
            trace.append({"step": step, "error": f"tool not permitted: {tool_name}"})
            break
        result = tools[tool_name](**decision.get("args", {}))
        observation = {"tool": tool_name, "result": result}
        state["observations"].append(observation)
        trace.append({"step": step, "t": time.time(), "observation": observation})

        output = _finish_after_tool(task, context, state)
        if output is not None:
            trace.append({"step": step, "t": time.time(), "action": "stop", "output": output})
            break
    else:
        trace.append({"step": max_steps, "note": "step budget exhausted"})

    trace_path = TRACE_DIR / f"{run_id}.json"
    trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    return {"output": output, "trace_path": str(trace_path)}


def _next_step_baseline(
    task: str,
    context: dict[str, Any],
    step: int,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic baseline policy for the bounded loop.

    This is intentionally simple: it gives ARGUS an auditable fallback path before
    a model-driven reason/act policy is added.
    """
    if task.startswith("extract_evidence:"):
        if not state["observations"]:
            dimension = context["dimension"]
            return {
                "action": "evidence_search",
                "args": {
                    "paper": context["paper"],
                    "query": _build_query(dimension),
                    "k": 5,
                },
            }
        return {"action": "stop", "output": _format_extraction(task, context, state)}

    if task.startswith("assess_chain:"):
        return {"action": "stop", "output": _assess_chain(task, context)}

    return {"action": "stop", "output": None}


def _finish_after_tool(task: str, context: dict[str, Any], state: dict[str, Any]) -> Any:
    if task.startswith("extract_evidence:"):
        return _format_extraction(task, context, state)
    return None


def _build_query(dimension: dict[str, Any]) -> str:
    dim_id = dimension.get("id")
    if dim_id in _SEARCH_TERMS:
        return _SEARCH_TERMS[dim_id]

    expected = " ".join(dimension.get("expected_evidence", []))
    return " ".join(
        str(part)
        for part in (
            dimension.get("name", ""),
            dimension.get("assumption", ""),
            dimension.get("implication", ""),
            expected,
        )
        if part
    )


def _dimension_id(task: str, context: dict[str, Any]) -> str:
    if ":" in task:
        return task.split(":", 1)[1]
    return str(context.get("dimension", {}).get("id", "unknown"))


def _format_extraction(task: str, context: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    dim_id = _dimension_id(task, context)
    observations = state["observations"]
    items = []
    if observations:
        items = observations[-1]["result"] or []
    return {
        "dimension_id": dim_id,
        "query": _build_query(context["dimension"]),
        "items": items,
        "support_level": _support_level(items),
    }


def _support_level(items: list[dict[str, Any]]) -> str:
    if not items:
        return "none"
    if len(items) == 1:
        return "weak"
    return "moderate"


def _assess_chain(task: str, context: dict[str, Any]) -> dict[str, Any]:
    dim_id = _dimension_id(task, context)
    evidence = context.get("evidence") or {}
    items = evidence.get("items") or []
    snippets = [_normalise(item.get("text", "")) for item in items]
    joined = " ".join(snippets)

    negative_hits = _hits(joined, _NEGATIVE_SIGNALS.get(dim_id, []))
    positive_hits = _hits(joined, _POSITIVE_SIGNALS.get(dim_id, []))

    if not items:
        risk = "high"
        rationale = "No relevant evidence was found for this identification dimension."
    elif negative_hits:
        risk = "high" if len(negative_hits) >= 2 else "medium"
        rationale = "Evidence contains risk signals: " + ", ".join(negative_hits[:5]) + "."
    elif len(items) == 1 and not positive_hits:
        risk = "medium"
        rationale = "Only weak evidence was found, with no strong supporting signal."
    else:
        risk = "low"
        if positive_hits:
            rationale = "Evidence contains supporting signals: " + ", ".join(positive_hits[:5]) + "."
        else:
            rationale = "Relevant evidence was found and no configured risk signal was detected."

    return {
        "risk": risk,
        "rationale": rationale,
        "cited_evidence": [
            {
                "source": item.get("source", "unknown"),
                "text": item.get("text", ""),
                "score": item.get("score"),
            }
            for item in items[:3]
        ],
    }


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _hits(text: str, phrases: list[str]) -> list[str]:
    return [phrase for phrase in phrases if phrase in text]


def _trace_decision(decision: dict[str, Any]) -> dict[str, Any]:
    if decision.get("action") != "evidence_search":
        return decision
    args = decision.get("args", {})
    paper = args.get("paper", {})
    return {
        "action": decision["action"],
        "args": {
            "paper_id": paper.get("id", "unknown") if isinstance(paper, dict) else "unknown",
            "query": args.get("query"),
            "k": args.get("k"),
        },
    }
