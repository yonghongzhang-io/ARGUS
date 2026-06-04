# ARGUS

**A responsible-AI framework for auditing causal identification in environmental policy evaluation.**

ARGUS audits the *causal identification credibility* of difference-in-differences (DID)
studies in environmental policy evaluation (case study: China's carbon emissions trading
pilots). It does **not** judge whether a paper's estimated effect is "true" — in a DID
design the counterfactual is never observed. Instead, ARGUS decomposes identification into
auditable dimensions, gathers supporting evidence from the paper, assesses each
assumption→implication→evidence chain, localizes weaknesses, and produces a transparent
report that flags risks for a human expert. The system is validated through *synthetic flaw
injection*, which yields local ground truth for identification threats without requiring the
true causal effect.

> **Status:** early-stage doctoral research prototype. A deterministic non-LLM
> baseline now runs end-to-end: evidence retrieval, rule-based assessment, risk
> localization, report generation, synthetic flaw injection, and clean-vs-injected
> evaluation. The model-driven reason/act policy, real PDF parsing, real figure
> extraction, and corpus-scale experiments are still future work.

---

## Pipelines

### 1. Audit pipeline (run per paper)

```
   Empirical DID policy paper
              |
              v
   [ decomposition ]        deterministic  - map paper onto ~10 identification dimensions
              |
              v
   [ extraction ]   <-- AGENTIC --+   bounded ReAct loop: fixed tool set, hard step budget
              |                   |   tools: evidence_search, figure_parse, policy_lookup
              v                   |
   [ assessment ]   <-- AGENTIC --+   assess each assumption -> implication -> evidence chain
              |                        emits a logged trace -> results/traces/
              v
   [ localization ]         deterministic  - aggregate dimension risks into a risk map
              |
              v
   [ report ]               deterministic  - transparent, evidence-anchored report
              |
              v
   Human-review report  -->  expert  (human-in-the-loop)

   NOT produced: a verdict on the true causal effect.
```

### 2. Flaw-injection evaluation loop (validates ARGUS)

```
   credible DID paper --+
                        |
                        v
              [ injection ]   inject ONE known flaw on a target dimension
                        |     (defined in config/flaw_taxonomy.yaml)
              +---------+---------+
              v                   v
        clean version       injected version
              |                   |
              v                   v
          ARGUS audit         ARGUS audit
              |                   |
              +---------+---------+
                        v
              [ evaluation ]
                 detection_rate    - did it catch the injected flaw?
                 false_alarm_rate  - did it stay quiet on the clean version?
                 localization_acc  - did it flag the RIGHT dimension?

   Local ground truth = the injected flaw, NOT the true causal effect.
```

---

## Architecture

ARGUS is a **bounded-agentic** system, not an end-to-end autonomous agent. This choice is
deliberate and load-bearing for the project's goals.

**Between modules: a fixed, deterministic, auditable pipeline.** The stages
`decomposition → extraction → assessment → localization → report` always run in the same
order, and the evaluation loop `injection → evaluation` is separate and reproducible. The
control flow is written in code, not decided by a model.

**Within modules: agentic only where it earns its place.** Only `extraction` and
`assessment` are agentic. Each invokes a bounded ReAct-style loop (`src/argus/agent/`) with:

- a **small fixed tool set** passed in per call — `evidence_search`, `figure_parse`,
  `policy_lookup`;
- a **hard step budget** (`max_steps`) so a run cannot wander indefinitely;
- a **logged trace** of every step, tool call, and cited evidence, written to
  `results/traces/`.

All other stages are plain deterministic orchestration with no agent loop.

**Current baseline.** Until a model-driven reason/act policy is added, ARGUS uses
a deterministic fallback inside the bounded loop. `extraction` calls
`evidence_search` over parsed paper text/sections/figures/tables; `assessment`
uses explicit positive/negative signals per identification dimension. This gives
the project a reproducible lower-bound system and a testable contract for later
LLM upgrades.

**Why this split.** A fully autonomous agent would make per-run behaviour path-dependent and
high-variance, which would undermine ARGUS's central evaluation claim — that flaw injection
provides *reproducible* local ground truth (detection / false-alarm / localization). Bounding
the agency to two clearly scoped sub-tasks keeps two properties that the framework depends on:
**reproducibility** (stable, comparable metrics across runs) and **evidence-traceability**
(every judgment is anchored to logged evidence a human can inspect). The human expert sits at
the end of the pipeline; ARGUS surfaces and localizes identification risks, it does not
adjudicate them.

---

## Repository layout

```
config/        identification dimensions + flaw taxonomy (the rubric the system runs on)
src/argus/     pipeline stages, the bounded agent loop + tools, evaluation metrics
data/          paper corpus, flaw-injected versions, annotations (not committed)
experiments/   phase-1 pilot and later studies
results/       generated reports and agent traces
paper/         LNCS Doctoral Consortium submission
tests/         minimal tests
```

---

## Quickstart

Run the test suite:

```bash
python3 -m pytest -q
```

Run the audit pipeline from a parsed-paper dictionary:

```bash
PYTHONPATH=src python3 -c 'from argus.pipeline.audit import run_audit; paper={"id":"demo","sections":{"parallel trends":"The event-study pre-trend coefficients are near zero and support parallel trends."}}; result=run_audit(paper, max_steps=1); print(result.report_path); print(result.risk_map["by_dimension"]["parallel_trends"]["risk"])'
```

Run one clean-vs-injected evaluation pair:

```bash
PYTHONPATH=src python3 -c 'from argus.evaluation.runner import evaluate_injected_pair; paper={"id":"demo","sections":{"parallel trends":"The event-study pre-trend coefficients are near zero and support parallel trends.","robustness placebo":"Placebo and falsification checks are reported."}}; print(evaluate_injected_pair(paper, "pretrend_divergence", max_steps=1)["score"])'
```
