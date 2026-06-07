#!/usr/bin/env python3
"""Data-driven adjudication for the gold-expansion set (scales past the pilot).

The pilot adjudicate.py hard-codes 27 verdicts in a Python dict -- fine for 5
papers, unworkable for 25. This version reads the verdicts from a CSV the
annotation lead fills, so adjudicating more papers never touches code.

Two steps:

  1) emit the disagreements to adjudicate (after A/B sheets are filled):
       python3 .../adjudicate_v2.py --emit-disagreements
     -> writes verdicts_template.csv with A_risk/B_risk filled and
        winner/ambiguous blank for the lead to complete.

  2) build gold once verdicts.csv is filled (winner in {A,B,both}, ambiguous 0/1):
       python3 .../adjudicate_v2.py --verdicts verdicts.csv
     -> writes gold_labels_expansion.csv  (same schema as the pilot gold:
        paper_id,dimension,gold_risk,ambiguous,source), so compare_argus_gold.py
        and calibrate_argus.py consume it unchanged.

Agreed cells keep their shared label; 'both' resolves conservatively to the
higher severity (matching the pilot's rule).
"""
from __future__ import annotations

import argparse
import csv
import glob
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ANN = ROOT / "data" / "annotations" / "gold_expansion"
HERE = Path(__file__).resolve().parent
RANK = {"low": 0, "medium": 1, "high": 2}


def load_side(suffix: str) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for f in glob.glob(str(ANN / f"*_{suffix}.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            v = (r.get("risk") or "").strip().lower()
            if v:
                out[(r["paper_id"], r["dimension"])] = v
    return out


def emit_disagreements(A: dict, B: dict, out_path: Path) -> int:
    keys = sorted(set(A) & set(B))
    disagree = [k for k in keys if A[k] != B[k]]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["paper_id", "dimension", "A_risk", "B_risk", "winner", "ambiguous"])
        for k in disagree:
            w.writerow([k[0], k[1], A[k], B[k], "", ""])
    return len(disagree)


def load_verdicts(path: Path) -> dict[tuple[str, str], tuple[str, int]]:
    v: dict[tuple[str, str], tuple[str, int]] = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        winner = (r.get("winner") or "").strip().upper()[:1]  # A / B / B(oth)->B? keep explicit
        winner = (r.get("winner") or "").strip().lower()
        amb = 1 if str(r.get("ambiguous", "")).strip() in ("1", "true", "yes") else 0
        v[(r["paper_id"], r["dimension"])] = (winner, amb)
    return v


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-disagreements", action="store_true")
    ap.add_argument("--verdicts", default=str(HERE / "verdicts.csv"))
    ap.add_argument("--out", default=str(ANN / "gold_labels_expansion.csv"))
    args = ap.parse_args()

    A, B = load_side("A"), load_side("B")
    if not A or not B:
        raise SystemExit(f"no filled *_A.csv / *_B.csv with a `risk` value in {ANN}\n"
                         "fill the annotation sheets first.")
    keys = sorted(set(A) & set(B))

    if args.emit_disagreements:
        tmpl = HERE / "verdicts_template.csv"
        n = emit_disagreements(A, B, tmpl)
        agree = len(keys) - n
        print(f"overlap cells: {len(keys)}  | agree: {agree}  | disagree: {n}")
        print(f"wrote {tmpl.relative_to(ROOT)}  (fill winner in {{A,B,both}} + ambiguous 0/1,")
        print(f"      save as verdicts.csv, then rerun without --emit-disagreements)")
        return

    verdicts_path = Path(args.verdicts)
    if not verdicts_path.exists():
        raise SystemExit(f"verdicts file not found: {verdicts_path}\n"
                         "run with --emit-disagreements first, fill it, save as verdicts.csv")
    verdicts = load_verdicts(verdicts_path)

    gold, won, amb = [], Counter(), 0
    unresolved = []
    for k in keys:
        a, b = A[k], B[k]
        if a == b:
            gold.append((*k, a, 0, "agree"))
            continue
        if k not in verdicts or not verdicts[k][0]:
            unresolved.append(k)
            continue
        winner, ambiguous = verdicts[k]
        if winner == "a":
            g = a
        elif winner == "b":
            g = b
        elif winner == "both":
            g = a if RANK.get(a, 0) >= RANK.get(b, 0) else b
        else:
            unresolved.append(k)
            continue
        won[winner] += 1
        amb += ambiguous
        gold.append((*k, g, ambiguous, f"adj:{winner}"))

    if unresolved:
        print(f"WARNING: {len(unresolved)} disagreements have no verdict; not written:")
        for k in unresolved[:20]:
            print(f"   {k[0]} {k[1]}  A={A[k]} B={B[k]}")
        print("   fill these in verdicts.csv and rerun.\n")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["paper_id", "dimension", "gold_risk", "ambiguous", "source"])
        w.writerows(gold)

    disputes = sum(1 for k in keys if A[k] != B[k])
    print(f"gold cells written: {len(gold)} -> {Path(args.out).relative_to(ROOT)}")
    print(f"  disputes: {disputes}  resolved: {disputes - len(unresolved)}  "
          f"ambiguous: {amb}  direction: {dict(won)}")
    print("  gold risk distribution:", dict(Counter(g[2] for g in gold)))
    print("  high cells:", sum(1 for g in gold if g[2] == "high"),
          "(pilot had 2 -- aim higher for stable precision/recall)")


if __name__ == "__main__":
    main()
