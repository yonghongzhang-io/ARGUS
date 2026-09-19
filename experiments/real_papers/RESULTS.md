# Real-corpus audit — keyword vs two-stage LLM

27 published DID papers from the CausalVerify corpus, audited end-to-end by
ARGUS.

> **Camera-ready note (2026-09-13):** `paper_164` is a byte-identical duplicate of
> `paper_120` in the source corpus (same markdown, identical audits on all 11
> dimensions for both assessors). The paper and `make_realcorpus_figure.py` now
> exclude it and report **26 unique papers / 286 cells** (LLM: high 127, medium 40,
> low 6, unknown 113; keyword: low 259 of 286). The table below is the raw 27-paper run. Same retrieval is improved (section-level + relevance gate) only on the
LLM path; the keyword baseline is unchanged. Figure: `paper/figures/figure_realcorpus.pdf`.

## Risk distribution (totals over 27 papers × 11 dimensions = 297)

| assessor | high | medium | low | unknown |
|---|---:|---:|---:|---:|
| keyword baseline | 16 | 11 | 270 | 0 |
| two-stage LLM (gpt-4o) | 134 | 42 | 6 | 115 |

## Reading it

- **Keyword is credulous**: ~91% `low`. It sees topic vocabulary ("robustness",
  "clustered", "controls") and judges the dimension supported — it cannot tell
  presence from adequacy, so it almost never flags a real paper.
- **The two-stage LLM is differentiated**, and ~39% of judgements are `unknown`
  (~40% over the deduplicated 26 papers, which is the figure the paper reports)
  — the relevance gate could not surface evidence for that dimension, so the
  system says so rather than over-flagging. Two regimes are visible:
  - *High-unknown* dimensions (parallel trends, no anticipation, staggered
    timing, placebo): the relevant discussion is diffuse or lives in figures the
    text retrieval does not reach → honest `unknown`. This localizes the
    evidence-grounding bottleneck.
  - *Low-unknown, high-flag* dimensions (sample period, concurrent policies,
    SUTVA): retrieval finds a section and adequacy judges it insufficient.

## Honest caveat

~45% `high` on 27 top-journal papers is likely still over-strict where retrieval
succeeds — without expert labels we cannot say whether high/medium/unknown match
expert judgement. Calibrating against dimension-level expert annotation is the
next step. The defensible claim today is methodological: moving from synthetic
fixtures to real papers is bottlenecked by *evidence grounding*, which is why the
two-stage design reports retrieval quality and an explicit `unknown`.

Reproduce (CSVs are committed, so the figure needs no re-run):

```bash
PYTHONPATH=src python3 experiments/real_papers/make_realcorpus_figure.py
# to regenerate the CSVs (LLM costs API calls):
PYTHONPATH=src python3 experiments/real_papers/run_corpus.py --n 30
PYTHONPATH=src python3 experiments/real_papers/run_corpus.py --n 30 --llm
```
