"""Leave-one-paper-out recurrence of the over-severity pattern on the pilot.

For each fold, hold out one paper and ask whether, among the remaining four papers'
over-severe `high` cells, the same pattern holds: weak retrieval and missing evidence.
This is a recurrence check. No rule is refitted on four papers and scored on the fifth.

Primary analysis: the rich re-run that Section 5.6 of the paper uses, read from the frozen,
committed pilot inputs (24 over-severe highs; 23 missing, 20 weak). Result: the pattern
recurs in all five folds (weak 79-86%, missing 94-100%).

Secondary, for the record: an earlier version of this script ran on
gold_rich_cells.json, a reconstruction of the corpus run's rich fields from June-era
traces (23 over-severe highs, all missing), which gave weak 72-81% / missing 100%.
Those figures are kept under "reconstructed_corpus_run"; the paper reports the primary ones.

    python3 experiments/ablations/lopo_calibration.py     # no model access
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / "experiments" / "annotation" / "pilot_frozen"
ABL = ROOT / "experiments" / "ablations"
RANK = {"low": 0, "medium": 1, "high": 2}


def folds(rich: dict, gold: dict) -> dict:
    out = {}
    for held in sorted({p for p, _ in rich}):
        oh = [v for k, v in rich.items() if k[0] != held and v["risk"] == "high" and RANK[gold[k]] < 2]
        out[held] = {"n": len(oh),
                     "weak_share": round(sum(v["retrieval_quality"] == "weak" for v in oh) / len(oh), 2),
                     "missing_share": round(sum(v["evidence_status"] == "missing" for v in oh) / len(oh), 2)}
    return out


gold = {(r["paper_id"], r["dimension"]): r["gold_risk"].strip().lower()
        for r in csv.DictReader((FROZEN / "gold_labels.csv").open(encoding="utf-8"))}
rerun = {(r["paper_id"], r["dimension"]): r
         for r in csv.DictReader((FROZEN / "argus_rich_gold5.csv").open(encoding="utf-8"))}
recon = {tuple(k.split("|")): v for k, v in json.load(open(ABL / "gold_rich_cells.json")).items()}

primary = folds(rerun, gold)
out = {"rule": "over-severe high -> weak retrieval / missing evidence",
       "source": "rich re-run (experiments/annotation/pilot_frozen/argus_rich_gold5.csv)",
       "folds": primary, "stable": all(f["weak_share"] > 0.5 for f in primary.values()),
       "reconstructed_corpus_run": {"source": "gold_rich_cells.json", "folds": folds(recon, gold)}}
(ABL / "lopo_calibration.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out["folds"], indent=1))
