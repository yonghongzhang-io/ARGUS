# ARGUS

**Evidence-grounded auditing of identification assumptions in climate-policy causal evaluations.**

ARGUS audits the *causal identification credibility* of difference-in-differences (DID)
studies in environmental policy evaluation (fixture: China's carbon emissions trading
pilots). It does **not** judge whether a paper's estimated effect is "true" — in a DID
design the counterfactual is never observed. Instead, ARGUS decomposes identification into
eleven auditable dimensions, gathers supporting evidence from the paper, assesses each
assumption→implication→evidence chain, localizes weaknesses, and produces a transparent
report that flags risks for a human expert. The system is validated through *synthetic flaw
injection*, which yields local ground truth for identification threats without requiring the
true causal effect.

> **Status:** submitted to **ClimateNLP 2026** (EMNLP workshop, under review); the
> submitted paper is `paper_climatenlp/` (snapshot tag `climatenlp2026-submission-v1`).
> The full two-stage LLM pipeline runs end-to-end: deterministic retrieval, a relevance
> gate with an explicit `unknown` abstention state, per-dimension adequacy assessment,
> risk localization, and report generation — evaluated on two flaw-injection benchmarks,
> a 27-paper real corpus, a cross-model panel, and an expert-annotated human-gold pilot.

---

## Headline results

**Flaw injection, 11 clear flaws** (gpt-4o; keyword and two-stage share identical retrieved
evidence, so that pair isolates the judgement policy):

| assessor | calls/paper | detection | false alarm | localization |
| --- | --- | --- | --- | --- |
| keyword baseline | 0 | 0.182 | 0.000 | 0.182 |
| full-paper single pass | 1 | 0.818 | 0.000 | 0.818 |
| per-dimension, no retrieval | 11 | 1.000 | 0.000 | 1.000 |
| two-stage ARGUS (retrieval + gate) | 22 | 0.727 | 0.000 | 0.727 |

The gated pipeline's misses are all *omission* flaws on which it **abstains rather than
guesses**; an oracle-retrieval ablation attributes every such miss to the gate, not the
judge (commission 0.86 / omission 1.00 when the assessor is fed the target section
directly), and the gate also suppresses the alarms section-level evidence alone triggers.

**Harder 33-variant benchmark** (three runs, near-deterministic, 32/33 verdicts identical):
detection 0.75, false alarm 0.09, localization 0.66; commission 0.89 vs omission 0.45
(omission misses are abstentions — the evidence-grounding bottleneck).

**Cross-model panel** (unchanged pipeline, `config/models.yaml`): commission detection is
high everywhere (gpt-4o 0.89, Claude Opus 4.8 1.00, Gemini 2.5 Flash 0.91, local
Llama 3.1 8B 0.95); the precision profile is model-dependent.

**Real papers (27 top-journal DID studies):** the bottleneck relocates from causal
reasoning to *evidence grounding* — ~39% of judgements abstain to `unknown` where
retrieval fails. **Human-gold pilot (5 papers × 11 dimensions):** ARGUS is systematically
over-severe; a deterministic calibration layer (demote weak-retrieval `high`) raises exact
agreement 0.15 → 0.45, and the rule re-emerges in every leave-one-paper-out fold.

---

## Pipelines

### 1. Audit pipeline (run per paper)

```
   Empirical DID policy paper
              |
              v
   [ decomposition ]        deterministic  - map paper onto 11 identification dimensions
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

Injection is *realistic structural perturbation*, not sentinel strings: omission flaws
delete the supporting section/figure; commission flaws rewrite a section in
flawed-but-natural prose. A leak-freedom regression test fails if an injected paper
contains the detector's negative-signal phrases, so circular detection cannot silently
return.

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

**Assessors.** The primary assessor is the **two-stage LLM pipeline**: deterministic
section retrieval, one relevance-gate call (may abstain to `unknown`), one adequacy call
per dimension (2 calls/dimension, 22/paper, ≈US$0.25 of gpt-4o per audit at temperature 0,
`max_steps=1`). A **deterministic keyword baseline** (explicit positive/negative signals
per dimension) is retained as the comparison floor, and single-pass / per-dimension
ablation arms isolate what each architectural ingredient buys. Providers are configured in
`config/models.yaml`: OpenAI, Anthropic (via an OpenAI-shaped facade), and any
OpenAI-compatible endpoint (Gemini; local Llama via Ollama).

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
config/            identification rubric, flaw taxonomy, 33-variant catalog, model registry
examples/          committed parsed-paper fixtures (clean + injectable)
src/argus/         pipeline stages, bounded agent loop + tools, LLM assessors, metrics
data/              paper corpus, flaw-injected versions, annotations (not committed)
annotation/        human-gold protocols + annotation tooling (oracle spans; gold expansion)
experiments/       phase1_pilot, variants (33-flaw benchmark), ablations (compute-graded,
                   oracle-evidence, oracle-retrieval, LOPO calibration), models (cross-model),
                   real_papers (27-paper corpus runs)
results/           generated reports and agent traces
paper_climatenlp/  ClimateNLP 2026 submission (ACL format; submissions/ holds the frozen PDF)
paper/             earlier LNCS Doctoral Consortium draft (superseded)
tests/             test suite (125 tests; includes leak-freedom regression checks)
```

---

## Quickstart

Run the test suite (no API key needed):

```bash
python3 -m pytest -q
```

ARGUS starts from a parsed-paper JSON object, not a raw PDF. Minimum schema:

```json
{
  "id": "paper_id",
  "title": "Paper title",
  "abstract": "optional abstract text",
  "sections": {
    "section title": "section text"
  },
  "figures": [
    {"id": "fig_event_study", "caption": "figure caption"}
  ],
  "tables": [
    {"id": "table_balance", "caption": "table caption"}
  ]
}
```

Run the audit pipeline from a parsed-paper JSON file:

```bash
PYTHONPATH=src python3 -m argus.cli audit examples/papers/china_carbon_ets_pilot.json --max-steps 1
```

Run one clean-vs-injected evaluation pair:

```bash
PYTHONPATH=src python3 -m argus.cli evaluate examples/papers/clean_supported.json --flaw pretrend_divergence --max-steps 1
```

LLM runs read API keys from a gitignored `.env` (see `.env.example`); experiment runners
that spend money are gated behind an explicit `--i-understand-this-costs-money` flag.
Frozen result JSONs for every number reported in the paper are committed under
`experiments/`; Appendix C of the paper documents reproducibility details, including an
observed provider-side serving-drift episode and why only currently replicable numbers are
reported.
