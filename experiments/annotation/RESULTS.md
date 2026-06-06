# Second-annotator pilot — results (aggregate only)

**Pilot, heavy caveats.** 5 DID papers × 11 dimensions = 55 cells, **two**
annotators (A, B). Per-dimension n=5 is too small to read; the 55-cell overall
figure is indicative, not conclusive. Raw labels live in gitignored
`data/annotations/` and are not committed.

## Inter-annotator agreement on `risk` (round 1, pre-calibration)

Four numbers (more informative than a single Cohen's kappa on an ordinal scale):

| measure | value |
|---|---|
| exact 3-level agreement | 0.51 |
| **weighted kappa (quadratic)** | **0.31** |
| binary flag-vs-low kappa | 0.30 (agreement 0.64) |
| **adjacent-disagreement share** | **0.96** |
| (plain Cohen's kappa, 3-level) | 0.17 |

Weighted kappa (0.31) is the fair summary: plain Cohen's kappa (0.17)
over-penalizes a scale whose disagreements are almost all one step apart. Of the 27
disagreements, **19 are low↔medium, 7 medium↔high, 1 a direction reversal**.

## Diagnosis: disagreement is adjacent, not substantive
- Of 55 cells: **28 exact, 26 off-by-one-level, 1 off-by-two.** A and B almost
  never disagree on direction — only on severity / where the level boundaries lie.
- Systematic calibration offset: mean severity A=0.51 vs B=0.69; B defaults to
  `medium` (32/55) where A is decisive (`low` 32/55). One hedges, one commits.

## Reading it
Low 3-level kappa here reflects **under-anchored scale boundaries and annotator
calibration drift**, not deep epistemic conflict: the binary "flag vs not"
agreement is much higher, and only one cell in 55 is a direction reversal. This
*partly* supports the thesis that identification risk is intrinsically contested,
while showing much of the disagreement is fixable rubric vagueness.

## Calibration round 1 — outcome
We adjudicated all 27 disagreements (winner A/B/both + whether the cell is
intrinsically ambiguous) and distilled anchor rules into `annotation/guideline.md`.

| outcome | count |
|---|---|
| disputes resolved to a single label | 16 / 27 |
| disputes flagged intrinsically ambiguous | 11 / 27 |
| direction of clean resolutions | B 13, A 12, both 2 |

Adjudicated **gold** (55 cells): low 29, medium 24, high 2; **11/55 (20%)** marked
ambiguous. (Gold in gitignored `data/annotations/gold_labels.csv`.)

**The key qualitative finding:** the 11 ambiguous cells are not random — they
concentrate on **non-canonical DID designs** (continuous-shock, event-study),
where a dimension like `treatment_timing` or `parallel_trends` is *not applicable
as conventionally defined*. So a real share of "expert disagreement" is actually
**design-applicability**, not severity. This is why even experts set
`ambiguity_flag`, and why ARGUS should flag/abstain rather than judge. It also
previews the ARGUS comparison: the human gold has almost no `high` (2/55), whereas
ARGUS-LLM flagged ~45% high on the corpus — i.e. ARGUS likely over-flags `high`,
to be quantified once we compare against this gold.

## Next step
A fresh independent re-annotation under the anchored guideline would measure the
kappa lift directly; then compare ARGUS's `risk` against the adjudicated gold
(`agreement.py gold_labels.csv did_llm_risks.csv`, handling `unknown`).

Reproduce: `PYTHONPATH=src python3 experiments/annotation/agreement.py --dir data/annotations`

## ARGUS-LLM vs adjudicated gold

We compared the two-stage ARGUS-LLM risk labels against the 55-cell adjudicated
gold subset. Because ARGUS has an explicit `unknown` abstention state, we report
two policies:

| unknown policy | n scored | exact agreement | Cohen's kappa | weighted kappa | binary flag kappa |
|---|---:|---:|---:|---:|---:|
| exclude unknown | 33 | 0.15 | 0.02 | 0.04 | 0.05 |
| unknown = mismatch | 55 | 0.09 | 0.00 | n/a | n/a |

Coverage and calibration:

- ARGUS answered **33/55** cells and abstained as `unknown` on **22/55**.
- Gold distribution: **low 29, medium 24, high 2**.
- ARGUS distribution on the same 55 cells: **low 1, medium 8, high 24, unknown 22**.
- On answered cells, ARGUS is more severe than gold in **28/33**, less severe in
  **0/33**, and equal in **5/33**.
- ARGUS emitted `high` on **24/55** cells, but only **1/24** was gold-high
  (precision **0.04**); it recovered **1/2** gold-high cells.

This confirms the previewed failure mode: ARGUS-LLM is not simply uncertain; when
it answers, it is strongly severity-biased upward. The practical implication is
that `unknown` should remain a separate abstention channel, while substantive
`high` requires calibration against human anchors.

Full aggregate report: `experiments/annotation/ARGUS_VS_GOLD.md`.

Reproduce: `PYTHONPATH=src python3 experiments/annotation/compare_argus_gold.py`
