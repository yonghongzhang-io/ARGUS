"""Apply the calibration-round verdicts to build adjudicated gold labels.

Encodes the round-1 adjudication of the 27 A/B disagreements (winner + whether
the cell is intrinsically ambiguous). Agreed cells keep their shared label.
Writes data/annotations/gold_labels.csv (gitignored) and prints the calibration
outcome: how many disputes were resolved cleanly vs. flagged ambiguous, the gold
distribution, and which way the resolutions went.

Run: PYTHONPATH=src python3 experiments/annotation/adjudicate.py
"""

from __future__ import annotations

import csv
import glob
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANN = ROOT / "data" / "annotations"
RANK = {"low": 0, "medium": 1, "high": 2}

# (paper, dimension) -> (winner in {A,B,both}, intrinsically_ambiguous)
VERDICTS = {
    ("paper_08", "no_anticipation"): ("A", True),
    ("paper_01", "concurrent_policies"): ("B", False),
    ("paper_01", "data_measurement"): ("both", True),
    ("paper_01", "inference"): ("B", False),
    ("paper_01", "no_anticipation"): ("B", False),
    ("paper_01", "parallel_trends"): ("B", True),
    ("paper_01", "sample_period"): ("B", False),
    ("paper_01", "treatment_definition_sutva"): ("B", False),
    ("paper_03", "concurrent_policies"): ("A", False),
    ("paper_03", "inference"): ("A", True),
    ("paper_03", "no_anticipation"): ("B", False),
    ("paper_03", "sample_period"): ("B", False),
    ("paper_03", "specification"): ("both", True),
    ("paper_03", "treatment_timing"): ("B", False),
    ("paper_07", "concurrent_policies"): ("A", True),
    ("paper_07", "no_anticipation"): ("A", False),
    ("paper_07", "parallel_trends"): ("A", True),
    ("paper_07", "treatment_timing"): ("A", False),
    ("paper_08", "data_measurement"): ("B", False),
    ("paper_08", "inference"): ("A", False),
    ("paper_08", "parallel_trends"): ("A", True),
    ("paper_08", "treatment_timing"): ("A", True),
    ("paper_10", "concurrent_policies"): ("A", True),
    ("paper_10", "inference"): ("A", False),
    ("paper_10", "no_anticipation"): ("B", False),
    ("paper_10", "sample_period"): ("B", False),
    ("paper_10", "treatment_timing"): ("B", True),
}


def load(suffix: str) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for f in glob.glob(str(ANN / f"*_{suffix}.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            out[(r["paper_id"], r["dimension"])] = (r.get("risk") or "").strip().lower()
    return out


def main() -> None:
    A, B = load("A"), load("B")
    keys = sorted(set(A) & set(B))
    gold = []
    won = Counter()
    amb_disputes = 0

    for k in keys:
        a, b = A[k], B[k]
        if a == b:
            gold.append((*k, a, 0, "agree"))
            continue
        winner, ambiguous = VERDICTS[k]
        if winner == "A":
            g = a
        elif winner == "B":
            g = b
        else:  # both reasonable -> conservative (higher severity)
            g = a if RANK[a] >= RANK[b] else b
        won[winner] += 1
        if ambiguous:
            amb_disputes += 1
        gold.append((*k, g, int(ambiguous), f"adj:{winner}"))

    ANN.mkdir(parents=True, exist_ok=True)
    out = ANN / "gold_labels.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["paper_id", "dimension", "gold_risk", "ambiguous", "source"])
        w.writerows(gold)

    disputes = sum(1 for k in keys if A[k] != B[k])
    print(f"gold labels: {len(gold)} cells -> {out.relative_to(ROOT)}\n")
    print(f"disputes adjudicated: {disputes}")
    print(f"  clean resolution (single label): {disputes - amb_disputes}")
    print(f"  flagged intrinsically ambiguous: {amb_disputes}")
    print(f"  resolution direction: {dict(won)}  (A=annotator A upheld, etc.)\n")
    print("gold risk distribution:", dict(Counter(g[2] for g in gold)))
    print("ambiguous cells (of 55):", sum(g[3] for g in gold))


if __name__ == "__main__":
    main()
