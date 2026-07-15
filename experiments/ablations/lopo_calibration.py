"""P0-2: leave-one-paper-out stability of the calibration rule.

Rich per-cell fields (risk, retrieval_quality, evidence_status) for the 5 gold
papers are reconstructed from the June-era assess_llm traces by risk-pattern
fingerprinting (see gold_rich_cells.json; each 11-dim trace window is matched
to exactly one did_llm_risks.csv row pattern). Reconstruction validates against
the published error analysis up to denominator convention (23 over-severe highs
vs 24 total highs; 100% missing).

For each fold, hold out one paper and ask whether the same dominant rule
(over-severe highs concentrate on weak-retrieval / missing-evidence cells)
emerges from the remaining four papers' error analysis. Result: EMERGES in all
five folds (weak 72-81%, missing 100%). Zero API cost.
"""
import json, csv
rich = {tuple(k.split("|")): v for k, v in json.load(open("experiments/ablations/gold_rich_cells.json")).items()}
gold = {(r["paper_id"], r["dimension"]): r["gold_risk"] for r in csv.DictReader(open("data/annotations/gold_labels.csv"))}
RANK = {"low": 0, "medium": 1, "high": 2}
folds = {}
for held in sorted({p for p, _ in rich}):
    oh = [(k, v) for k, v in rich.items() if k[0] != held and v["risk"] == "high" and RANK[gold[k]] < 2]
    folds[held] = {"n": len(oh),
                   "weak_share": round(sum(v["retrieval_quality"] == "weak" for _, v in oh) / len(oh), 2),
                   "missing_share": round(sum(v["evidence_status"] == "missing" for _, v in oh) / len(oh), 2)}
out = {"rule": "over-severe high -> weak retrieval / missing evidence", "folds": folds,
       "stable": all(f["weak_share"] > 0.5 for f in folds.values())}
json.dump(out, open("experiments/ablations/lopo_calibration.json", "w"), indent=1)
print(json.dumps(out, indent=1))
