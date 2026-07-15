"""Oracle-RETRIEVAL arm on the 33 variants (P0-1).

The injector knows exactly what each variant changed, so we can hand the
assessor perfect retrieval and isolate the judgement layer:

  commission -> feed the injected (flawed) section text for the target
                dimension directly to the adequacy assessor;
  omission   -> the support was deleted; perfect retrieval finds nothing, so
                feed empty evidence, bypassing the gate (which would abstain).

Detection under oracle retrieval vs the full pipeline splits every miss into
"retrieval/gate failure" vs "judgement failure". Clean-side control: the same
oracle feed from the CLEAN fixture must stay below medium (false-alarm check).

Run (PAID, gpt-4o, ~66 calls):
    PYTHONPATH=src python3 experiments/ablations/oracle_retrieval.py \
        --i-understand-this-costs-money
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from argus.agent.llm_assessor import assess_chain_llm, make_client  # noqa: E402
from argus.config import load_flaw_variants  # noqa: E402
from argus.evaluation.variants import inject_variant  # noqa: E402
from argus.pipeline.decomposition import decompose  # noqa: E402

PAPER = ROOT / "examples" / "papers" / "clean_supported.json"
OUT = Path(__file__).resolve().parent / "oracle_retrieval.json"
RANK = {"low": 0, "medium": 1, "high": 2}


def target_items(paper: dict, variant: dict) -> list[dict]:
    """Perfect retrieval: the target dimension's section(s) from this paper."""
    inj = variant["injection"]
    names = list(inj.get("sections") or [])  # dict (replace) or list (remove)
    items = []
    sections = paper.get("sections") or {}
    for name in names:
        if name in sections:
            items.append({"source": f"section: {name}", "text": str(sections[name])})
    for fid, cap in (inj.get("figure_captions") or {}).items():
        for fig in paper.get("figures") or []:
            if fig.get("id") == fid:
                items.append({"source": f"figure {fid}", "text": str(fig.get("caption", ""))})
    return items  # empty for omission variants on the injected paper


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--i-understand-this-costs-money", action="store_true")
    args = ap.parse_args()
    if not args.i_understand_this_costs_money:
        print("Paid gpt-4o run (~66 calls); add the flag", file=sys.stderr)
        return 2

    paper = json.loads(PAPER.read_text(encoding="utf-8"))
    dims = decompose(paper)["dimensions"]
    variants = load_flaw_variants()
    client = make_client()
    t0 = time.time()

    rows = []
    for vid in sorted(variants):
        v = variants[vid]
        dim = dims[v["target_dimension"]]
        injected = inject_variant(paper, v)
        inj_items = target_items(injected, v)
        clean_items = target_items(paper, v)
        r_inj = assess_chain_llm(dim, {"items": inj_items}, client=client)["judgement"]
        r_cln = assess_chain_llm(dim, {"items": clean_items}, client=client)["judgement"]
        detected = RANK.get(r_inj["risk"], -1) >= 1
        false_alarm = RANK.get(r_cln["risk"], -1) >= 1
        rows.append({"variant_id": vid, "flaw_type": v["flaw_type"],
                     "target": v["target_dimension"], "oracle_injected": r_inj["risk"],
                     "oracle_clean": r_cln["risk"], "detected": detected,
                     "false_alarm": false_alarm})
        print(f"  {vid}: inj={r_inj['risk']} clean={r_cln['risk']}", flush=True)

    def rate(ft, key):
        s = [r for r in rows if ft is None or r["flaw_type"] == ft]
        return round(sum(r[key] for r in s) / len(s), 3)

    out = {"arm": "oracle retrieval (target section fed directly; empty for omissions)",
           "model": "gpt-4o", "n": len(rows),
           "detection": rate(None, "detected"),
           "commission_detection": rate("commission", "detected"),
           "omission_detection": rate("omission", "detected"),
           "false_alarm": rate(None, "false_alarm"),
           "rows": rows}
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n[oracle-retrieval] det={out['detection']} comm={out['commission_detection']} "
          f"omit={out['omission_detection']} fa={out['false_alarm']} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
