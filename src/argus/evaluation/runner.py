"""Orchestrate the clean-vs-injected evaluation loop."""

from __future__ import annotations

from typing import Any, Optional

from ..config import load_flaws
from ..paper import PaperPath, load_paper
from ..pipeline.audit import AuditResult, run_audit
from .injection import inject_flaw
from .metrics import evaluate_pair, summarize_results


def evaluate_injected_pair(
    clean_paper: dict[str, Any],
    flaw_id: str,
    *,
    max_steps: int = 12,
    threshold: str = "medium",
) -> dict[str, Any]:
    """Inject one flaw, run clean/injected audits, and score the pair."""
    injected_paper = inject_flaw(clean_paper, flaw_id)
    ground_truth = injected_paper["argus_ground_truth"]

    clean_audit = run_audit(clean_paper, max_steps=max_steps)
    injected_audit = run_audit(injected_paper, max_steps=max_steps)
    score = evaluate_pair(
        clean_audit.risk_map,
        injected_audit.risk_map,
        ground_truth["target_dimension"],
        threshold=threshold,
    )

    return {
        "flaw_id": flaw_id,
        "ground_truth": ground_truth,
        "score": score,
        "clean_audit": clean_audit,
        "injected_audit": injected_audit,
    }


def evaluate_flaws(
    clean_paper: dict[str, Any],
    flaw_ids: Optional[list[str]] = None,
    *,
    max_steps: int = 12,
    threshold: str = "medium",
) -> dict[str, Any]:
    """Run the evaluation loop for multiple injected flaws."""
    selected = flaw_ids or sorted(load_flaws())
    pair_results = [
        evaluate_injected_pair(clean_paper, flaw_id, max_steps=max_steps, threshold=threshold)
        for flaw_id in selected
    ]
    scores = [result["score"] for result in pair_results]
    return {"pairs": pair_results, "summary": summarize_results(scores)}


def evaluate_paper_file(
    paper_path: PaperPath,
    flaw_ids: Optional[list[str]] = None,
    *,
    max_steps: int = 12,
    threshold: str = "medium",
) -> dict[str, Any]:
    """Load a parsed-paper JSON file and run the flaw-injection evaluation loop."""
    return evaluate_flaws(
        load_paper(paper_path),
        flaw_ids=flaw_ids,
        max_steps=max_steps,
        threshold=threshold,
    )


__all__ = ["AuditResult", "evaluate_injected_pair", "evaluate_flaws", "evaluate_paper_file"]
