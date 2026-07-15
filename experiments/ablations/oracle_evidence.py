"""Oracle-evidence experiment: expert-provided evidence vs ARGUS's own retrieval.

For each of the 55 pilot cells, feed the EXPERT-annotated evidence spans
(annotation/oracle/evidence_spans_completed.csv, gitignored like the gold)
directly to the adequacy assessor, skipping retrieval and the relevance gate.
Compare three arms against the adjudicated human gold:

  pipeline : ARGUS full pipeline risks (frozen did_llm_risks.csv)
  oracle   : same assessor, expert evidence  [THIS RUN, ~55 gpt-4o calls]
  gold     : adjudicated expert labels

If oracle >> pipeline agreement, grounding is the dominant bottleneck; if
oracle stays over-severe, the judgement/rubric itself is also biased.

Run: PYTHONPATH=src python3 experiments/ablations/oracle_evidence.py \
        --i-understand-this-costs-money
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from argus.agent.llm_assessor import assess_chain_llm, make_client  # noqa: E402
from argus.config import load_dimensions  # noqa: E402

SPANS = ROOT / "annotation" / "oracle" / "evidence_spans_completed.csv"
GOLD = ROOT / "data" / "annotations" / "gold_labels.csv"
PIPE = ROOT / "experiments" / "real_papers" / "corpus_results" / "did_llm_risks.csv"
OUT = Path(__file__).resolve().parent / "oracle_evidence.json"

RANK = {"low": 0, "medium": 1, "high": 2}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--i-understand-this-costs-money", action="store_true")
    args = ap.parse_args()
    if not args.i_understand_this_costs_money:
        print("Paid gpt-4o run (~55 calls); add --i-understand-this-costs-money",
              file=sys.stderr)
        return 2

    dims = load_dimensions()
    spans = list(csv.DictReader(open(SPANS, encoding="utf-8-sig")))
    gold = {(r["paper_id"], r["dimension"]): r["gold_risk"]
            for r in csv.DictReader(open(GOLD, encoding="utf-8"))}
    pipe = {(r["paper_id"], r["dimension"]): r["risk"]
            for r in csv.DictReader(open(PIPE, encoding="utf-8"))}

    client = make_client()
    t0 = time.time()
    cells = []
    for r in spans:
        key = (r["paper_id"], r["dimension"])
        d = dims[r["dimension"]]
        dim_meta = {"id": d["id"], "name": d["name"], "assumption": d["assumption"],
                    "implication": d["implication"], "expected_evidence": d["evidence"]}
        items = []
        if r["evidence_span_1"].strip():
            items.append({"source": r["span_1_location"] or "expert-provided",
                          "text": r["evidence_span_1"]})
        if r["evidence_span_2"].strip():
            items.append({"source": r["span_2_location"] or "expert-provided",
                          "text": r["evidence_span_2"]})
        res = assess_chain_llm(dim_meta, {"items": items}, client=client)
        j = res["judgement"]
        cells.append({"paper_id": key[0], "dimension": key[1],
                      "oracle_risk": j["risk"], "evidence_status": j["evidence_status"],
                      "gold": gold.get(key), "pipeline": pipe.get(key)})
        print(f"  {key[0]}/{key[1]}: oracle={j['risk']} gold={gold.get(key)} "
              f"pipeline={pipe.get(key)}", flush=True)

    def agree(arm):
        ans = [c for c in cells if c[arm] not in (None, "unknown")]
        ex = sum(c[arm] == c["gold"] for c in ans)
        over = sum(RANK.get(c[arm], -1) > RANK.get(c["gold"], -1) for c in ans)
        under = sum(0 <= RANK.get(c[arm], -1) < RANK.get(c["gold"], -1) for c in ans)
        return {"answered": len(ans), "exact": ex, "exact_rate": round(ex/len(ans), 3),
                "over": over, "under": under}

    summary = {"model": "gpt-4o", "n_cells": len(cells),
               "oracle_vs_gold": agree("oracle_risk"),
               "pipeline_vs_gold": agree("pipeline"),
               "pipeline_unknowns_where_expert_found_evidence":
                   sum(1 for c in cells if c["pipeline"] == "unknown"),
               "cells": cells}
    OUT.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    o, p = summary["oracle_vs_gold"], summary["pipeline_vs_gold"]
    print(f"\n[oracle]   answered={o['answered']} exact={o['exact_rate']} "
          f"over={o['over']} under={o['under']}")
    print(f"[pipeline] answered={p['answered']} exact={p['exact_rate']} "
          f"over={p['over']} under={p['under']}")
    print(f"wrote {OUT.relative_to(ROOT)} in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
