"""Week-0 reality check: run ARGUS on a real DID paper.

Ingest a paper (Markdown convention, see src/argus/ingest.py), audit it, and
print the per-dimension risk map. This tests external validity — does the
pipeline handle real (messy) text, and are the judgements sensible — before any
annotation work begins.

Usage:
    PYTHONPATH=src python3 experiments/real_papers/run_real_paper.py PAPER.md
    # LLM assessor (needs OPENAI_API_KEY):
    PYTHONPATH=src python3 experiments/real_papers/run_real_paper.py PAPER.md --llm

The ingested JSON is written to data/real_papers/<id>.json (gitignored — real
papers are copyrighted, keep them out of the repo).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from argus.ingest import ingest_file  # noqa: E402
from argus.pipeline.audit import run_audit  # noqa: E402

DATA_DIR = ROOT / "data" / "real_papers"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paper", help="path to a .md/.txt (Markdown convention) or .pdf")
    ap.add_argument("--llm", action="store_true", help="use the LLM assessor (needs OPENAI_API_KEY)")
    ap.add_argument("--max-steps", type=int, default=1)
    args = ap.parse_args()

    paper = ingest_file(args.paper)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / f"{paper['id']}.json").write_text(json.dumps(paper, indent=2), encoding="utf-8")

    n_sec = len(paper.get("sections", {}))
    print(f"ingested '{paper['id']}': {n_sec} sections, "
          f"{len(paper.get('figures', []))} figures, {len(paper.get('tables', []))} tables")
    if n_sec == 0:
        print("WARNING: no sections parsed — check the Markdown convention (## headings).")

    assessor = "llm" if args.llm else "keyword"
    result = run_audit(paper, max_steps=args.max_steps, assessor=assessor)

    print(f"\n=== ARGUS risk map ({assessor}) ===")
    print(f"{'dimension':28}{'risk':8}rationale")
    print("-" * 78)
    for dim_id in result.risk_map["ranked"]:
        d = result.risk_map["by_dimension"][dim_id]
        rat = (d.get("rationale") or "")[:60]
        print(f"{dim_id:28}{str(d['risk']):8}{rat}")
    print(f"\nreport: {result.report_path}")


if __name__ == "__main__":
    main()
