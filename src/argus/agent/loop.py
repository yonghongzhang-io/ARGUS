"""Bounded ReAct-style loop.

Deliberately *not* an open-ended autonomous agent. Each call gets:
  - a small fixed tool set (passed in),
  - a hard step budget (`max_steps`) — the loop cannot wander indefinitely,
  - a logged trace of every step / tool call / cited evidence.

These three constraints are what keep ARGUS reproducible and evidence-traceable.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable

TRACE_DIR = Path(__file__).resolve().parents[3] / "results" / "traces"

Tool = Callable[..., Any]


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
    trace: list[dict[str, Any]] = []
    run_id = f"{task.replace(':', '_')}-{uuid.uuid4().hex[:8]}"

    output: Any = None
    for step in range(max_steps):
        # --- model reason/act step goes here ---
        # A real step proposes one tool call from `tools` only, or stops.
        decision = _next_step_stub(task, context, step)
        trace.append({"step": step, "t": time.time(), **decision})

        if decision["action"] == "stop":
            output = decision.get("output")
            break
        tool_name = decision["action"]
        if tool_name not in tools:
            # hard tool gate: the loop may only call its fixed tool set
            trace.append({"step": step, "error": f"tool not permitted: {tool_name}"})
            break
        # tools[tool_name](**decision.get("args", {}))  # executed in real impl
    else:
        trace.append({"step": max_steps, "note": "step budget exhausted"})

    trace_path = TRACE_DIR / f"{run_id}.json"
    trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    return {"output": output, "trace_path": str(trace_path)}


def _next_step_stub(task: str, context: dict[str, Any], step: int) -> dict[str, Any]:
    """Placeholder for the model-driven reason/act step.

    Real implementation: prompt the model with the task + accumulated evidence,
    parse a single action (one tool call or `stop`). Stubbed to stop immediately.
    """
    raise NotImplementedError(
        "Agent reason/act step not implemented yet — see config/ for the rubric "
        "the loop operates over."
    )
