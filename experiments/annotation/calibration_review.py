"""Build the calibration-review sheet: every A/B risk disagreement, with both
rationales and a targeted calibration question.

The annotators review ONLY these rows (not all 55), decide per row whether A is
right, B is right, or both are reasonable (-> ambiguity_flag), and use the
pattern to anchor the low/medium/high boundaries in annotation/guideline.md.

Usage:
    PYTHONPATH=src python3 experiments/annotation/calibration_review.py
Writes data/annotations/calibration_review.csv (gitignored) and prints a summary.
"""

from __future__ import annotations

import csv
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANN = ROOT / "data" / "annotations"
RANK = {"low": 0, "medium": 1, "high": 2}


def load(suffix: str) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for f in glob.glob(str(ANN / f"*_{suffix}.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            out[(r["paper_id"], r["dimension"])] = r
    return out


def question(a: str, b: str) -> str:
    pair = {a, b}
    if pair == {"low", "medium"}:
        return ("low vs medium: does a reported-but-incomplete check, or an "
                "unresolved residual concern, stay low or become medium? Anchor "
                "the low/medium boundary.")
    if pair == {"medium", "high"}:
        return ("medium vs high: is the evidence merely vague/absent (-> high) or "
                "partially present (-> medium)? Anchor the medium/high boundary.")
    if pair == {"low", "high"}:
        return ("DIRECTION REVERSAL: one sees adequate evidence, the other sees "
                "none. Reconcile reading/retrieval before anchoring severity.")
    return "review"


def main() -> None:
    A, B = load("A"), load("B")
    keys = sorted(set(A) & set(B))
    rows = []
    for k in keys:
        ra, rb = (A[k]["risk"] or "").strip().lower(), (B[k]["risk"] or "").strip().lower()
        if ra == rb:
            continue
        dist = abs(RANK.get(ra, -9) - RANK.get(rb, -9))
        rows.append({
            "paper_id": k[0], "dimension": k[1],
            "A_risk": ra, "B_risk": rb,
            "distance": dist,
            "A_evidence_status": A[k].get("evidence_status", ""),
            "B_evidence_status": B[k].get("evidence_status", ""),
            "A_ambiguity": A[k].get("ambiguity_flag", ""),
            "B_ambiguity": B[k].get("ambiguity_flag", ""),
            "A_rationale": A[k].get("rationale", ""),
            "B_rationale": B[k].get("rationale", ""),
            "calibration_question": question(ra, rb),
            "verdict_A_B_both": "",   # annotators fill: A / B / both(->ambiguity)
            "anchor_note": "",        # annotators fill: the rule this implies
        })
    rows.sort(key=lambda r: (-r["distance"], r["paper_id"], r["dimension"]))

    ANN.mkdir(parents=True, exist_ok=True)
    out = ANN / "calibration_review.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"{len(rows)} disagreements -> {out.relative_to(ROOT)}\n")
    from collections import Counter
    pat = Counter(tuple(sorted((r["A_risk"], r["B_risk"]))) for r in rows)
    print("disagreement types:", {f"{a}/{b}": n for (a, b), n in pat.items()})
    print(f"direction reversals (low/high): {sum(r['distance'] == 2 for r in rows)}\n")
    for r in rows:
        tag = "  !!" if r["distance"] == 2 else ""
        print(f"[{r['paper_id']} / {r['dimension']}] A={r['A_risk']} B={r['B_risk']}{tag}")


if __name__ == "__main__":
    main()
