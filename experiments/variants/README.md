# Multi-variant flaw-injection harness

Extends the base 11-flaw benchmark (one flaw per dimension) to **several
naturalistic flaw variants per identification dimension**, so detection is
measured over many test points rather than one, directly addressing the
small-benchmark limitation.

## What it is
- `config/flaw_variants.yaml` — the variant catalog. Each variant declares a
  `target_dimension`, `flaw_type` (`commission` = replace a section with
  flawed-but-natural prose; `omission` = remove the supporting evidence),
  `severity`, an `injection` block, `expected` risk bounds, and
  `forbidden_leakage_terms`.
- `src/argus/evaluation/variants.py` — `inject_variant`, `validate_variant`
  (static non-circularity check), and `evaluate_variants` (clean audited once,
  then each variant scored; per-dimension breakdown).
- `experiments/variants/run_variants.py` — driver with a **deterministic no-API
  dry run** and a gated LLM mode.
- `tests/test_flaw_variants.py` — parametrized regression tests; the key one
  asserts every variant is leak-free.

## Non-circularity (enforced, no API)
A variant is rejected if, after injection, the paper text contains the keyword
detector's own sentinel phrases for the target dimension
(`argus.agent.loop._NEGATIVE_SIGNALS`) or the variant's own
`forbidden_leakage_terms`. Otherwise "detection" would just be the injector
planting the string the detector greps for. This is checked statically for every
variant in CI.

## Dry run (no API, no cost)
```
PYTHONPATH=src python3 experiments/variants/run_variants.py --dry-run
```
This validates leak-freedom and runs the deterministic keyword baseline.
**Commission variants are expected to be under-detected by the keyword baseline**
— that gap is the whole point, and closing it is the LLM assessor's job.

## Real detection numbers (frozen)
A three-run gpt-4o pass (temperature 0) is frozen in `llm_variant_summary.json`
(raw runs in `llm_runs/run_{1,2,3}.json`) and reported in the paper (Results,
"Robustness"). Results are near-deterministic (32/33 verdicts identical across
runs): detection 0.75 (0.73--0.76), **commission 0.89**, **omission 0.45**
(the misses abstain to `unknown` -- the evidence-grounding bottleneck), false
alarm 0.09 (concentrated in `inference`). Reproduce (issues **paid API calls**):
```
PYTHONPATH=src python3 experiments/variants/run_variants.py \
    --assessor llm --i-understand-this-costs-money
# or three runs -> llm_runs/: python3 experiments/variants/run_multi.py
```
