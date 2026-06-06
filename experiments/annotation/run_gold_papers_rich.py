"""Run ARGUS-LLM on the 5 gold papers, capturing FULL per-cell output.

did_llm_risks.csv only stores `risk`; the deterministic calibration layer needs
evidence_status / retrieval_quality / rationale too. This re-runs the 5 gold
papers and dumps the rich judgement per (paper, dimension), serving as the
consistent "before-calibration" baseline for the calibration experiment.

Run (needs OPENAI_API_KEY in .env):
    PYTHONPATH=src python3 experiments/annotation/run_gold_papers_rich.py
Writes data/annotations/argus_rich_gold5.csv (gitignored; contains rationale text).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from argus.ingest import ingest_file  # noqa: E402
from argus.pipeline.audit import run_audit  # noqa: E402

CV_MD = ROOT.parent / "CAUSALVERIFY" / "v11" / "pdfs-corpus" / "converted" / "markdown"
GOLD_PAPERS = ["paper_01", "paper_03", "paper_07", "paper_08", "paper_10"]
OUT = ROOT / "data" / "annotations" / "argus_rich_gold5.csv"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for pid in GOLD_PAPERS:
        paper = ingest_file(CV_MD / f"{pid}.md", paper_id=pid)
        result = run_audit(paper, max_steps=1, assessor="llm")
        for dim_id, d in result.risk_map["by_dimension"].items():
            rows.append({
                "paper_id": pid,
                "dimension": dim_id,
                "risk": d.get("risk", ""),
                "evidence_status": d.get("evidence_status", "") or "",
                "retrieval_quality": d.get("retrieval_quality", "") or "",
                "rationale": (d.get("rationale") or "").replace("\n", " "),
            })
        print(f"  ran {pid}")

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["paper_id", "dimension", "risk",
                                           "evidence_status", "retrieval_quality", "rationale"])
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {OUT.relative_to(ROOT)} ({len(rows)} cells)")


if __name__ == "__main__":
    main()
