"""Run the 33-variant benchmark on one model from config/models.yaml.

This is the cross-model robustness driver. It resolves a model id from the
registry, sets the provider environment for that run (ARGUS_PROVIDER /
OPENAI_BASE_URL / OPENAI_API_KEY / ARGUS_LLM_MODEL), verifies every variant is
leak-free, audits the clean fixture once plus all 33 injected variants, and
writes a compact result to experiments/models/crossmodel/<id>.json.

Paid providers are gated behind --i-understand-this-costs-money; local models
(price_per_1k_usd == 0, e.g. Ollama) run without the flag. A --smoke mode runs a
single variant (~44 calls -> 2 audits) to verify connectivity/compatibility
before committing to a full run.

Usage:
    PYTHONPATH=src python3 experiments/models/run_crossmodel.py --model llama_open --smoke
    PYTHONPATH=src python3 experiments/models/run_crossmodel.py --model gemini_flash \
        --i-understand-this-costs-money
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from argus.agent.llm_assessor import _load_env_file  # noqa: E402
from argus.agent.model_config import resolve  # noqa: E402
from argus.config import load_flaw_variants  # noqa: E402
from argus.evaluation.variants import evaluate_variants, validate_variant  # noqa: E402

PAPER = ROOT / "examples" / "papers" / "clean_supported.json"
OUT_DIR = Path(__file__).resolve().parent / "crossmodel"
SMOKE_VARIANT = "parallel_trends_commission_01"  # keyword-missed; a real test of adequacy reasoning


def set_provider_env(cfg: dict) -> None:
    """Point the assessor at this model for the current process."""
    _load_env_file()
    provider = cfg["provider"]
    os.environ["ARGUS_LLM_MODEL"] = cfg["model"]
    if provider == "anthropic":
        os.environ["ARGUS_PROVIDER"] = "anthropic"
        os.environ.pop("OPENAI_BASE_URL", None)
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("ANTHROPIC_API_KEY missing (add it to .env)")
        return
    os.environ["ARGUS_PROVIDER"] = "openai"
    if provider == "openai-compatible":
        os.environ["OPENAI_BASE_URL"] = cfg["base_url"]
        key_env = cfg.get("api_key_env") or ""
        key = os.environ.get(key_env, "") if key_env else ""
        if key_env and not key:
            raise SystemExit(f"{key_env} missing (add it to .env)")
        os.environ["OPENAI_API_KEY"] = key or "local-no-key"
    else:  # plain openai
        os.environ.pop("OPENAI_BASE_URL", None)
        if not os.environ.get("OPENAI_API_KEY"):
            raise SystemExit("OPENAI_API_KEY missing (add it to .env)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, help="model id from config/models.yaml")
    ap.add_argument("--smoke", action="store_true",
                    help="run a single variant (~2 audits) to verify connectivity")
    ap.add_argument("--i-understand-this-costs-money", action="store_true")
    args = ap.parse_args()

    _load_env_file()
    cfg = resolve(args.model)
    paid = float(cfg.get("price_per_1k_usd", 0)) > 0
    if paid and not args.i_understand_this_costs_money:
        print(f"{args.model} is a paid provider; re-run with --i-understand-this-costs-money "
              "(or use --smoke plus the flag for a ~44-call connectivity test).", file=sys.stderr)
        return 2

    variants = load_flaw_variants()
    paper = json.loads(PAPER.read_text(encoding="utf-8"))

    leaked = {vid: t for vid, t in ((v, validate_variant(paper, c)) for v, c in variants.items()) if t}
    if leaked:
        print(f"refusing to run: leaking variants {sorted(leaked)}", file=sys.stderr)
        return 1

    set_provider_env(cfg)
    ids = [SMOKE_VARIANT] if args.smoke else None
    n = 1 if args.smoke else len(variants)
    print(f"[{args.model}] provider={cfg['provider']} model={cfg['model']} "
          f"variants={n} ({'SMOKE' if args.smoke else 'FULL'})", flush=True)

    t0 = time.time()
    res = evaluate_variants(paper, variant_ids=ids, assessor="llm", max_steps=1, variants=variants)
    s = res["summary"]
    print(f"done in {time.time()-t0:.0f}s: detection={s['detection_rate']:.3f} "
          f"false_alarm={s['false_alarm_rate']:.3f} localization={s['localization_acc']:.3f}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{args.model}{'.smoke' if args.smoke else ''}.json"
    compact = {
        "model_id": args.model, "provider": cfg["provider"], "model": cfg["model"],
        "mode": "smoke" if args.smoke else "full", "n_variants": res["n_variants"],
        "summary": res["summary"], "by_dimension": res["by_dimension"],
        "pairs": [{"variant_id": p["variant_id"],
                   "target_dimension": p["ground_truth"]["target_dimension"],
                   "flaw_type": p["ground_truth"].get("flaw_type"),
                   "score": {k: p["score"][k] for k in
                             ("detected", "false_alarm", "localized",
                              "clean_risk", "injected_risk", "meets_expected")}}
                  for p in res["pairs"]],
    }
    out.write_text(json.dumps(compact, indent=1), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
