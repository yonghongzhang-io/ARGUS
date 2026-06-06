# Second-annotator pilot — results (aggregate only)

**Pilot, heavy caveats.** 5 DID papers × 11 dimensions = 55 cells, **two**
annotators (A, B). Per-dimension n=5 is too small to read; the 55-cell overall
figure is indicative, not conclusive. Raw labels live in gitignored
`data/annotations/` and are not committed.

## Inter-annotator agreement on `risk`

| measure | value |
|---|---|
| percent agreement (3-level) | 0.51 |
| Cohen's kappa (3-level low/med/high) | **0.17** |
| Cohen's kappa (binary: flagged [med+high] vs low) | 0.30 |
| percent agreement (high vs rest) | 0.85 |

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

## Next step
A **calibration round** — anchor the low/medium/high boundaries with worked
examples (especially `medium`), or collapse to a 2-level flag, then re-annotate.
The rise in kappa measures how much disagreement was fixable vagueness vs
intrinsic ambiguity — itself a reportable result. Only then compare ARGUS's
`risk` against the (adjudicated) human labels.

Reproduce: `PYTHONPATH=src python3 experiments/annotation/agreement.py --dir data/annotations`
