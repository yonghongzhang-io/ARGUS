"""Run the multi-variant flaw-injection benchmark.

This drives ``argus.evaluation.variants.evaluate_variants`` over
``config/flaw_variants.yaml`` (several naturalistic flaw variants per
identification dimension) and reports detection / false-alarm / localization
overall and per dimension.

Two modes:

  --dry-run           (default)  Keyword assessor only. Fully DETERMINISTIC, NO
                                 API calls, no cost. Also statically checks every
                                 variant for leakage (non-circularity). Use this
                                 to validate the harness offline.

  --assessor llm                 Two-stage LLM assessor. Issues real model calls
                                 and therefore COSTS money and needs OPENAI_API_KEY
                                 (and honours ARGUS_LLM_MODEL). Guarded behind
                                 --i-understand-this-costs-money so it can never
                                 run by accident.

Real per-variant detection numbers for the LLM assessor are NOT produced by the
default path and are not committed; they require a separately authorized run.

Usage:
    PYTHONPATH=src python3 experiments/variants/run_variants.py --dry-run
    PYTHONPATH=src python3 experiments/variants/run_variants.py \
        --assessor llm --i-understand-this-costs-money
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from argus.config import load_flaw_variants  # noqa: E402
from argus.evaluation.variants import evaluate_variants, validate_variant  # noqa: E402

PAPER = ROOT / "examples" / "papers" / "clean_supported.json"
OUT = Path(__file__).resolve().parent / "variant_results.json"


def _load_clean() -> dict:
    return json.loads(PAPER.read_text(encoding="utf-8"))


def leak_report(paper: dict, variants: dict) -> dict[str, list[str]]:
    """Static, no-API non-circularity check over every variant."""
    return {vid: validate_variant(paper, v) for vid, v in variants.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="keyword assessor only; deterministic, no API (default if no --assessor)")
    ap.add_argument("--assessor", choices=["keyword", "llm"], default=None,
                    help="assessor to use; 'llm' issues paid model calls")
    ap.add_argument("--max-steps", type=int, default=1)
    ap.add_argument("--threshold", default="medium")
    ap.add_argument("--i-understand-this-costs-money", action="store_true",
                    help="required to run the LLM assessor")
    args = ap.parse_args()

    assessor = args.assessor or "keyword"
    if assessor == "llm" and not args.i_understand_this_costs_money:
        print("Refusing to run the LLM assessor without --i-understand-this-costs-money "
              "(it issues paid API calls). Use --dry-run for the free keyword pass.",
              file=sys.stderr)
        return 2

    paper = _load_clean()
    variants = load_flaw_variants()

    # 1) Static leak-freedom check (always, no API).
    leaks = leak_report(paper, variants)
    leaked = {vid: terms for vid, terms in leaks.items() if terms}
    print(f"variants: {len(variants)} | leak-free: {len(variants) - len(leaked)} | leaking: {len(leaked)}")
    if leaked:
        for vid, terms in leaked.items():
            print(f"  LEAK {vid}: {terms}")
        print("Refusing to evaluate: fix leaking variants first (they would make detection circular).",
              file=sys.stderr)
        return 1

    # 2) Evaluate (keyword = deterministic/no API; llm = gated above).
    if assessor == "llm":
        print(f"Running LLM assessor (model={__import__('os').environ.get('ARGUS_LLM_MODEL', 'gpt-4o')}). "
              "This issues paid API calls.")
    result = evaluate_variants(
        paper, max_steps=args.max_steps, threshold=args.threshold, assessor=assessor, variants=variants
    )

    s = result["summary"]
    print(f"\n[{assessor}] n={result['n_variants']}  "
          f"detection={s['detection_rate']:.3f}  false_alarm={s['false_alarm_rate']:.3f}  "
          f"localization={s['localization_acc']:.3f}")
    print("per-dimension (detection / false_alarm / localization / meets_expected):")
    for dim, d in result["by_dimension"].items():
        print(f"  {dim:28s} n={d['n']}  {d['detection_rate']:.2f} / {d['false_alarm_rate']:.2f} "
              f"/ {d['localization_acc']:.2f} / {d['meets_expected_rate']:.2f}")

    # Persist a compact, model-agnostic summary (drop the heavy audit objects).
    compact = {
        "assessor": assessor,
        "n_variants": result["n_variants"],
        "summary": result["summary"],
        "by_dimension": result["by_dimension"],
        "pairs": [
            {"variant_id": p["variant_id"], "target_dimension": p["ground_truth"]["target_dimension"],
             "flaw_type": p["ground_truth"].get("flaw_type"), "severity": p["ground_truth"]["severity"],
             "score": {k: p["score"][k] for k in
                       ("detected", "false_alarm", "localized", "clean_risk", "injected_risk", "meets_expected")}}
            for p in result["pairs"]
        ],
    }
    OUT.write_text(json.dumps(compact, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    if assessor == "keyword":
        print("NOTE: keyword is the deterministic baseline; commission variants are expected to be "
              "under-detected here. Real detection requires the LLM assessor under an authorized run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
