"""Recheck of the pilot calibration layer from frozen inputs (camera-ready audit).

Reads only committed files under experiments/annotation/pilot_frozen/; no model access.

1. Re-runs the recovered version-1 script (calibrate_argus_v1_pilot.py) under both
   weak-retrieval policies and checks its output cell for cell against the historical
   CSVs behind Table 14.
2. Reports agreement with the adjudicated gold for three rule sets: none (before),
   the dominant weak-retrieval rule alone, and all four version-1 rules.
3. Reports paired tests of the exact-agreement lift: an exact McNemar test over the
   answered cells, and a per-paper sign test (ties dropped). Cells are nested in five
   papers, so the cell-level test overstates the evidence; and every rule was written
   on this same pilot, so none of this is a held-out estimate.

    python3 experiments/ablations/calibration_recheck.py   # prints + writes calibration_recheck.json
"""
from __future__ import annotations

import csv
import importlib.util
import json
import random
from math import comb
from pathlib import Path

from uncertainty import ORDER, mcnemar_exact, weighted_kappa

ROOT = Path(__file__).resolve().parents[2]
ABL = ROOT / "experiments" / "ablations"
FROZEN = ROOT / "experiments" / "annotation" / "pilot_frozen"
V1 = ROOT / "experiments" / "annotation" / "calibrate_argus_v1_pilot.py"
import sys
sys.path.insert(0, str(ROOT / "experiments" / "annotation"))
from goldpath import gold_path  # noqa: E402  final gold once locked, else the frozen June gold
DOMINANT = ("weak_retrieval_high_to_medium", "weak_retrieval_high_to_unknown")
Key = tuple[str, str]


def rows(name: str) -> list[dict[str, str]]:
    return list(csv.DictReader((FROZEN / name).open(encoding="utf-8")))


def sign_test(wins: int, losses: int) -> float:
    n = wins + losses
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(min(wins, losses) + 1)) / 2 ** n)


def metrics(pred: dict[Key, str], gold: dict[Key, str]) -> dict:
    keys = [k for k in gold if pred[k] in ORDER]
    pairs = [(ORDER[pred[k]], ORDER[gold[k]]) for k in keys]
    highs = [k for k in keys if pred[k] == "high"]
    tp = sum(1 for k in highs if gold[k] == "high")
    exs, wks = [], []
    for _ in range(5000):
        pp = [(ORDER[pred[k]], ORDER[gold[k]]) for k in (random.choice(keys) for _ in keys)]
        exs.append(sum(1 for a, b in pp if a == b) / len(pp))
        wk = weighted_kappa(pp)
        if wk == wk:
            wks.append(wk)
    exs.sort()
    wks.sort()
    q = lambda v, f: round(v[int(len(v) * f)], 4)  # 4 d.p. so that two-decimal reporting rounds once
    exact = sum(1 for a, b in pairs if a == b)
    return {"answered": len(keys), "unknown": len(gold) - len(keys),
            "exact": [exact, len(keys)], "exact_ci95": [q(exs, .025), q(exs, .975)],
            "over_severe": sum(1 for a, b in pairs if a > b), "under_severe": sum(1 for a, b in pairs if a < b),
            "high_assigned": len(highs), "high_precision": [tp, len(highs)],
            "high_recall": [tp, sum(1 for g in gold.values() if g == "high")],
            "weighted_kappa": round(weighted_kappa(pairs), 3), "weighted_kappa_ci95": [q(wks, .025), q(wks, .975)]}


def paired(before: dict[Key, str], after: dict[Key, str], gold: dict[Key, str]) -> dict:
    # Compared on the cells answered before calibration; an after-calibration abstention
    # counts as not-exact, so the abstain policy is not flattered by its lost coverage.
    keys = [k for k in gold if before[k] in ORDER]
    fixed = sum(1 for k in keys if before[k] != gold[k] and after[k] == gold[k])
    broken = sum(1 for k in keys if before[k] == gold[k] and after[k] != gold[k])
    per_paper = {}
    for paper in sorted({k[0] for k in keys}):
        ks = [k for k in keys if k[0] == paper]
        per_paper[paper] = {"answered": len(ks), "exact_before": sum(before[k] == gold[k] for k in ks),
                            "exact_after": sum(after[k] == gold[k] for k in ks)}
    wins = sum(1 for v in per_paper.values() if v["exact_after"] > v["exact_before"])
    losses = sum(1 for v in per_paper.values() if v["exact_after"] < v["exact_before"])
    return {"cells_fixed": fixed, "cells_broken": broken, "mcnemar_exact_p": round(mcnemar_exact(fixed, broken), 4),
            "per_paper": per_paper, "papers_improved": wins, "papers_worse": losses,
            "papers_tied": len(per_paper) - wins - losses, "sign_test_p_ties_dropped": round(sign_test(wins, losses), 4)}


def main() -> None:
    spec = importlib.util.spec_from_file_location("calibrate_v1", V1)
    v1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v1)

    rich = rows("argus_rich_gold5.csv")
    gold = {(r["paper_id"], r["dimension"]): r["gold_risk"].strip().lower() for r in csv.DictReader(gold_path().open(encoding="utf-8"))}
    before = {(r["paper_id"], r["dimension"]): r["risk"].strip().lower() for r in rich}
    out: dict = {"inputs": (FROZEN / "MANIFEST.sha256").read_text().split("\n")[:-1], "policies": {}}

    preds: dict[str, dict] = {}
    for action in ("medium", "unknown"):
        applied = [v1.calibrated_risk(r, weak_high_action=action) for r in rich]
        hist = rows(f"argus_rich_gold5_calibrated_{action}.csv")
        same = sum(1 for r, (risk, rule), h in zip(rich, applied, hist)
                   if (r["paper_id"], r["dimension"], risk, rule) == (h["paper_id"], h["dimension"], h["risk"], h["calibration_rule"]))
        fired: dict[str, int] = {}
        for _, rule in applied:
            fired[rule] = fired.get(rule, 0) + 1
        preds[action] = {
            "four": {(r["paper_id"], r["dimension"]): risk for r, (risk, _) in zip(rich, applied)},
            "dominant": {(r["paper_id"], r["dimension"]): (risk if rule in DOMINANT else r["risk"].strip().lower())
                         for r, (risk, rule) in zip(rich, applied)}}
        out["policies"][action] = {"reproduces_historical_output": [same, len(hist)], "rules_fired": fired}

    # One seeded stream, consumed in the order uncertainty.py uses (before, four-rule medium,
    # four-rule unknown), so those three intervals equal uncertainty.json; rule-1 rows follow.
    random.seed(0)
    m_before = metrics(before, gold)
    m_four = {a: metrics(preds[a]["four"], gold) for a in ("medium", "unknown")}
    m_dom = {a: metrics(preds[a]["dominant"], gold) for a in ("medium", "unknown")}
    for action in ("medium", "unknown"):
        out["policies"][action].update({
            "before": m_before, "dominant_rule_only": m_dom[action], "four_rules": m_four[action],
            "paired_vs_before": {"dominant_rule_only": paired(before, preds[action]["dominant"], gold),
                                 "four_rules": paired(before, preds[action]["four"], gold)}})

    (ABL / "calibration_recheck.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for action, p in out["policies"].items():
        print(f"== weak-retrieval high -> {action}: reproduces historical output {p['reproduces_historical_output']}")
        for name in ("before", "dominant_rule_only", "four_rules"):
            m = p[name]
            print(f"  {name:19s} answered {m['answered']:2d}  exact {m['exact'][0]}/{m['exact'][1]}={m['exact'][0] / m['exact'][1]:.2f} {m['exact_ci95']}"
                  f"  over {m['over_severe']:2d}  high prec {m['high_precision']}  wt-k {m['weighted_kappa']} {m['weighted_kappa_ci95']}")
        for name, t in p["paired_vs_before"].items():
            print(f"  paired {name:19s} fixed/broken {t['cells_fixed']}/{t['cells_broken']} McNemar p={t['mcnemar_exact_p']}"
                  f"  papers +{t['papers_improved']}/={t['papers_tied']}/-{t['papers_worse']} sign p={t['sign_test_p_ties_dropped']}")


if __name__ == "__main__":
    main()
