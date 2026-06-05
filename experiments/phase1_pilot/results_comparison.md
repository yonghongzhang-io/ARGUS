# Phase-1 pilot — keyword baseline vs LLM evidence-adequacy assessor

Same flaw-injection evaluation, same retrieved evidence, two assessment policies.
Fixture: `clean_supported.json`, all 11 flaws, `max_steps=1`.

| assessor | detection | false alarm | localization |
|---|---:|---:|---:|
| keyword baseline | 0.182 | 0.000 | 0.182 |
| **LLM (gpt-4o)** | **1.000** | **0.000** | **0.909** |
| (circular, pre-fix) | 1.000 | 0.000 | 1.000 |

**Reading it.** Once the sentinel leakage that made evaluation circular is removed,
the keyword baseline collapses to 0.182 detection — blind to every commission-type
flaw. Swapping *only* the assessment policy (extraction is identical) to an LLM that
judges evidence **adequacy** recovers detection to 1.000 with no false alarms and
0.909 localization. The model reads flawed-but-natural prose the keyword scorer
cannot — e.g. it flags an injected anticipation effect as high/flawed because
"outcomes began changing between the policy announcement and rollout", with no
sentinel keyword present. This is the empirical core of the project: evidence
*presence* is not evidence *adequacy*.

**Caveat.** These are synthetic fixtures (N small); 1.000 is a proof-of-concept on
clear injected flaws, not a claim of a solved task. Real-corpus, expert-annotated
evaluation is future work.

Reproduce:

```bash
export OPENAI_API_KEY=sk-...
PYTHONPATH=src python3 experiments/phase1_pilot/compare_assessors.py
```

The LLM run is non-deterministic and costs API calls; the headline LLM summary is
frozen in `llm_summary.json` and consumed by `make_figure2.py`.
