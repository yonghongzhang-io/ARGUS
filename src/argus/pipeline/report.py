"""Stage 5 — report (deterministic).

Render a transparent, evidence-anchored report for a human reviewer. ARGUS
surfaces and localizes risks; it does not adjudicate the true causal effect.
"""

from __future__ import annotations

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
    path = RESULTS_DIR / f"{paper_id}.md"

    lines = [f"# ARGUS identification audit — {paper_id}", ""]
    lines.append("> Audits identification *credibility*, not the true causal effect.")
    lines.append("")
    for dim_id in risk_map["ranked"]:
        d = risk_map["by_dimension"][dim_id]
        lines.append(f"## {dim_id} — risk: {d['risk']}")
        if d.get("rationale"):
            lines.append(d["rationale"])
        for ev in d.get("cited_evidence", []):
            lines.append(f"- evidence: {ev}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return {"report_path": str(path)}
