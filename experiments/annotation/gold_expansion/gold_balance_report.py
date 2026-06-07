#!/usr/bin/env python3
"""Risk-class balance + coverage report for the gold-expansion set.

The pilot gold had only 2 high cells, which made high precision/recall unstable
and was the reviewer's headline objection. This report tracks the metric that
matters for an AAAI-grade evaluation: how many HIGH (and medium) cells the
expanded gold actually contains, broken down by dimension and design stratum, so
the annotation lead can over-sample high-risk papers if the count is still thin.

Modes:
  (default) post-adjudication balance of gold_labels_expansion.csv
            (optionally merged with the pilot gold via --with-pilot):
              python3 .../gold_balance_report.py [--with-pilot]
  --preview : BEFORE annotation, use ARGUS's own corpus predictions
              (experiments/real_papers/corpus_results/did_llm_risks.csv) as a
              sampling aid -- shows predicted high-rate for the sampled papers
              and how many still need auditing. (Aid only; never a gold label.)

This consumes the same gold schema as compare_argus_gold.py / calibrate_argus.py.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ANN = ROOT / "data" / "annotations"
GOLD_EXP = ANN / "gold_expansion" / "gold_labels_expansion.csv"
GOLD_PILOT = ANN / "gold_labels.csv"
ARGUS_PRED = ROOT / "experiments" / "real_papers" / "corpus_results" / "did_llm_risks.csv"
MANIFEST = HERE / "sample_manifest.csv"

HIGH_TARGET = 15  # rough floor for stable high precision/recall on a pilot-plus gold


def load_gold(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return list(csv.DictReader(open(path, encoding="utf-8")))


def report_balance(rows: list[dict]) -> None:
    dist = Counter(r["gold_risk"] for r in rows)
    n = len(rows)
    high = dist.get("high", 0)
    print(f"gold cells: {n}")
    print(f"  risk distribution: low={dist.get('low',0)}  medium={dist.get('medium',0)}  "
          f"high={high}  (other={n - sum(dist.get(k,0) for k in ('low','medium','high'))})")
    amb = sum(1 for r in rows if str(r.get("ambiguous", "")).strip() in ("1", "true", "yes"))
    print(f"  ambiguous cells: {amb}")
    flag = "OK" if high >= HIGH_TARGET else f"THIN (target >= {HIGH_TARGET})"
    print(f"  HIGH cells: {high}  [{flag}]   pilot had 2\n")

    # per-dimension
    by_dim = defaultdict(Counter)
    for r in rows:
        by_dim[r["dimension"]][r["gold_risk"]] += 1
    print(f"  {'dimension':28}{'low':>5}{'med':>5}{'high':>5}")
    print("  " + "-" * 43)
    for dim in sorted(by_dim):
        c = by_dim[dim]
        print(f"  {dim:28}{c.get('low',0):>5}{c.get('medium',0):>5}{c.get('high',0):>5}")


def report_by_stratum(rows: list[dict]) -> None:
    if not MANIFEST.exists():
        return
    strat = {r["paper_id"]: r.get("stratum", "?") for r in csv.DictReader(open(MANIFEST, encoding="utf-8"))}
    by_s = defaultdict(Counter)
    for r in rows:
        by_s[strat.get(r["paper_id"], "?")][r["gold_risk"]] += 1
    print(f"\n  {'stratum':24}{'low':>5}{'med':>5}{'high':>5}")
    print("  " + "-" * 39)
    for s in sorted(by_s):
        c = by_s[s]
        print(f"  {s:24}{c.get('low',0):>5}{c.get('medium',0):>5}{c.get('high',0):>5}")


def preview() -> None:
    if not MANIFEST.exists():
        raise SystemExit("no sample_manifest.csv; run sample_gold_corpus.py first")
    sampled = [r["paper_id"] for r in csv.DictReader(open(MANIFEST, encoding="utf-8"))]
    pred = defaultdict(Counter)
    if ARGUS_PRED.exists():
        for r in csv.DictReader(open(ARGUS_PRED, encoding="utf-8")):
            pred[r["paper_id"]][r["risk"]] += 1
    audited = [p for p in sampled if p in pred]
    not_audited = [p for p in sampled if p not in pred]
    print("PREVIEW (ARGUS predictions as a sampling aid -- NOT gold labels)\n")
    print(f"  sampled papers: {len(sampled)}  | already audited by ARGUS: {len(audited)}  "
          f"| need auditing: {len(not_audited)}")
    if audited:
        print(f"\n  {'paper':12}{'high':>5}{'med':>5}{'low':>5}{'unk':>5}")
        print("  " + "-" * 32)
        for p in audited:
            c = pred[p]
            print(f"  {p:12}{c.get('high',0):>5}{c.get('medium',0):>5}"
                  f"{c.get('low',0):>5}{c.get('unknown',0):>5}")
        tot_high = sum(pred[p].get("high", 0) for p in audited)
        print(f"\n  predicted-high cells among audited sample: {tot_high} "
              f"(ARGUS is over-severe, so true high is lower)")
    if not_audited:
        print(f"\n  {len(not_audited)} sampled papers are NOT yet audited by ARGUS; run:")
        print("    PYTHONPATH=src python3 experiments/real_papers/run_corpus.py --llm ...")
        print("  so an ARGUS prediction exists for every gold paper (needed for vs-gold).")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--with-pilot", action="store_true",
                    help="merge the pilot gold_labels.csv into the balance")
    args = ap.parse_args()

    if args.preview:
        preview()
        return

    rows = load_gold(GOLD_EXP)
    if args.with_pilot:
        rows = rows + load_gold(GOLD_PILOT)
    if not rows:
        raise SystemExit(f"no gold yet at {GOLD_EXP}\n"
                         "run adjudicate_v2.py after annotation, or use --preview now.")
    report_balance(rows)
    report_by_stratum(rows)


if __name__ == "__main__":
    main()
