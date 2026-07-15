"""Generate gold_expansion_template.csv from the papers marked selected=y.

Run after marking selections in candidate_papers.csv:
    python3 annotation/expansion/make_template.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

dims = yaml.safe_load(open(ROOT / "config" / "identification_dimensions.yaml"))["dimensions"]
cands = list(csv.DictReader(open(HERE / "candidate_papers.csv")))
selected = [c for c in cands if c.get("selected(y/n)", "").strip().lower() == "y"]
if not selected:
    raise SystemExit("no papers marked selected=y in candidate_papers.csv yet")

out = HERE / "gold_expansion_template.csv"
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["paper_id", "title", "dimension", "dimension_name", "assumption",
                "applicability", "evidence_risk", "evidence_span",
                "evidence_location", "confidence", "notes"])
    for c in selected:
        for d in dims:
            w.writerow([c["paper_id"], c["title"][:80], d["id"], d["name"],
                        d["assumption"], "", "", "", "", "", ""])
print(f"wrote {out.name}: {len(selected)} papers x {len(dims)} dims = "
      f"{len(selected) * len(dims)} rows")
