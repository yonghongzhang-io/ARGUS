"""Emit a blind dimension-level annotation sheet for one paper.

One row per rubric dimension, with the assumption/implication pre-filled as a
prompt and the human columns blank. ARGUS's own judgement is deliberately NOT
included, to avoid anchoring the annotator (see annotation/guideline.md).

Usage:
    PYTHONPATH=src python3 experiments/annotation/build_tasks.py PAPER.md [--annotator A]
Writes data/annotations/<paper_id>_<annotator>.csv (gitignored).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from argus.config import load_dimensions  # noqa: E402
from argus.ingest import ingest_file  # noqa: E402

OUT_DIR = ROOT / "data" / "annotations"
HUMAN_COLS = ["reported", "evidence_status", "risk", "ambiguity_flag",
              "confidence", "evidence_location", "rationale"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paper", help="path to a .md/.txt paper (Markdown convention)")
    ap.add_argument("--annotator", default="A")
    args = ap.parse_args()

    paper = ingest_file(args.paper)
    dims = load_dimensions()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{paper['id']}_{args.annotator}.csv"

    header = ["paper_id", "dimension", "assumption", "implication", "expected_evidence",
              *HUMAN_COLS, "annotator_id"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for dim_id, d in dims.items():
            w.writerow([
                paper["id"], dim_id, d["assumption"], d["implication"],
                "; ".join(d.get("evidence", [])),
                "", "", "", "", "", "", "",            # blank human columns
                args.annotator,
            ])
    print(f"wrote {out.relative_to(ROOT)}  ({len(dims)} dimensions, annotator={args.annotator})")
    print("Fill the blank columns while reading the paper; do not consult ARGUS output.")


if __name__ == "__main__":
    main()
