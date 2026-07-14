# Multi-model runner scaffolding

Provider-neutral configuration for cross-model robustness runs.

**This is ready-to-run infrastructure, not experimental results.** Multi-model
execution scaffolding is included, but cross-model numerical results require
separately authorized paid or local model runs and are **not reported** in the
paper. Every number currently reported uses the single default `gpt-4o` path.
"Code supports multiple models" must never be read as "cross-model robustness has
been verified."

## Files
- `config/models.yaml` — the model registry. **All models are `enabled: false`
  by default**, so nothing runs by accident. Each entry declares provider, model
  name, and (via `defaults`) temperature, max tokens, max steps, retries, a
  `cost_ceiling_usd`, and caching.
- `src/argus/agent/model_config.py` — loader, `enabled_models()`, `resolve()`,
  and `build_run_manifest()` (a no-API cost/plan projector). Also defines the
  `ProviderAdapter` seam.
- `experiments/models/plan_run.py` — **dry-run only**, no API. Prints the plan and
  an order-of-magnitude cost estimate for the enabled (or all) models.

## Dry run (no API, no cost)
```
PYTHONPATH=src python3 experiments/models/plan_run.py --all
```

## Actually running a second model (only when authorized)
Today only the **openai** provider has an implemented backend (the existing
`argus.agent.llm_assessor.make_client` path); other providers are marked
`runnable: false`. To add one:
1. Implement a `ProviderAdapter` in `src/argus/agent/model_config.py`.
2. Branch it in `src/argus/pipeline/assessment.py:assess`, returning the same
   judgement dict shape as `llm_assessor` (`{risk, evidence_status, rationale,
   cited_evidence}`).
3. Set `enabled: true` for that model and provide its credentials.
4. Run the LLM assessor under an explicit, authorized configuration.

Cost figures in the planner are estimates for planning only; verify provider
pricing before any real run.
