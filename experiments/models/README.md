# Cross-model runner

Provider-neutral configuration and runner for the cross-model panel reported in
the paper (Appendix B, Tables 5 and 6).

## Results

The unchanged pipeline was ported across four providers and run end-to-end on
the 33-variant flaw-injection benchmark. Frozen per-variant results are in
`crossmodel/` (`*.json` are full 33-variant runs; `*.smoke.json` are one-variant
connectivity checks).

| model | detection | false alarm | localization | commission | omission |
| --- | --- | --- | --- | --- | --- |
| gpt-4o (3-run mean) | 0.75 | 0.09 | 0.66 | 0.89 | 0.45 |
| Claude Opus 4.8 | 0.91 | 0.82 | 0.24 | 1.00 | 0.73 |
| Gemini 2.5 Flash | 0.79 | 0.18 | 0.36 | 0.91 | 0.55 |
| Llama 3.1 8B (local) | 0.94 | 0.27 | 0.27 | 0.95 | 0.91 |

These are **single runs** per model except gpt-4o, so they support the
qualitative claim only: detection of *commission* flaws ports across providers,
while the operating point does not. Opus 4.8 rates the unmodified fixture medium
or high on 18 of 22 commission pairs; Llama 8B abstains on only one of eleven
omissions. Cross-provider decoding defaults differ, and newer reasoning models
reject an explicit temperature, so runs are not decoding-matched. A practitioner
changing the model should re-tune the calibration layer.

## Files
- `config/models.yaml` — the model registry. Models are `enabled: false` by
  default so nothing runs by accident. Each entry declares provider, model name,
  and (via `defaults`) temperature, max tokens, max steps, retries, a
  `cost_ceiling_usd`, and caching.
- `src/argus/agent/model_config.py` — loader, `enabled_models()`, `resolve()`,
  `build_run_manifest()` (a no-API cost/plan projector), and the
  `ProviderAdapter` seam.
- `src/argus/agent/anthropic_compat.py` — Anthropic SDK behind an OpenAI-shaped
  facade. Gemini and local Llama run through `OPENAI_BASE_URL` against the
  OpenAI-compatible path.
- `plan_run.py` — dry-run only, no API. Prints the plan and a cost estimate.
- `run_crossmodel.py` — the runner that produced `crossmodel/`. Issues paid API
  calls for hosted providers.

## Dry run (no API, no cost)
```
PYTHONPATH=src python3 experiments/models/plan_run.py --all
```

## Reproducing a model's run (spends money for hosted providers)
Set `enabled: true` for that model in `config/models.yaml`, provide its
credentials in a gitignored `.env`, then run `run_crossmodel.py`. The local
Llama run took roughly 67 minutes on a laptop at zero API cost; a hosted gpt-4o
run is about US$8 and 20 minutes. Cost figures in the planner are estimates;
verify provider pricing before any real run.
