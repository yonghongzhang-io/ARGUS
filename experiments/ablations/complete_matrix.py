"""Complete the 2-benchmark x 3-arm ablation matrix (the missing cells).

Existing frozen cells: single-pass on the 11 clear flaws (0.455, historical);
two-stage on both benchmarks; per-dimension-no-retrieval on the 33 variants.
This script fills the rest with gpt-4o:

  A. single-pass on the 33 variants   (1 call/paper,  34 calls)
  B. per-dim no-retrieval on 11 flaws (11 calls/paper, 132 calls)
  C. single-pass replicated on 11 flaws (12 calls) -- checks the historical
     0.455 (the original runner script did not survive in the repo, so this is
     a fresh implementation of the paper's description: full paper + all
     eleven dimensions in one call, same model/temperature/risk schema).

Run: PYTHONPATH=src python3 experiments/ablations/complete_matrix.py \
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
sys.path.insert(0, str(ROOT / "experiments" / "ablations"))

from argus.agent.llm_assessor import create_structured, make_client  # noqa: E402
from argus.config import load_flaw_variants, load_flaws  # noqa: E402
from argus.evaluation.injection import inject_flaw  # noqa: E402
from argus.evaluation.metrics import evaluate_pair, summarize_results  # noqa: E402
from argus.evaluation.variants import inject_variant  # noqa: E402
from argus.pipeline.decomposition import decompose  # noqa: E402
from argus.pipeline.localization import localize  # noqa: E402
from perdim_noretrieval import audit_perdim, paper_as_items  # noqa: E402

PAPER = ROOT / "examples" / "papers" / "clean_supported.json"
OUT = Path(__file__).resolve().parent / "ablation_matrix.json"

_SP_SYSTEM = (
    "You audit the causal-identification credibility of a difference-in-differences "
    "(DID) study. You do NOT judge whether the estimated effect is true. For EACH of "
    "the eleven identification dimensions listed, judge whether the evidence the paper "
    "reports is ADEQUATE to support that assumption. Evidence presence is not evidence "
    "adequacy. Return one judgement per dimension."
)


def _sp_schema(dim_ids: list[str]) -> dict:
    return {
        "type": "object", "additionalProperties": False,
        "properties": {"judgements": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "dimension": {"type": "string", "enum": dim_ids},
                "risk": {"type": "string", "enum": ["low", "medium", "high"]},
                "evidence_status": {"type": "string",
                                    "enum": ["sufficient", "partial", "missing", "flawed"]},
                "rationale": {"type": "string"},
            },
            "required": ["dimension", "risk", "evidence_status", "rationale"],
        }}},
        "required": ["judgements"],
    }


def audit_singlepass(paper: dict, client) -> dict:
    """Whole paper + all eleven dimensions in ONE model call."""
    skeleton = decompose(paper)
    dims = skeleton["dimensions"]
    dim_block = "\n".join(
        f"- {d['id']}: {d['assumption']} (expect: {', '.join(d['expected_evidence'])})"
        for d in dims.values()
    )
    items = paper_as_items(paper)
    paper_block = "\n\n".join(f"[{it['source']}]\n{it['text']}" for it in items)
    user = (f"Identification dimensions to judge:\n{dim_block}\n\n"
            f"THE PAPER:\n{paper_block}\n\n"
            f"Judge the adequacy of the reported evidence for EVERY dimension.")
    resp = create_structured(
        client, model="gpt-4o", temperature=0,
        messages=[{"role": "system", "content": _SP_SYSTEM},
                  {"role": "user", "content": user}],
        response_format={"type": "json_schema", "json_schema": {
            "name": "singlepass_judgements", "strict": True,
            "schema": _sp_schema(list(dims))}},
    )
    parsed = json.loads(resp.choices[0].message.content or "{}")
    judgements = {dim_id: None for dim_id in dims}
    for j in parsed.get("judgements", []):
        if j.get("dimension") in judgements:
            judgements[j["dimension"]] = {
                "risk": j.get("risk", "high"),
                "evidence_status": j.get("evidence_status", "missing"),
                "rationale": j.get("rationale", ""),
                "cited_evidence": [], "retrieval_quality": "none",
            }
    return localize({"judgements": judgements})


def run_bench(name, injectors, audit_fn, client):
    """injectors: list of (label, flaw_type_or_None, make_injected_paper)."""
    paper = json.loads(PAPER.read_text(encoding="utf-8"))
    t0 = time.time()
    clean = audit_fn(paper, client)
    pairs = []
    for label, ftype, target, make in injectors:
        inj_map = audit_fn(make(paper), client)
        score = evaluate_pair(clean, inj_map, target, threshold="medium")
        pairs.append({"id": label, "flaw_type": ftype, "target": target, "score": score})
        print(f"  [{name}] {label}: detected={score['detected']}", flush=True)
    summary = summarize_results([p["score"] for p in pairs])
    print(f"[{name}] det={summary['detection_rate']:.3f} fa={summary['false_alarm_rate']:.3f} "
          f"loc={summary['localization_acc']:.3f} ({time.time()-t0:.0f}s)", flush=True)
    return {"summary": summary, "pairs": pairs}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--i-understand-this-costs-money", action="store_true")
    args = ap.parse_args()
    if not args.i_understand_this_costs_money:
        print("Paid gpt-4o run (~180 calls); add --i-understand-this-costs-money",
              file=sys.stderr)
        return 2

    client = make_client()
    variants = load_flaw_variants()
    flaws = load_flaws()

    var_inj = [(vid, v["flaw_type"], v["target_dimension"],
                (lambda p, v=v: inject_variant(p, v)))
               for vid, v in sorted(variants.items())]
    flaw_inj = [(fid, None, flaws[fid]["target_dimension"],
                 (lambda p, fid=fid: inject_flaw(p, fid)))
                for fid in sorted(flaws)]

    out = {
        "singlepass_33variants": run_bench("singlepass/33var", var_inj, audit_singlepass, client),
        "perdim_11flaws": run_bench("perdim/11flaw", flaw_inj, audit_perdim, client),
        "singlepass_11flaws_replication": run_bench("singlepass/11flaw", flaw_inj,
                                                    audit_singlepass, client),
        "note": ("single-pass reimplemented from the paper's description (original "
                 "runner not in repo); 11-flaw replication checks the historical 0.455."),
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
