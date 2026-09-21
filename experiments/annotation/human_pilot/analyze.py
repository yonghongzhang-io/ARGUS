"""Human pilot: the protocol's analyses that no other script covers (no model access).

    python3 experiments/annotation/human_pilot/analyze.py

Needs the locked gold (gold_final/) and the private cell-level labels. Writes aggregate numbers
only to results.json:

  system_vs_gold      ARGUS corpus run against the human gold (abstentions, severity, kappa)
  abstentions         on cells ARGUS abstained on, did the annotators find reported evidence?
  earlier_labels      the LLM-assisted labels of the submitted version against the human gold,
                      and the same system comparison under those labels, side by side

Agreement between the annotators is in agreement.json (pilot.py ingest); calibration and
intervals come from ablations/calibration_recheck.py and ablations/uncertainty.py.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "annotation"))
from compare_argus_gold import cohen_kappa, weighted_kappa  # noqa: E402
from goldpath import FINAL_GOLD, FROZEN_GOLD  # noqa: E402

PRIVATE = ROOT / "data" / "annotations" / "human_pilot"
RUN = ROOT / "experiments" / "real_papers" / "corpus_results" / "did_llm_risks.csv"
RANK = {"low": 0, "medium": 1, "high": 2}
Key = tuple[str, str]


def table(path: Path, field: str) -> dict[Key, str]:
    with path.open(encoding="utf-8") as fh:
        return {(r["paper_id"], r["dimension"]): r[field].strip().lower() for r in csv.DictReader(fh)}


def versus(system: dict[Key, str], gold: dict[Key, str]) -> dict:
    answered = [(system[k], gold[k]) for k in gold if system[k] in RANK]
    strict = [(system[k], gold[k]) for k in gold]
    highs = [k for k in gold if system[k] == "high"]
    gold_high = [k for k in gold if gold[k] == "high"]
    return {"cells": len(gold), "gold_low_medium_high": [sum(v == lv for v in gold.values()) for lv in RANK],
            "abstained": len(gold) - len(answered), "answered": len(answered),
            "exact": sum(a == b for a, b in answered), "more_severe": sum(RANK[a] > RANK[b] for a, b in answered),
            "less_severe": sum(RANK[a] < RANK[b] for a, b in answered),
            "cohen_kappa": round(cohen_kappa(answered), 3), "weighted_kappa": round(weighted_kappa(answered), 3),
            "strict_exact": sum(a == b for a, b in strict), "strict_cohen_kappa": round(cohen_kappa(strict), 3),
            "high_precision": [sum(gold[k] == "high" for k in highs), len(highs)],
            "high_recall": [sum(system[k] == "high" for k in gold_high), len(gold_high)]}


def main() -> None:
    if not FINAL_GOLD.exists():
        raise SystemExit("gold_final/ does not exist yet: run pilot.py ingest and pilot.py gold first.")
    gold = table(FINAL_GOLD, "gold_risk")
    earlier = table(FROZEN_GOLD, "gold_risk")
    papers = {k[0] for k in earlier}
    system = {k: v for k, v in table(RUN, "risk").items() if k[0] in papers}
    labels = {w: {(r["paper_id"], r["dimension"]): r for r in csv.DictReader((PRIVATE / f"labels_{w}.csv").open(encoding="utf-8"))}
              for w in "AB"}

    def found(w: str, k: Key) -> bool:
        r = labels[w][k]
        return r["reported"].strip().lower() == "yes" and r["evidence_location"].strip().lower() not in {"", "none found", "none", "n/a"}

    abst = [k for k in system if system[k] == "unknown"]
    rated = [k for k in abst if k in gold]
    both_found = sum(found("A", k) and found("B", k) for k in rated)
    either = sum(found("A", k) or found("B", k) for k in rated)
    shared = [k for k in gold if k in earlier]
    moved = Counter((earlier[k], gold[k]) for k in shared if earlier[k] != gold[k])
    out = {
        "system_vs_gold": versus(system, gold),
        "abstentions": {"system_abstained": len(abst), "of_which_not_applicable_in_gold": len(abst) - len(rated),
                        "rated_cells": len(rated), "evidence_reported_by_both_annotators": both_found,
                        "by_at_least_one": either, "by_neither": len(rated) - either},
        "earlier_labels": {"cells_compared": len(shared), "same_label": sum(earlier[k] == gold[k] for k in shared),
                           "earlier_more_severe": sum(RANK[earlier[k]] > RANK[gold[k]] for k in shared),
                           "earlier_less_severe": sum(RANK[earlier[k]] < RANK[gold[k]] for k in shared),
                           "changes_earlier_to_human": {f"{a}->{b}": n for (a, b), n in sorted(moved.items())},
                           "cohen_kappa_earlier_vs_human": round(cohen_kappa([(earlier[k], gold[k]) for k in shared]), 3),
                           "system_vs_earlier_labels": versus(system, earlier)},
    }
    (HERE / "results.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
