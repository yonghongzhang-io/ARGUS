"""Stage 5 — report (deterministic).

Render a transparent, evidence-anchored report for a human reviewer. ARGUS
surfaces and localizes risks; it does not adjudicate the true causal effect.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

RESULTS_DIR = Path(__file__).resolve().parents[3] / "results" / "reports"


def render(
    paper: dict[str, Any],
    risk_map: dict[str, Any],
    assessed: dict[str, Any],
) -> dict[str, Any]:
    paper_id = paper.get("id", "unknown")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{_safe_filename(str(paper_id))}.md"

    lines = [f"# ARGUS identification audit — {paper_id}", ""]
    lines.append("> Audits identification *credibility*, not the true causal effect.")
    lines.append("")
    for dim_id in risk_map["ranked"]:
        d = risk_map["by_dimension"][dim_id]
        header = f"## {dim_id} — risk: {d['risk']}"
        if d.get("retrieval_quality"):
            header += f" (retrieval: {d['retrieval_quality']})"
        lines.append(header)
        if d.get("rationale"):
            lines.append(d["rationale"])
        for ev in d.get("cited_evidence", []):
            lines.append(f"- evidence: {_format_evidence(ev)}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return {"report_path": str(path)}


def _format_evidence(evidence: Any) -> str:
    if not isinstance(evidence, dict):
        return str(evidence)
    source = evidence.get("source", "unknown")
    text = str(evidence.get("text", "")).strip()
    if len(text) > 500:
        text = text[:497].rstrip() + "..."
    return f"{source}: {text}"


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return safe or "unknown"
