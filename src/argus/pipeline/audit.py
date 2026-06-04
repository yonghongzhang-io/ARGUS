"""Deterministic orchestration of the audit pipeline.

The control flow here is intentionally plain Python: the sequence of stages is
fixed and reproducible. Agency is confined to `extraction` and `assessment`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import assessment, decomposition, extraction, localization, report


@dataclass
class AuditResult:
    paper_id: str
    risk_map: dict[str, Any]      # dimension_id -> risk
    report_path: str
    trace_paths: list[str]


def run_audit(paper: dict[str, Any], *, max_steps: int = 12) -> AuditResult:
    """Run the full audit on a single parsed DID paper.

    `max_steps` is the hard step budget passed to each agentic stage.
    """
    skeleton = decomposition.decompose(paper)
    evidence = extraction.extract(paper, skeleton, max_steps=max_steps)
    assessed = assessment.assess(skeleton, evidence, max_steps=max_steps)
    risk_map = localization.localize(assessed)
    out = report.render(paper, risk_map, assessed)
    return AuditResult(
        paper_id=paper.get("id", "unknown"),
        risk_map=risk_map,
        report_path=out["report_path"],
        trace_paths=evidence.get("trace_paths", []) + assessed.get("trace_paths", []),
    )
