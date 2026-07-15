"""Run the LLM variant benchmark N more times for a mean+-range (PAID, no-commit).
Saves each run to experiments/variants/llm_runs/run_{i}.json. Non-deterministic;
used to quantify run-to-run variance before reporting a paper number.
"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, "src")
from argus.evaluation.variants import evaluate_variants
from argus.config import load_flaw_variants

ROOT = Path(".")
paper = json.loads((ROOT / "examples/papers/clean_supported.json").read_text())
outdir = ROOT / "experiments/variants/llm_runs"; outdir.mkdir(parents=True, exist_ok=True)
variants = load_flaw_variants()
for i in (2, 3):
    t = time.time()
    res = evaluate_variants(paper, assessor="llm", max_steps=1, variants=variants)
    compact = {"assessor": "llm", "model": "gpt-4o", "run": i, "n_variants": res["n_variants"],
               "summary": res["summary"], "by_dimension": res["by_dimension"],
               "pairs": [{"variant_id": p["variant_id"], "target_dimension": p["ground_truth"]["target_dimension"],
                          "flaw_type": p["ground_truth"].get("flaw_type"),
                          "score": {k: p["score"][k] for k in ("detected", "false_alarm", "localized",
                                                               "clean_risk", "injected_risk", "meets_expected")}}
                         for p in res["pairs"]]}
    (outdir / f"run_{i}.json").write_text(json.dumps(compact, indent=1))
    print(f"run {i} done in {time.time()-t:.0f}s: det={res['summary']['detection_rate']:.3f} "
          f"fa={res['summary']['false_alarm_rate']:.3f} loc={res['summary']['localization_acc']:.3f}", flush=True)
print("ALL DONE", flush=True)
