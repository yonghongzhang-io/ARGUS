> **SUPERSEDED (25 September 2026).** This document describes the June 2026 labels, which are replaced by the two-annotator gold of `annotation/human_pilot/PROTOCOL.md` and `experiments/annotation/gold_final/` (provenance note in `experiments/annotation/pilot_frozen/PROVENANCE.md`). Kept for the record.

# ARGUS vs Adjudicated Human Gold

Aggregate-only comparison; raw human labels remain gitignored in `data/annotations/`.

## Inputs

- Gold: `data/annotations/gold_labels.csv`
- ARGUS: `experiments/real_papers/corpus_results/did_llm_risks.csv`

## Headline

| unknown policy | n scored | exact agreement | Cohen's kappa | weighted kappa | binary flag kappa |
|---|---:|---:|---:|---:|---:|
| exclude unknown | 33 | 0.152 | 0.019 | 0.044 | 0.045 |
| unknown = mismatch | 55 | 0.091 | 0.002 | n/a | n/a |

## Coverage And Distributions

- ARGUS answered 33/55 cells (0.600); `unknown` = 22.
- Gold distribution: low 29, medium 24, high 2.
- ARGUS distribution on the gold subset: low 1, medium 8, high 24, unknown 22.
- Unknown-by-gold: low 10, medium 11, high 1.

## High-Risk Calibration

- ARGUS emitted `high` on 24/55 gold-subset cells; gold has `high` on 2/55 cells.
- ARGUS high precision: 1/24 = 0.042; false-high count = 23.
- Gold-high recall: 1/2 = 0.500.
- On answered cells, ARGUS is more severe than gold in 28, less severe in 0, equal in 5.

## Confusion Matrix

| gold \ ARGUS | low | medium | high | unknown |
|---|---:|---:|---:|---:|
| low | 1 | 5 | 13 | 10 |
| medium | 0 | 3 | 10 | 11 |
| high | 0 | 0 | 1 | 1 |

## Per-Dimension Summary

| dimension | n | answered | unknown | strict exact | answered exact | false high |
|---|---:|---:|---:|---:|---:|---:|
| concurrent_policies | 5 | 3 | 2 | 0.000 | 0.000 | 3 |
| control_group | 5 | 2 | 3 | 0.200 | 0.500 | 1 |
| data_measurement | 5 | 5 | 0 | 0.200 | 0.200 | 3 |
| inference | 5 | 3 | 2 | 0.200 | 0.333 | 1 |
| no_anticipation | 5 | 3 | 2 | 0.400 | 0.667 | 1 |
| parallel_trends | 5 | 2 | 3 | 0.000 | 0.000 | 1 |
| robustness_placebo | 5 | 0 | 5 | 0.000 | nan | 0 |
| sample_period | 5 | 5 | 0 | 0.000 | 0.000 | 4 |
| specification | 5 | 5 | 0 | 0.000 | 0.000 | 4 |
| treatment_definition_sutva | 5 | 3 | 2 | 0.000 | 0.000 | 3 |
| treatment_timing | 5 | 2 | 3 | 0.000 | 0.000 | 2 |

## Reading

ARGUS is not merely noisy; on cells where it answers, it is strongly severity-biased upward. The key failure mode is false-high inflation, while `unknown` remains a useful abstention channel that should be reported separately from substantive high risk.

