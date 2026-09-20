"""Lock the final human gold after the two-cell re-adjudication. Runs once.

Reads the frozen June gold (`pilot_frozen/gold_labels.csv`) and the annotators' decisions in
`readjudication.csv`, and writes `gold_final/gold_labels.csv` with a lock record. The frozen
gold is not touched. A decision is one of

    keep      the adjudicated label stands
    relabel   the label becomes `new_label` (low | medium | high)
    exclude   the dimension does not apply to the study's design; the cell leaves the gold

Every row of `readjudication.csv` must be complete (decision, rationale, decided_by, date)
before anything is written, and the script refuses to run a second time: the gold is decided
once, by the annotators, before the numbers are regenerated, and is not adjusted afterwards.

    python3 experiments/annotation/finalize_gold.py            # validate, write, lock
    python3 experiments/annotation/finalize_gold.py --check    # validate only
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

from goldpath import FINAL_GOLD, FROZEN_GOLD

ANN = Path(__file__).resolve().parent
READJ = ANN / "readjudication.csv"
LOCK = FINAL_GOLD.parent / "LOCK.json"
LABELS = {"low", "medium", "high"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_decisions(gold: dict[tuple[str, str], dict[str, str]]) -> list[dict[str, str]]:
    rows = list(csv.DictReader(READJ.open(encoding="utf-8")))
    problems = []
    for r in rows:
        key = (r["paper_id"], r["dimension"])
        d = r["decision"].strip().lower()
        if key not in gold:
            problems.append(f"{key}: not a pilot cell")
        elif r["original_gold"].strip().lower() != gold[key]["gold_risk"]:
            problems.append(f"{key}: original_gold does not match the frozen gold")
        if d not in {"keep", "relabel", "exclude"}:
            problems.append(f"{key}: decision is {r['decision']!r}; expected keep, relabel or exclude")
        if d == "relabel" and r["new_label"].strip().lower() not in LABELS:
            problems.append(f"{key}: relabel needs new_label in {sorted(LABELS)}")
        if d == "relabel" and r["new_label"].strip().lower() == r["original_gold"].strip().lower():
            problems.append(f"{key}: relabel to the same label; use keep")
        for field in ("rationale", "decided_by", "date"):
            if not r[field].strip():
                problems.append(f"{key}: {field} is empty")
    if problems:
        raise SystemExit("readjudication.csv is not complete; nothing written:\n  " + "\n  ".join(problems))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate readjudication.csv and stop")
    args = ap.parse_args()
    if LOCK.exists():
        raise SystemExit(f"{LOCK.relative_to(ANN.parents[1])} exists: the final gold is locked and is not regenerated.")
    frozen = list(csv.DictReader(FROZEN_GOLD.open(encoding="utf-8")))
    gold = {(r["paper_id"], r["dimension"]): r for r in frozen}
    decisions = load_decisions(gold)
    if args.check:
        print("readjudication.csv is complete:", [(r["paper_id"], r["dimension"], r["decision"]) for r in decisions])
        return
    by_key = {(r["paper_id"], r["dimension"]): r for r in decisions}
    final = []
    for r in frozen:
        d = by_key.get((r["paper_id"], r["dimension"]))
        if d is None:
            final.append(r)
            continue
        kind = d["decision"].strip().lower()
        if kind == "exclude":
            continue
        row = dict(r)
        if kind == "relabel":
            row["gold_risk"] = d["new_label"].strip().lower()
        row["source"] = f"readj:{kind}"
        final.append(row)
    FINAL_GOLD.parent.mkdir(parents=True, exist_ok=True)
    with FINAL_GOLD.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(frozen[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(final)
    LOCK.write_text(json.dumps({
        "locked_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "cells": len(final),
        "decisions": decisions,
        "sha256": {"pilot_frozen/gold_labels.csv": sha(FROZEN_GOLD), "readjudication.csv": sha(READJ),
                   "gold_final/gold_labels.csv": sha(FINAL_GOLD)},
        "note": "Decided by the annotators before the numbers were regenerated; not adjusted afterwards.",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"locked {len(final)} cells ->", FINAL_GOLD.relative_to(ANN.parents[1]))


if __name__ == "__main__":
    main()
