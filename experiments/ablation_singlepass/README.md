# M4 — single-pass LLM ablation (isolate the architecture)

The keyword baseline only shows *LLM reasoning > keyword matching*. It does **not**
show *the bounded-agentic architecture > a vanilla single LLM call*. M4 supplies
that missing baseline: the **same model, rubric, and adequacy standard** as the
two-stage assessor, with the architecture removed — whole paper + all 11
dimensions in **one** call, no retrieval, no relevance gate, no `unknown`-by-
construction. The only variable is structure.

## True-parity guarantees (what makes this a clean ablation)

The single-pass assessor lives in `src/argus/agent/single_pass_assessor.py` and:

- **provider/model**: reuses `llm_assessor.make_client()` → OpenAI,
  `ARGUS_LLM_MODEL` (default `gpt-4o`), `temperature=0` — identical to the
  two-stage assessor. (The originally-shipped draft defaulted to an Anthropic
  backend while asking for `gpt-4o`; that mismatch is fixed.)
- **rubric**: `argus.config.load_dimensions()` — the *same* file the pipeline runs
  on, not a hand-copied parallel YAML. (The draft shipped a re-formatted dict
  copy; that drift risk is fixed.)
- **adequacy standard**: the same "presence is not adequacy" framing and risk
  semantics as `llm_assessor._SYSTEM_PROMPT`, extended to judge all dimensions in
  one pass.

It is exposed as a third pipeline assessor (`assessor="single_pass"` in
`argus.pipeline.assessment`), so it reuses the exact fixtures and scoring that
produced the Table-1 keyword (0.182) and two-stage (1.000) numbers.

## Arm 1 — synthetic flaws (the Table-1 fourth row)

Same fixture + protocol as the paper. Needs `OPENAI_API_KEY` (or a `.env`):

```bash
PYTHONPATH=src python3 experiments/phase1_pilot/compare_assessors.py
```
Prints keyword vs **single-pass** vs two-stage on identical fixtures:

| assessor | detection | false alarm | localization |
|----------|-----------|-------------|--------------|
| keyword baseline | 0.182 | 0.000 | 0.182 |
| single-pass LLM (gpt-4o) | _run_ | _run_ | _run_ |
| two-stage LLM (gpt-4o) | 1.000 | 0.000 | 0.909 |

Reading: if single-pass *also* ~1.000, the architecture adds nothing to
**detection** — reframe its value as grounding + traceability (honest, sharp).
That is the likely outcome on the easy `clean_supported` fixture; the decisive
evidence for the architecture is Arm 2.

## Arm 2 — real papers (the decisive comparison)

No retrieval/gate means single-pass cannot answer "retrieved nothing → unknown".
On real papers it should therefore **collapse `unknown` and inflate `high`**
relative to the two-stage assessor — and that gap *is* the architecture's
contribution.

```bash
# two-stage (already in the paper) and single-pass, same corpus + model:
PYTHONPATH=src python3 experiments/real_papers/run_corpus.py --assessor llm          --n 27
PYTHONPATH=src python3 experiments/real_papers/run_corpus.py --assessor single_pass  --n 27
# -> corpus_results/did_llm_risks.csv  and  did_single_pass_risks.csv
# put them side by side (extend make_realcorpus_figure.py) and compare the
# unknown-share and high-share per dimension.
```

## M1 — cross-paper variance (paper-level, not pooled)

The assessor-agnostic harness here aggregates per base paper, so 1.000 is reported
with paper-level mean ± SD instead of pooled over 11 flaws on one fixture.

```bash
# self-test (no key; validates detection/false-alarm/localization on canonical rubric)
PYTHONPATH=src python3 experiments/ablation_singlepass/flaw_injection_eval.py

# real run over a 3–5 base-paper manifest (see schema atop flaw_injection_eval.py)
PYTHONPATH=src python3 experiments/ablation_singlepass/flaw_injection_eval.py \
    --assessor single_pass --manifest fixtures/flaw_manifest_5papers.json \
    --out repl5.json
# summary.paper_level = {detection_mean, detection_sd}; summary.per_paper = breakdown
```

## Parity checklist (state this in the paper)

same model + `temperature=0`; same canonical rubric; same fixtures + threshold;
same risk/coefficient extraction. Single-pass is *not* tool-restricted, so any
extra over-flagging is attributable to the missing relevance gate, not a weaker
model or rubric.
