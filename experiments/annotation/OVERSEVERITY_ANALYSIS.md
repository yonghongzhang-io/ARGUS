# ARGUS Over-Severity Error Analysis

Aggregate-only report. Per-cell diagnostics are written to a gitignored CSV.

## Inputs

- Rich ARGUS labels: `data/annotations/argus_rich_gold5.csv`
- Detail CSV: `data/annotations/argus_overseverity_cases.csv`

## Headline

- Gold-overlap cells: 55.
- ARGUS answered 33/55 cells and abstained on 22.
- Among answered cells: over-severe 29, equal 4, under-severe 0.
- High-risk over-severity: 24 over-severe cells where ARGUS used `high`.
- Weak-retrieval high labels: 20.
- Missing-evidence high labels: 23.

## Over-Severity By Evidence Status

| evidence_status | over-severe cells |
|---|---:|
| missing | 23 |
| partial | 5 |
| flawed | 1 |

## Over-Severity By Retrieval Quality

| retrieval_quality | over-severe cells |
|---|---:|
| weak | 20 |
| good | 9 |

## Over-Severity By Dimension

| dimension | over-severe cells |
|---|---:|
| sample_period | 5 |
| specification | 5 |
| data_measurement | 4 |
| concurrent_policies | 3 |
| treatment_definition_sutva | 3 |
| inference | 2 |
| no_anticipation | 2 |
| parallel_trends | 2 |
| treatment_timing | 2 |
| control_group | 1 |

## Dominant Patterns

| ARGUS/gold and evidence pattern | over-severe cells |
|---|---:|
| high vs gold=low | missing/weak | 12 |
| high vs gold=medium | missing/weak | 7 |
| medium vs gold=low | partial/good | 5 |
| high vs gold=medium | missing/good | 3 |
| high vs gold=low | missing/good | 1 |
| high vs gold=medium | flawed/weak | 1 |

## Reading

The dominant failure is not random disagreement. Most over-severe answered cells are `high` labels attached to `missing` evidence under weak retrieval. This indicates a severity-calibration problem: ARGUS often turns thin or weakly retrieved evidence into substantive high risk instead of a medium flag or an abstention.
