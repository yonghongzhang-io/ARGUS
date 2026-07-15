"""Ablation arm: per-dimension prompting WITHOUT retrieval.

Isolates task decomposition from evidence retrieval. Each dimension gets its own
adequacy call (like the two-stage system, one judgement per dimension), but the
model sees the FULL paper as evidence for every dimension: no deterministic
retrieval, no relevance gate, and therefore no grounded `unknown` state.

Together with the existing arms this completes the compute-graded ablation:
  full-paper single pass   (1 call,  no decomposition)          [frozen result]
  per-dimension, no retrieval (11 calls, decomposition only)    [THIS SCRIPT]
  two-stage ARGUS          (22 calls, + retrieval/gate/abstain) [frozen result]

Run (PAID, gpt-4o, ~374 calls over 1 clean + 33 injected audits):
    PYTHONPATH=src python3 experiments/ablations/perdim_noretrieval.py \
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
from argus.evaluation.metrics import evaluate_pair, summarize_results  # noqa: E402
from argus.evaluation.variants import inject_variant, validate_variant  # noqa: E402
from argus.pipeline.decomposition import decompose  # noqa: E402
from argus.pipeline.localization import localize  # noqa: E402

PAPER = ROOT / "examples" / "papers" / "clean_supported.json"
OUT = Path(__file__).resolve().parent / "perdim_noretrieval.json"


def paper_as_items(paper: dict) -> list[dict]:
    """The whole paper as one evidence pool (no retrieval, no gate)."""
    items = []
    for title, text in (paper.get("sections") or {}).items():
        items.append({"source": f"section: {title}", "text": str(text)})
    for fig in paper.get("figures") or []:
        items.append({"source": f"figure {fig.get('id')}", "text": str(fig.get("caption", ""))})
    for tab in paper.get("tables") or []:
        items.append({"source": f"table {tab.get('id')}", "text": str(tab.get("caption", ""))})
    return items


def audit_perdim(paper: dict, client) -> dict:
    """One adequacy call per dimension over the full paper; no unknown state."""
    skeleton = decompose(paper)
    items = paper_as_items(paper)
    judgements = {}
    for dim_id, dim in skeleton["dimensions"].items():
        result = assess_chain_llm(dim, {"items": items}, client=client)
        j = dict(result["judgement"])
        j["retrieval_quality"] = "none"  # no retrieval layer in this arm
        judgements[dim_id] = j
    return localize({"judgements": judgements})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--i-understand-this-costs-money", action="store_true")
    args = ap.parse_args()
    if not args.i_understand_this_costs_money:
        print("Paid gpt-4o run (~374 calls); re-run with --i-understand-this-costs-money",
              file=sys.stderr)
        return 2

    paper = json.loads(PAPER.read_text(encoding="utf-8"))
    variants = load_flaw_variants()
    leaked = [v for v, c in variants.items() if validate_variant(paper, c)]
    if leaked:
        print(f"refusing: leaking variants {leaked}", file=sys.stderr)
        return 1

    client = make_client()
    t0 = time.time()
    clean_map = audit_perdim(paper, client)
    print(f"clean audited in {time.time()-t0:.0f}s", flush=True)

    pairs = []
    for vid in sorted(variants):
        v = variants[vid]
        injected = inject_variant(paper, v)
        inj_map = audit_perdim(injected, client)
        score = evaluate_pair(clean_map, inj_map, v["target_dimension"], threshold="medium")
        pairs.append({"variant_id": vid, "target_dimension": v["target_dimension"],
                      "flaw_type": v["flaw_type"], "score": score})
        print(f"  {vid}: detected={score['detected']} fa={score['false_alarm']}", flush=True)

    summary = summarize_results([p["score"] for p in pairs])
    def ft(ftype, key):
        sel = [p for p in pairs if p["flaw_type"] == ftype]
        return round(sum(p["score"][key] for p in sel) / len(sel), 3)
    out = {"arm": "per-dimension, no retrieval", "model": "gpt-4o",
           "calls_per_paper": 11, "n_variants": len(pairs), "summary": summary,
           "commission_detection": ft("commission", "detected"),
           "omission_detection": ft("omission", "detected"),
           "commission_localization": ft("commission", "localized"),
           "omission_localization": ft("omission", "localized"),
           "pairs": pairs}
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n[perdim-noretrieval] detection={summary['detection_rate']:.3f} "
          f"fa={summary['false_alarm_rate']:.3f} loc={summary['localization_acc']:.3f} "
          f"| commission={out['commission_detection']} omission={out['omission_detection']}")
    print(f"wrote {OUT.relative_to(ROOT)} in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
