"""Audit of the oracle-evidence check: what the expert spans do and do not show.

No model access. Reads the completed span file (kept out of the repository because it
quotes the audited articles), the committed oracle output, and the frozen adjudicated
gold, and writes

  annotation/oracle/evidence_spans_audit.csv   one row per cell, NO article text:
      applicability flag, whether each span is non-empty, its location, its length
  experiments/ablations/oracle_evidence_audit.json
      counts of pipeline abstentions by whether the expert found a relevant passage,
      and agreement metrics under two conventions: the frozen 55-cell protocol, and a
      53-cell sensitivity analysis that drops the cells the oracle-stage annotator
      marked not applicable.

The two conventions exist because the annotations disagree. For paper_01 and paper_08
the oracle-stage annotator recorded that parallel trends does not apply (the study is not
a treated-control DID design), while the adjudicated gold, fixed earlier and flagged
ambiguous on both cells, rates them high and medium. Neither is overwritten here.

    python3 experiments/ablations/oracle_evidence_audit.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPANS = ROOT / "annotation" / "oracle" / "evidence_spans_completed.csv"
AUDIT_CSV = ROOT / "annotation" / "oracle" / "evidence_spans_audit.csv"
ORACLE = ROOT / "experiments" / "ablations" / "oracle_evidence.json"
GOLD = ROOT / "experiments" / "annotation" / "pilot_frozen" / "gold_labels.csv"
OUT = ROOT / "experiments" / "ablations" / "oracle_evidence_audit.json"
READJ = ROOT / "experiments" / "annotation" / "readjudication.csv"
RANK = {"low": 0, "medium": 1, "high": 2}


def metrics(keys: list, gold: dict, cells: dict) -> dict:
    answered = [k for k in keys if cells[k]["pipeline"] in RANK]
    highs = [k for k in keys if gold[k] == "high"]
    return {
        "n_cells": len(keys),
        "gold_low_medium_high": [sum(gold[k] == lv for k in keys) for lv in ("low", "medium", "high")],
        "pipeline": {
            "answered": len(answered), "unknown": len(keys) - len(answered),
            "coverage": round(len(answered) / len(keys), 3),
            "exact_of_answered": [sum(cells[k]["pipeline"] == gold[k] for k in answered), len(answered)],
            "over_severe_of_answered": [sum(RANK[cells[k]["pipeline"]] > RANK[gold[k]] for k in answered), len(answered)],
            "strict_exact": [sum(cells[k]["pipeline"] == gold[k] for k in answered), len(keys)],
            "high_recall": [sum(cells[k]["pipeline"] == "high" for k in highs), len(highs)]},
        "oracle_arm": {
            "exact": [sum(cells[k]["oracle_risk"] == gold[k] for k in keys), len(keys)],
            "over_severe": [sum(RANK[cells[k]["oracle_risk"]] > RANK[gold[k]] for k in keys), len(keys)]}}


def main() -> None:
    spans = list(csv.DictReader(SPANS.open(encoding="utf-8-sig")))
    gold = {(r["paper_id"], r["dimension"]): r["gold_risk"].strip().lower()
            for r in csv.DictReader(GOLD.open(encoding="utf-8"))}
    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    cells = {(c["paper_id"], c["dimension"]): c for c in oracle["cells"]}

    rows, not_applicable = [], []
    for r in spans:
        key = (r["paper_id"], r["dimension"])
        na = r["no_evidence_in_paper"].strip().upper() == "TRUE"
        if na:
            not_applicable.append(key)
        rows.append({"paper_id": key[0], "dimension": key[1],
                     "marked_not_applicable_or_no_evidence": "yes" if na else "no",
                     "relevant_passage_located": "no" if na else ("yes" if r["evidence_span_1"].strip() else "no"),
                     "span_1_location": "" if na else r["span_1_location"],
                     "span_2_present": "yes" if (r["evidence_span_2"].strip() and not na) else "no",
                     "span_2_location": "" if na else r["span_2_location"],
                     "chars_quoted": 0 if na else len(r["evidence_span_1"]) + len(r["evidence_span_2"]),
                     "adjudicated_gold": gold[key], "pipeline_risk": cells[key]["pipeline"]})
    with AUDIT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    unknowns = [k for k in cells if cells[k]["pipeline"] == "unknown"]
    located = {(r["paper_id"], r["dimension"]) for r in rows if r["relevant_passage_located"] == "yes"}
    counts = {"cells": len(rows), "cells_with_relevant_passage": len(located),
              "cells_marked_not_applicable": len(not_applicable),
              "pipeline_unknowns_total": len(unknowns),
              "pipeline_unknowns_with_relevant_passage": sum(k in located for k in unknowns),
              "pipeline_unknowns_not_applicable": sum(k in not_applicable for k in unknowns)}
    out = {"counts": counts,
           "not_applicable_cells": [{"paper_id": k[0], "dimension": k[1], "adjudicated_gold": gold[k],
                                     "pipeline": cells[k]["pipeline"], "oracle_arm": cells[k]["oracle_risk"]}
                                    for k in not_applicable],
           "frozen_55_cell_protocol": metrics(list(gold), gold, cells),
           "sensitivity_53_cells": metrics([k for k in gold if k not in not_applicable], gold, cells)}
    # Optional re-adjudication of disputed cells (experiments/annotation/readjudication.csv).
    # The frozen gold is never edited; decisions are applied on a copy and reported separately.
    decisions = [r for r in csv.DictReader(READJ.open(encoding="utf-8")) if r["decision"].strip()] if READJ.exists() else []
    if decisions:
        regold, dropped = dict(gold), []
        for r in decisions:
            key, d = (r["paper_id"], r["dimension"]), r["decision"].strip().lower()
            if d == "relabel":
                regold[key] = r["new_label"].strip().lower()
            elif d == "exclude":
                dropped.append(key)
            elif d != "keep":
                raise SystemExit(f"unknown decision {d!r} for {key}")
        out["after_readjudication"] = {"decisions": decisions,
                                       "metrics": metrics([k for k in regold if k not in dropped], regold, cells)}
    else:
        out["after_readjudication"] = "pending: no decision recorded in experiments/annotation/readjudication.csv"
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    # The committed oracle output carried a field that only counted pipeline abstentions while
    # its name claimed the expert had found evidence for each. Recount it from the spans.
    oracle.pop("pipeline_unknowns_where_expert_found_evidence", None)
    oracle.update({k: counts[k] for k in ("pipeline_unknowns_total", "pipeline_unknowns_with_relevant_passage",
                                          "pipeline_unknowns_not_applicable")})
    ordered = {k: v for k, v in oracle.items() if k != "cells"}
    ordered["cells"] = oracle["cells"]
    ORACLE.write_text(json.dumps(ordered, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "not_applicable_cells"}, indent=1))


if __name__ == "__main__":
    main()
