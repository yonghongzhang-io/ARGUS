"""Compare the keyword baseline vs the LLM evidence-adequacy assessor.

Runs the full flaw-injection evaluation twice on the same fixture — once with
each assessor — and prints detection / false-alarm / localization side by side.
Extraction is identical for both, so the only thing that changes is the
judgement policy: keyword presence-scoring vs LLM adequacy-reasoning.

Requires an OpenAI key for the LLM run:
    export OPENAI_API_KEY=sk-...
    # optional: export ARGUS_LLM_MODEL=gpt-4o
    PYTHONPATH=src python3 experiments/phase1_pilot/compare_assessors.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from argus.config import load_flaws  # noqa: E402
from argus.evaluation.runner import evaluate_flaws  # noqa: E402

PAPER = ROOT / "examples" / "papers" / "clean_supported.json"


def summarize(assessor: str) -> dict:
    paper = json.loads(PAPER.read_text())
    return evaluate_flaws(paper, sorted(load_flaws()), max_steps=1, assessor=assessor)["summary"]


def main() -> None:
    rows = [("keyword baseline", summarize("keyword"))]

    if os.environ.get("OPENAI_API_KEY"):
        model = os.environ.get("ARGUS_LLM_MODEL", "gpt-4o")
        # M4 ablation: single-pass (no architecture) vs two-stage (full
        # architecture); same model + rubric + fixture, so only structure differs.
        rows.append((f"single-pass LLM ({model})", summarize("single_pass")))
        rows.append((f"two-stage LLM ({model})", summarize("llm")))
    else:
        print("OPENAI_API_KEY not set — skipping the LLM runs (single_pass + two-stage).")
        print("Export it and re-run for the keyword vs single-pass vs two-stage table.\n")

    print("{:<26}{:>11}{:>13}{:>15}".format("assessor", "detection", "false_alarm", "localization"))
    print("-" * 65)
    for name, s in rows:
        print("{:<26}{:>11.3f}{:>13.3f}{:>15.3f}".format(
            name, s["detection_rate"], s["false_alarm_rate"], s["localization_acc"]))


if __name__ == "__main__":
    main()
